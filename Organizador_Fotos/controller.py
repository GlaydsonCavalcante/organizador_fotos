# controller.py
import os
import shutil
import time
from pathlib import Path
from datetime import datetime
import model  # Importamos o nosso cérebro lógico

def organizar_arquivos(diretorio_origem, diretorio_destino, callback_progresso=None):
    """
    Função principal que percorre a origem e organiza no destino.
    
    Args:
        diretorio_origem (str): Caminho da pasta bagunçada.
        diretorio_destino (str): Onde vai ficar organizado.
        callback_progresso (func): Função opcional para atualizar barra de progresso no Streamlit.
    
    Returns:
        dict: Um relatório do que aconteceu (sucessos, duplicatas, erros).
    """
    
    origem_path = Path(diretorio_origem)
    destino_path = Path(diretorio_destino)
    
    # Estrutura para o Relatório Final
    stats = {
        "processados": 0,
        "movidos_novos": 0,
        "colisoes_renomeadas": 0,
        "duplicatas_quarentena": 0,
        "outros_arquivos": 0,
        "erros": []
    }

    # Lista todos os arquivos (recursivamente)
    arquivos = [f for f in origem_path.rglob("*") if f.is_file()]
    total_arquivos = len(arquivos)
    
    # Pastas especiais de segurança
    pasta_quarentena = destino_path / "_DUPLICATAS_DETECTADAS"
    
    print(f"Iniciando processamento de {total_arquivos} arquivos...")

    for i, arquivo_atual in enumerate(arquivos):
        # Atualiza a barra de progresso (se existir interface conectada)
        if callback_progresso:
            callback_progresso(i + 1, total_arquivos, arquivo_atual.name)
            
        try:
            # Ignora arquivos de sistema ocultos (começados por .)
            if arquivo_atual.name.startswith('.'):
                continue

            stats["processados"] += 1
            extensao = arquivo_atual.suffix
            categoria = model.definir_categoria(extensao)

            # === CAMINHO 1: ARQUIVOS DE MÍDIA (FOTOS/VÍDEOS) ===
            if categoria in ["RAW", "Editados"]:
                
                # 1. Obter dados
                data_foto = model.obter_data_foto(arquivo_atual)
                
                # 2. Definir pasta destino (Ano / Mês)
                pasta_ano = data_foto.strftime("%Y")
                pasta_mes = data_foto.strftime("%m")
                pasta_final = destino_path / pasta_ano / pasta_mes / categoria
                
                # 3. Gerar Nome Padronizado
                novo_nome = model.gerar_nome_padronizado(data_foto, arquivo_atual.name)
                caminho_final = pasta_final / novo_nome
                
                # Cria a pasta se não existir
                pasta_final.mkdir(parents=True, exist_ok=True)

                # === LÓGICA CORE DE SEGURANÇA ===
                
                # CENÁRIO A: Arquivo não existe no destino. Caminho livre!
                if not caminho_final.exists():
                    shutil.copy2(arquivo_atual, caminho_final)
                    
                    # Verificação Paranoica: Copiou direito?
                    if model.arquivos_sao_identicos(arquivo_atual, caminho_final):
                        os.remove(arquivo_atual) # Seguro para deletar origem
                        stats["movidos_novos"] += 1
                    else:
                        stats["erros"].append(f"FALHA INTEGRIDADE: {arquivo_atual.name}")
                        # Se falhou, remove o destino corrompido e mantém a origem
                        if caminho_final.exists(): os.remove(caminho_final)

                # CENÁRIO B: Arquivo com esse nome JÁ EXISTE.
                else:
                    # Verifica se é DUPLICATA REAL (Conteúdo Idêntico)
                    if model.arquivos_sao_identicos(arquivo_atual, caminho_final):
                        # É lixo. Mover para quarentena e limpar origem.
                        model.mover_para_quarentena(arquivo_atual, pasta_quarentena, origem_path)
                        stats["duplicatas_quarentena"] += 1
                    
                    else:
                        # COLISÃO DE NOME: Conteúdo diferente, mas mesmo nome (ex: foto tirada no mesmo segundo)
                        # Ação: Renomear com contador (_01, _02...) e Salvar.
                        contador = 1
                        while True:
                            nome_colisao = f"{caminho_final.stem}_{contador:02d}{caminho_final.suffix}"
                            caminho_colisao = pasta_final / nome_colisao
                            
                            if not caminho_colisao.exists():
                                # Achou um nome livre!
                                shutil.copy2(arquivo_atual, caminho_colisao)
                                
                                if model.arquivos_sao_identicos(arquivo_atual, caminho_colisao):
                                    os.remove(arquivo_atual)
                                    stats["colisoes_renomeadas"] += 1
                                break # Sai do while
                            
                            # Se o arquivo numerado também já existe, verifica se é duplicata dele
                            if model.arquivos_sao_identicos(arquivo_atual, caminho_colisao):
                                model.mover_para_quarentena(arquivo_atual, pasta_quarentena, origem_path)
                                stats["duplicatas_quarentena"] += 1
                                break # Sai do while
                            
                            contador += 1

            # === CAMINHO 2: OUTROS ARQUIVOS (PDF, TXT, ETC) ===
            else:
                # Mantém estrutura de pastas original dentro de "Outros_Arquivos"
                try:
                    rel_path = arquivo_atual.relative_to(origem_path)
                except ValueError:
                    rel_path = Path(arquivo_atual.name)
                
                dest_outro = destino_path / "Outros_Arquivos" / rel_path
                dest_outro.parent.mkdir(parents=True, exist_ok=True)
                
                # Lógica simplificada para outros arquivos:
                # Se não existe, move. Se existe e é igual, quarentena. Se diferente, renomeia.
                if not dest_outro.exists():
                    shutil.copy2(arquivo_atual, dest_outro)
                    if model.arquivos_sao_identicos(arquivo_atual, dest_outro):
                        os.remove(arquivo_atual)
                        stats["outros_arquivos"] += 1
                else:
                    if model.arquivos_sao_identicos(arquivo_atual, dest_outro):
                        model.mover_para_quarentena(arquivo_atual, pasta_quarentena, origem_path)
                        stats["duplicatas_quarentena"] += 1
                    else:
                        # Colisão em arquivo genérico -> Renomeia
                        cont = 1
                        while True:
                            nome_novo = f"{dest_outro.stem}_copy{cont}{dest_outro.suffix}"
                            dest_novo = dest_outro.parent / nome_novo
                            if not dest_novo.exists():
                                shutil.copy2(arquivo_atual, dest_novo)
                                if model.arquivos_sao_identicos(arquivo_atual, dest_novo):
                                    os.remove(arquivo_atual)
                                    stats["outros_arquivos"] += 1
                                break
                            cont += 1

        except Exception as e:
            error_msg = f"Erro ao processar {arquivo_atual}: {str(e)}"
            print(error_msg)
            stats["erros"].append(error_msg)

    # === LIMPEZA FINAL PROFUNDA ===
    # Percorre a árvore de diretórios de BAIXO para CIMA (topdown=False)
    # Isso garante que apagamos as subpastas vazias antes de tentar apagar as pastas pai.
    print("Executando limpeza de pastas vazias...")
    
    for root, dirs, files in os.walk(origem_path, topdown=False):
        for name in dirs:
            caminho_pasta = Path(root) / name
            try:
                # rmdir só apaga se a pasta estiver ESTRITAMENTE vazia.
                # Se tiver sobrado algum arquivo oculto ou não movido, ele protege e não apaga.
                caminho_pasta.rmdir()
            except OSError:
                pass # Pasta não estava vazia ou erro de permissão, segue o jogo.

    return stats