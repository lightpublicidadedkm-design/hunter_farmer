import os
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime
from fpdf import FPDF
from dotenv import load_dotenv
from supabase import create_client, Client

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="IA Hunter - Sicredi", layout="wide", page_icon="🏦")

# --- CONEXÃO COM BANCO SUPABASE ---
load_dotenv()
try:
    supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
except Exception as e:
    st.error(f"⚠️ Erro ao configurar Supabase. Verifique seu arquivo .env. Detalhes: {e}")

@st.cache_data(ttl=60) # Atualiza os dados a cada 60 segundos
def carregar_dados():
    try:
        response = supabase.table("leads_hunter").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Erro ao buscar dados no Supabase: {e}")
        return pd.DataFrame()

# --- FUNÇÃO GERADORA DE PDF ---
def gerar_pdf_relatorio(df, total, quentes, taxa):
    data_hora_atual = datetime.now().strftime('%d/%m/%Y às %H:%M:%S')
    
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Relatorio de Prospeccao - IA Hunter Sicredi", ln=True, align='C')
    
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(200, 10, txt=f"Gerado em: {data_hora_atual}", ln=True, align='C')
    pdf.ln(10)
    
    # KPIs
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="RESUMO DE PERFORMANCE:", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 8, txt=f"- Total Prospectado: {total} empresas", ln=True)
    pdf.cell(200, 8, txt=f"- Leads Quentes (Respondeu Ok): {quentes} empresas", ln=True)
    pdf.cell(200, 8, txt=f"- Taxa de Conversao: {taxa:.1f}%", ln=True)
    pdf.ln(10)
    
    # Tabela de Leads Quentes
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="ULTIMOS LEADS QUENTES (OK):", ln=True)
    pdf.set_font("Arial", '', 10)
    
    df_quentes = df[df['status_funil'] == 'Respondeu Ok']
    if df_quentes.empty:
        pdf.cell(200, 8, txt="Nenhum lead quente no momento.", ln=True)
    else:
        for index, row in df_quentes.iterrows():
            nicho = str(row.get('nicho_mercado', 'N/A'))
            empresa = str(row.get('nome_empresa', 'N/A'))
            # Limpa caracteres especiais para o PDF não quebrar
            linha = f"[{nicho}] {empresa}".encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(200, 8, txt=linha, ln=True)
        
    # Retorna o PDF em bytes prontos para o botão de download
    return pdf.output(dest='S').encode('latin-1')


# --- MENU LATERAL (SIDEBAR) ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Sicredi_logo.svg/2560px-Sicredi_logo.svg.png", width=150)
st.sidebar.title("Navegação")
menu_selecionado = st.sidebar.radio("Ir para:", ["📊 Dashboard CRM", "⚙️ Motor Principal IA"])
st.sidebar.markdown("---")
st.sidebar.caption("🤖 App Master v1.0")


# ==========================================
# TELA 1: DASHBOARD CRM E MÉTRICAS
# ==========================================
if menu_selecionado == "📊 Dashboard CRM":
    st.title("📊 Painel de Performance B2B")
    df_leads = carregar_dados()

    if df_leads.empty:
        st.warning("📭 Nenhum dado encontrado no banco de dados ainda. Inicie a prospecção no menu lateral!")
    else:
        # Cálculos de KPI
        total_leads = len(df_leads)
        leads_ok = len(df_leads[df_leads['status_funil'] == 'Respondeu Ok'])
        leads_recusa = len(df_leads[df_leads['status_funil'] == 'Respondeu Não'])
        leads_em_negociacao = total_leads - leads_ok - leads_recusa
        taxa_conversao = (leads_ok / total_leads) * 100 if total_leads > 0 else 0

        # Botão de Exportar PDF
        pdf_bytes = gerar_pdf_relatorio(df_leads, total_leads, leads_ok, taxa_conversao)
        st.download_button(
            label="📄 Exportar Relatório em PDF",
            data=pdf_bytes,
            file_name=f"Relatorio_Prospeccao_Sicredi_{datetime.now().strftime('%d_%m_%Y')}.pdf",
            mime="application/pdf",
            type="primary"
        )
        st.markdown("---")

        # KPIs Visuais Superiores
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🎯 Total Prospectado", total_leads)
        col2.metric("🔥 Leads Quentes (Ok)", leads_ok)
        col3.metric("🧊 Em Aquecimento", leads_em_negociacao)
        col4.metric("📈 Taxa de Conversão", f"{taxa_conversao:.1f}%")
        st.markdown("---")

        # Gráficos Dinâmicos
        col_grafico1, col_grafico2 = st.columns(2)
        with col_grafico1:
            st.subheader("📍 Efetividade por Nicho")
            df_nicho_ok = df_leads[df_leads['status_funil'] == 'Respondeu Ok'].groupby('nicho_mercado').size().reset_index(name='Convertidos')
            df_nicho_total = df_leads.groupby('nicho_mercado').size().reset_index(name='Total')
            df_nicho = pd.merge(df_nicho_total, df_nicho_ok, on='nicho_mercado', how='left').fillna(0)
            df_nicho['Taxa'] = (df_nicho['Convertidos'] / df_nicho['Total']) * 100
            
            fig_nicho = px.bar(df_nicho, x='nicho_mercado', y='Taxa', text_auto='.2s', 
                               title="Taxa de Conversão por Setor (%)")
            fig_nicho.update_traces(marker_color='#009b3a') # Verde Sicredi
            st.plotly_chart(fig_nicho, use_container_width=True)

        with col_grafico2:
            st.subheader("🌪️ Funil de Vendas Atual")
            status_counts = df_leads['status_funil'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Quantidade']
            fig_funil = px.funnel(status_counts, x='Quantidade', y='Status', title="Distribuição do Funil")
            st.plotly_chart(fig_funil, use_container_width=True)

        # Tabela Final
        st.subheader("🤝 Últimos Leads Quentes ('Respondeu Ok')")
        df_quentes = df_leads[df_leads['status_funil'] == 'Respondeu Ok'][['nome_empresa', 'nicho_mercado', 'dor_presumida']]
        st.dataframe(df_quentes, use_container_width=True, hide_index=True)


# ==========================================
# TELA 2: CONTROLE DO MOTOR (SALES HUNTER)
# ==========================================
elif menu_selecionado == "⚙️ Motor Principal IA":
    st.title("⚙️ Painel de Controle do Motor IA")
    st.markdown("Use este painel para forçar a execução de tarefas da Inteligência Artificial fora do horário agendado.")
    
    # Tenta importar o motor
    motor_conectado = False
    try:
        import sales_hunter
        motor_conectado = True
    except ImportError:
        st.error("❌ Arquivo 'sales_hunter.py' não encontrado na mesma pasta. Verifique o nome do arquivo!")

    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 Caça de Leads e Follow-ups")
        st.write("Aciona a rotina completa: Verifica o Trello, faz remarketing e busca novos leads no Google.")
        
        if st.button("▶️ Executar Rotina Completa Agora", type="primary", disabled=not motor_conectado):
            with st.spinner("⏳ A IA está trabalhando... Acompanhe os detalhes na tela preta do seu terminal. Isso pode levar alguns minutos."):
                try:
                    # Chama a função principal do seu arquivo sales_hunter.py
                    sales_hunter.executar_rotina_hunter()
                    st.success("✅ Ciclo concluído com sucesso! Verifique seu Trello e o Dashboard.")
                except Exception as e:
                    st.error(f"❌ Ocorreu um erro durante a execução: {e}")
            
    with col2:
        st.subheader("📡 Status do Sistema")
        if motor_conectado:
            st.success("✅ Motor `sales_hunter.py` conectado!")
        else:
            st.error("❌ Motor desconectado.")
            
        st.info("💡 **Lembrete:** Para o robô de envios automáticos pelo WhatsApp Web (Playwright) funcionar, o script dele deve ser rodado separadamente no terminal.")