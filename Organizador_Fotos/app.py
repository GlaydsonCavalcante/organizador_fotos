# app.py
import streamlit as st
import tkinter as tk
from tkinter import filedialog
import controller
import model
import os

# Configuração da Página
st.set_page_config(
    page_title="Organizador Mestre de Fotos",
    page_icon="📸",
    layout="centered"
)

def selecionar_pasta_janela():
    """
    Abre uma janela nativa do sistema para selecionar pasta.
    Funciona porque o Streamlit está rodando localmente na sua máquina.
    """
    root = tk.Tk()
    root.withdraw()  # Esconde a janela principal feia
    root.attributes('-topmost', True)  # Força a janela a aparecer na frente
    pasta = filedialog.askdirectory()
    root.destroy()
    return pasta

# --- TÍTULO E EXPLICAÇÃO ---
st.title("📸 Organizador Mestre de Fotos")
st.markdown("""
Este sistema organiza suas fotos em **Ano/Mês**, separa **RAW de JPG** e move duplicatas para uma **Quarentena** segura.
""")

st.divider()

# --- SEÇÃO 1: SELEÇÃO DE ORIGEM E DESTINO ---

col1, col2 = st.columns(2)

# Variáveis de estado para guardar os caminhos selecionados
if 'input_origem' not in st.session_state:
    st.session_state['input_origem'] = ""
if 'input_destino' not in st.session_state:
    st.session_state['input_destino'] = ""

with col1:
    st.subheader("📂 1. Origem")
    st.info("Onde estão as fotos bagunçadas?")

    if st.button("Selecionar Pasta Origem"):
        caminho = selecionar_pasta_janela()
        if caminho:
            st.session_state['origem'] = caminho
            st.session_state['input_origem'] = caminho 
            st.rerun() 
            
    st.text_input("Caminho Origem:", key="input_origem")

with col2:
    st.subheader("💾 2. Destino")
    st.info("Para onde elas vão?")
    
    if st.button("Selecionar Pasta Destino"):
        caminho = selecionar_pasta_janela()
        if caminho:
            st.session_state['destino'] = caminho
            st.session_state['input_destino'] = caminho
            st.rerun()
    
    st.text_input("Caminho Destino:", key="input_destino")

# --- SEÇÃO 2: VALIDAÇÃO E EXECUÇÃO ---

st.divider()

# Botão principal
btn_iniciar = st.button("🚀 INICIAR ORGANIZAÇÃO", type="primary", use_container_width=True)

# Área de Feedback
status_text = st.empty()
progress_bar = st.progress(0)
log_area = st.expander("Ver Log Detalhado", expanded=True)

if btn_iniciar:
    origem = st.session_state['input_origem'] 
    destino = st.session_state['input_destino']

    # Validações Básicas
    if not origem or not os.path.exists(origem):
        st.error("❌ Por favor, selecione uma pasta de ORIGEM válida.")
    elif not destino or not os.path.exists(destino):
        st.error("❌ Por favor, selecione uma pasta de DESTINO válida.")
    elif origem == destino:
        st.error("⚠️ A Origem e o Destino não podem ser exatamente a mesma pasta!")
    else:
        # --- INÍCIO DO PROCESSO ---
        status_text.info("⏳ Iniciando a análise dos arquivos...")
        
        # Função de Callback para atualizar a barra do Streamlit
        def atualizar_interface(atual, total, nome_arquivo):
            percentual = int((atual / total) * 100)
            progress_bar.progress(percentual)
            status_text.text(f"Processando [{atual}/{total}]: {nome_arquivo}")

        # Chama o Controller
        try:
            # O st.spinner mostra uma animação de "carregando"
            with st.spinner('Organizando suas memórias... Isso pode demorar.'):
                resultado = controller.organizar_arquivos(
                    origem, 
                    destino, 
                    callback_progresso=atualizar_interface
                )
            
            # --- RELATÓRIO FINAL ---
            progress_bar.progress(100)
            status_text.success("✅ Processo Concluído!")
            
            st.balloons() # Celebração!

            st.subheader("📊 Resumo da Operação")
            
            # Métricas lado a lado
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Processados", resultado["processados"])
            m2.metric("Movidos (Novos)", resultado["movidos_novos"])
            m3.metric("Renomeados (Colisões)", resultado["colisoes_renomeadas"])
            m4.metric("Quarentena (Duplicatas)", resultado["duplicatas_quarentena"])
            
            st.metric("Outros Arquivos (Espelhados)", resultado["outros_arquivos"])

            # Se houver erros, mostra em vermelho
            if resultado["erros"]:
                st.error(f"Ocorreram {len(resultado['erros'])} erros durante o processo.")
                with st.expander("Ver Erros"):
                    for erro in resultado["erros"]:
                        st.write(erro)
            else:
                st.success("Nenhum erro de leitura/gravação detectado.")

        except Exception as e:
            st.error(f"Ocorreu um erro crítico no sistema: {e}")