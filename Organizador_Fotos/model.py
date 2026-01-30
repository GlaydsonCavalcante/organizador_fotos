import os
import shutil
import hashlib
import exifread
import platform
from datetime import datetime
from pathlib import Path

# --- CONFIGURAÇÕES GLOBAIS ---
EXTENSOES_RAW = {'.CR2', '.NEF', '.ARW', '.DNG', '.ORF', '.RAF', '.SR2'}
EXTENSOES_IMAGEM = EXTENSOES_RAW.union({'.JPG', '.JPEG', '.PNG', '.HEIC', '.TIFF', '.BMP'})

def listar_drivers():
    """Retorna uma lista de letras de unidade (Windows) ou montagens disponíveis."""
    drives = []
    sistema = platform.system()
    
    if sistema == 'Windows':
        import string
        # Itera de A a Z verificando se existe
        available_drives = ['%s:' % d for d in string.ascii_uppercase if os.path.exists('%s:' % d)]
        drives = available_drives
    else:
        # Linux/Mac (adaptação simples)
        drives = [str(p) for p in Path("/Volumes").iterdir()] if os.path.exists("/Volumes") else ["/"]
        
    return drives

def calcular_hash_arquivo(filepath):
    """
    Gera uma impressão digital (MD5) do arquivo.
    Se dois arquivos têm o mesmo hash, eles são bit-a-bit idênticos.
    """
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            # Lê em blocos de 64kb para não lotar a memória RAM
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None

def obter_data_foto(filepath):
    """
    Tenta descobrir a data real da foto.
    Ordem: EXIF DateTimeOriginal > EXIF DateTime > Data Modificação Arquivo
    """
    try:
        with open(filepath, 'rb') as f:
            tags = exifread.process_file(f, stop_tag="EXIF DateTimeOriginal", details=False)
            
            # Tenta tags comuns de data
            for tag in ["EXIF DateTimeOriginal", "Image DateTime"]:
                if tag in tags:
                    data_str = str(tags[tag])
                    try:
                        return datetime.strptime(data_str, "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        continue # Formato inválido, tenta próxima
    except Exception:
        pass
    
    # Se falhar tudo, usa data do sistema de arquivos
    timestamp = os.path.getmtime(filepath)
    return datetime.fromtimestamp(timestamp)

def definir_categoria(extensao):
    """Define se é RAW, Editado (JPG/PNG) ou Outro."""
    ext = extensao.upper()
    if ext in EXTENSOES_RAW:
        return "RAW"
    elif ext in EXTENSOES_IMAGEM:
        return "Editados" # Ou 'Processados', como preferir
    else:
        return "Outros_Arquivos"

def gerar_nome_padronizado(data_obj, nome_original):
    """
    Gera nome estritamente pela data: AAAAMMDD_HHMMSS.ext
    Ignora o nome original da câmera (IMG_001, DSC001, etc).
    """
    # Separa a extensão do arquivo (ex: .JPG, .CR2)
    _, extensao = os.path.splitext(nome_original)
        
    # Gera o nome base
    novo_nome_base = data_obj.strftime("%Y%m%d_%H%M%S")
    
    return f"{novo_nome_base}{extensao}"

def arquivos_sao_identicos(caminho_origem, caminho_destino):
    """
    Verificação de segurança nível paranoico.
    Retorna True APENAS se tamanho E conteúdo (hash) forem iguais.
    """
    if not caminho_destino.exists():
        return False
        
    # 1. Cheque rápido: Tamanho
    if caminho_origem.stat().st_size != caminho_destino.stat().st_size:
        return False
    
    # 2. Cheque demorado: Hash (Conteúdo)
    hash_origem = calcular_hash_arquivo(caminho_origem)
    hash_destino = calcular_hash_arquivo(caminho_destino)
    
    return hash_origem == hash_destino and hash_origem is not None

def mover_para_quarentena(caminho_arquivo, pasta_base_quarentena, raiz_origem):
    """
    Em vez de apagar, move duplicatas para uma pasta isolada mantendo a estrutura.
    """
    # Calcula o caminho relativo para manter a estrutura de pastas
    # Ex: Origem: D:/Fotos/2020/Foto.jpg -> Quarentena/2020/Foto.jpg
    try:
        caminho_relativo = caminho_arquivo.relative_to(raiz_origem)
    except ValueError:
        caminho_relativo = caminho_arquivo.name

    destino_quarentena = pasta_base_quarentena / caminho_relativo
    destino_quarentena.parent.mkdir(parents=True, exist_ok=True)
    
    # Move (sobrescreve se já existir na quarentena, pois é lixo duplicado)
    shutil.move(str(caminho_arquivo), str(destino_quarentena))

def copiar_com_verificacao(origem, destino):
    """Copia e garante que chegou inteiro."""
    shutil.copy2(origem, destino)
    if arquivos_sao_identicos(origem, destino):
        return True
    return False