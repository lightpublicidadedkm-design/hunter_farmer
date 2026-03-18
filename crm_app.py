import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

# --- LIGAÇÃO À BASE DE DADOS ---
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

st.set_page_config(page_title="CRM - DJM Tecnologia", layout="wide")
st.title("🎯 CRM de Prospeção ABM")
st.markdown("Faça a gestão dos leads gerados pela IA e controle a cadência.")

# --- DADOS ---
@st.cache_data(ttl=60)
def carregar_leads():
    # Vai buscar apenas os leads que ainda estão em cadência ou responderam
    resposta = supabase.table("leads_hunter").select("*").execute()
    return resposta.data

leads = carregar_leads()

if not leads:
    st.info("Nenhum lead encontrado. Execute o seu Motor de Busca primeiro.")
else:
    # --- MÉTRICAS ---
    ativos = sum(1 for lead in leads if lead.get("status_funil") == "Prospecção")
    respondidos = sum(1 for lead in leads if lead.get("status_funil") == "Respondeu")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Leads em Cadência", ativos)
    col2.metric("Respostas Recebidas", respondidos)
    col3.metric("Taxa de Conversão", f"{(respondidos/len(leads)*100):.1f}%" if len(leads) > 0 else "0%")

    st.divider()
    
    # --- PAINEL KANBAN (LISTAGEM) ---
    st.subheader("📋 Fila de Execução e Kill Switch")
    
    for lead in leads:
        with st.expander(f"🏢 {lead['nome_empresa']} - {lead.get('nome_socio', 'Sem Nome')}"):
            c1, c2 = st.columns([3, 1])
            
            with c1:
                st.write(f"**E-mail Sugerido:** {lead.get('email', 'N/A')}")
                st.write(f"**Dor Detetada:** {lead.get('dor_presumida', 'N/A')}")
                st.write(f"**Estado Atual:** `{lead.get('status_funil', 'Desconhecido')}`")
            
            with c2:
                # O KILL SWITCH
                if lead.get("status_funil") != "Respondeu":
                    if st.button("🛑 Cliente Respondeu (Parar Cadência)", key=f"stop_{lead['id']}"):
                        supabase.table("leads_hunter").update({"status_funil": "Respondeu"}).eq("id", lead['id']).execute()
                        st.success("Cadência interrompida!")
                        st.rerun()
                else:
                    st.success("✅ Negociação Ativa")