import streamlit as st
import requests
import os
import time
from datetime import datetime, timedelta, time as dt_time
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

@st.cache_data(ttl=3600)
def carregar_estados():
    try:
        r = requests.get("https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome", timeout=15)
        return {e['sigla']: e['nome'] for e in r.json()}
    except: return {}

@st.cache_data(ttl=3600)
def carregar_cidades(estados_siglas):
    if not estados_siglas: return []
    todas_cidades = []
    for sigla in estados_siglas:
        try:
            r = requests.get(f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{sigla}/municipios", timeout=15)
            todas_cidades.extend([f"{c['nome']} - {sigla}" for c in r.json()])
        except: continue
    return sorted(todas_cidades)

@st.cache_data(ttl=3600)
def carregar_secoes_cnae():
    try:
        r = requests.get("https://servicodados.ibge.gov.br/api/v2/cnae/secoes", timeout=15)
        return {s['id']: s['descricao'] for s in r.json()}
    except: return {}

@st.cache_data(ttl=3600)
def carregar_cnaes_por_secoes(lista_secoes):
    if not lista_secoes: return []
    subclasses = []
    for id_secao in lista_secoes:
        try:
            r = requests.get(f"https://servicodados.ibge.gov.br/api/v2/cnae/secoes/{id_secao}/subclasses", timeout=15)
            for sub in r.json():
                subclasses.append(f"{sub['id']} - {sub['descricao']}")
        except: continue
    return sorted(list(set(subclasses)))

def executar_setup(id_edicao=None):
    st.title("🏗️ Setup Avançado de Clientes")
    
    dados_banco = {}
    if id_edicao:
        res = get_supabase().table("clientes").select("*").eq("id", id_edicao).execute()
        if res.data:
            dados_banco = res.data[0]
            st.info(f"Editando: {dados_banco['nome_empresa']}")

    st.subheader("1. Identificação e Metas")
    col_a, col_b = st.columns(2)
    with col_a:
        nome_empresa = st.text_input("Nome da Empresa", value=dados_banco.get('nome_empresa', ""))
        produto = st.text_input("Produto/Serviço", value=dados_banco.get('produto_oferecido', ""))
    with col_b:
        meta = st.number_input("Meta de Leads", min_value=1, value=dados_banco.get('meta_de_leads', 10))
        venc_banco = dados_banco.get('data_vencimento', str(datetime.now().date()))
        vencimento = st.date_input("Vencimento", value=datetime.strptime(venc_banco, '%Y-%m-%d').date())

    st.divider()
    
    # --- NOVA SEÇÃO: EXPEDIENTE DO ROBÔ ---
    st.subheader("⏰ Horário de Expediente do Robô")
    cd1, cd2, cd3 = st.columns(3)
    dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    with cd1:
        dias_sel = st.multiselect("Dias de Operação", dias_semana, default=dados_banco.get('dias_operacao', ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]))
    with cd2:
        h_ini_str = dados_banco.get('horario_inicio', "08:00")
        h_ini = datetime.strptime(h_ini_str, "%H:%M").time() if h_ini_str else dt_time(8, 0)
        hora_inicio = st.time_input("Hora de Início", value=h_ini)
    with cd3:
        h_fim_str = dados_banco.get('horario_fim', "18:00")
        h_fim = datetime.strptime(h_fim_str, "%H:%M").time() if h_fim_str else dt_time(18, 0)
        hora_fim = st.time_input("Hora de Fim", value=h_fim)

    st.divider()
    st.subheader("📍 Filtro Geográfico")
    c1, c2 = st.columns(2)
    estados_ibge = carregar_estados()
    with c1:
        estados_sel = st.multiselect("Estados", options=list(estados_ibge.keys()), 
                                     default=dados_banco.get('estados_alvo', []), format_func=lambda x: f"{x} - {estados_ibge[x]}")
    with c2:
        cidades_ops = carregar_cidades(estados_sel)
        cidades_sel = st.multiselect("Cidades (Vazio = Todas)", options=cidades_ops, 
                                     default=[c for c in dados_banco.get('cidades_alvo', []) if c in cidades_ops])

    st.divider()
    st.subheader("📊 Segmentação CNAE")
    cs1, cs2 = st.columns(2)
    secoes_ibge = carregar_secoes_cnae()
    with cs1:
        reverso = {v: k for k, v in secoes_ibge.items()}
        def_secoes = [reverso[g] for g in dados_banco.get('grupos_cnae', []) if g in reverso]
        secoes_sel = st.multiselect("Grupos Econômicos", options=list(secoes_ibge.keys()), 
                                    default=def_secoes, format_func=lambda x: f"Seção {x}: {secoes_ibge[x]}")
    with cs2:
        cnaes_ops = carregar_cnaes_por_secoes(secoes_sel)
        cnaes_sel = st.multiselect("Atividades Específicas", options=cnaes_ops, 
                                    default=[c for c in dados_banco.get('cnaes_especificos', []) if c in cnaes_ops])

    st.divider()
    st.subheader("🔐 Credenciais")
    cx, cy, cz = st.columns(3)
    with cx:
        email_r = st.text_input("E-mail Disparo", value=dados_banco.get('email_remetente_disparo', ""))
        email_s = st.text_input("Senha App", value=dados_banco.get('senha_email_disparo', ""), type="password")
    with cy:
        tr_key = st.text_input("Trello Key", value=dados_banco.get('trello_api_key', ""), type="password")
        tr_tok = st.text_input("Trello Token", value=dados_banco.get('trello_token', ""), type="password")
    with cz:
        tr_board = st.text_input("Trello Board ID", value=dados_banco.get('trello_board_id', ""))
        email_alert = st.text_input("E-mail Alertas", value=dados_banco.get('email_destino_alertas', ""))

    label_btn = "💾 SALVAR ALTERAÇÕES" if id_edicao else "🔥 ATIVAR MÁQUINA"
    if st.button(label_btn, use_container_width=True):
        dados = {
            "nome_empresa": nome_empresa, "data_vencimento": str(vencimento), "status_pagamento": "Em dia",
            "produto_oferecido": produto, "estados_alvo": estados_sel, "cidades_alvo": cidades_sel if cidades_sel else ["TODAS"],
            "grupos_cnae": [secoes_ibge[s] for s in secoes_sel], "cnaes_especificos": cnaes_sel if cnaes_sel else ["TODOS"],
            "meta_de_leads": meta, "email_remetente_disparo": email_r, "senha_email_disparo": email_s,
            "email_destino_alertas": email_alert, "trello_api_key": tr_key, "trello_token": tr_tok, "trello_board_id": tr_board,
            "dias_operacao": dias_sel, "horario_inicio": hora_inicio.strftime("%H:%M"), "horario_fim": hora_fim.strftime("%H:%M")
        }
        sb = get_supabase()
        if id_edicao:
            sb.table("clientes").update(dados).eq("id", id_edicao).execute()
        else:
            sb.table("clientes").insert(dados).execute()
        st.success("✅ Processado com sucesso!")
        st.balloons()

if __name__ == "__main__":
    executar_setup()