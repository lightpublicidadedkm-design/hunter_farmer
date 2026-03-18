import streamlit as st

# MODO TELA CHEIA ATIVADO PARA O CRM NÃO FICAR EXPRIMIDO
st.set_page_config(page_title="Painel DJM", layout="wide", initial_sidebar_state="expanded")

import pandas as pd
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText
from supabase import create_client, Client
from dotenv import load_dotenv

# --- NOVOS IMPORTS PARA EXECUTAR O ROBÔ ---
import subprocess
import sys
import time

load_dotenv()

# --- CONEXÃO SUPABASE ---
def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

supabase = get_supabase()

# --- FUNÇÃO DE ENVIO DE E-MAIL ---
def enviar_email(destinatario, assunto, corpo):
    try:
        remetente = os.getenv("EMAIL_REMETENTE")
        senha_app = os.getenv("EMAIL_SENHA_APP")
        msg = MIMEText(corpo)
        msg['Subject'] = assunto
        msg['From'] = remetente
        msg['To'] = destinatario
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(remetente, senha_app)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Erro ao enviar e-mail: {e}")
        return False

# --- TELA DE LOGIN ---
def tela_login():
    # Centraliza o login mesmo com a tela em modo wide
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.title("🔐 DJM Tecnologia - Login")
        aba1, aba2 = st.tabs(["Acessar", "Esqueci a Senha"])
        with aba1:
            usuario = st.text_input("Login/E-mail").strip()
            senha = st.text_input("Senha", type="password")
            if st.button("Entrar", use_container_width=True):
                if usuario == "derik" and senha == "djm2026":
                    st.session_state['logado'] = True
                    st.session_state['user_type'] = "admin"
                    st.rerun()
                
                res = supabase.table("usuarios").select("*, clientes(*)").ilike("login", usuario).eq("senha", senha).execute()
                if res.data:
                    user_data = res.data[0]
                    cliente = user_data.get('clientes')
                    if cliente:
                        venc = datetime.strptime(cliente['data_vencimento'], '%Y-%m-%d').date()
                        atraso = (datetime.now().date() - venc).days
                        if atraso > 30:
                            st.error(f"🛑 BLOQUEADO: Fatura vencida há {atraso} dias. Vencimento: {venc.strftime('%d/%m/%Y')}")
                            return
                    
                    st.session_state['logado'] = True
                    st.session_state['user_type'] = user_data['role']
                    st.session_state['user_info'] = user_data
                    st.session_state['cliente_id'] = user_data['cliente_id']
                    st.rerun()
                else:
                    st.error("Credenciais inválidas ou usuário não encontrado.")

        with aba2:
            email_recup = st.text_input("Informe seu e-mail de cadastro").strip()
            if st.button("Enviar Link de Recuperação"):
                res = supabase.table("usuarios").select("login").ilike("login", email_recup).execute()
                if res.data:
                    enviar_email(email_recup, "Recuperação de Senha - DJM", "Sua senha atual é: DJM@2026. Altere-a ao logar.")
                    st.success("E-mail de recuperação enviado com sucesso!")
                else:
                    st.error("E-mail não encontrado na base.")

# --- INICIALIZAÇÃO ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'menu_admin' not in st.session_state: st.session_state['menu_admin'] = "Dashboard"

if not st.session_state['logado']:
    tela_login()
else:
    st.sidebar.title("DJM Tecnologia")
    
    if st.session_state['user_type'] == "admin":
        mapa_indices = {"Dashboard": 0, "Criar Usuários": 1, "Configurações IA": 2}
        menu = st.sidebar.radio("Admin", list(mapa_indices.keys()), index=mapa_indices.get(st.session_state['menu_admin'], 0))
        st.session_state['menu_admin'] = menu
    else:
        # ATUALIZADO: Menu Cliente agora exibe CRM Pipeline
        menu = st.sidebar.radio("Menu Cliente", ["🏠 Início", "📊 CRM Pipeline", "⚙️ Configurações do Robô"])

    st.sidebar.divider()
    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()

    # --- TELAS ADMIN ---
    if st.session_state['user_type'] == "admin":
        if menu == "Dashboard":
            st.title("📊 Dashboard Master")
            c1, c2 = st.columns(2)
            c1.metric("Clientes", supabase.table("clientes").select("id", count='exact').execute().count)
            c2.metric("Usuários", supabase.table("usuarios").select("id", count='exact').execute().count)
        
        elif menu == "Criar Usuários":
            st.title("👥 Gestão de Usuários")
            aba_cad, aba_man = st.tabs(["Novo Acesso", "Manutenção"])
            clientes_db = supabase.table("clientes").select("id, nome_empresa").execute().data
            opcoes_clientes = {c['nome_empresa']: c['id'] for c in clientes_db}

            with aba_cad:
                with st.form("novo_user"):
                    login_u = st.text_input("Login")
                    senha_u = st.text_input("Senha")
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        cli_v = st.selectbox("Vincular ao Cliente", options=list(opcoes_clientes.keys()))
                    with col2:
                        st.write("")
                        if st.form_submit_button("➕ Novo"):
                            st.session_state['menu_admin'] = "Configurações IA"
                            st.rerun()
                    role_u = st.selectbox("Nível", ["cliente", "admin"])
                    if st.form_submit_button("Criar Usuário"):
                        supabase.table("usuarios").insert({"login": login_u, "senha": senha_u, "cliente_id": opcoes_clientes[cli_v], "role": role_u}).execute()
                        st.success("Criado!")

            with aba_man:
                usuarios_db = supabase.table("usuarios").select("*, clientes(nome_empresa)").execute().data
                if usuarios_db:
                    for u in usuarios_db:
                        emp_nome = u['clientes']['nome_empresa'] if u['clientes'] else "ADMIN MASTER"
                        with st.expander(f"👤 {u['login']} ({emp_nome})"):
                            with st.form(f"man_user_{u['id']}"):
                                new_login = st.text_input("Login", value=u['login'])
                                new_senha = st.text_input("Senha", value=u['senha'])
                                new_role = st.selectbox("Role", ["cliente", "admin"], index=0 if u['role']=='cliente' else 1)
                                c1, c2 = st.columns(2)
                                if c1.form_submit_button("💾 Salvar"):
                                    supabase.table("usuarios").update({"login": new_login, "senha": new_senha, "role": new_role}).eq("id", u['id']).execute()
                                    st.success("Salvo!")
                                    st.rerun()
                                if c2.form_submit_button("🗑️ Excluir"):
                                    supabase.table("usuarios").delete().eq("id", u['id']).execute()
                                    st.warning("Excluído!")
                                    st.rerun()

        elif menu == "Configurações IA":
            from setup_cliente import executar_setup
            executar_setup()

    # --- TELAS CLIENTE ---
    else:
        cliente_id = st.session_state.get('cliente_id')
        dados_cliente = supabase.table("clientes").select("*").eq("id", cliente_id).execute().data[0]

        if menu == "🏠 Início":
            st.title(f"🚀 Painel - {dados_cliente['nome_empresa']}")
            res_leads = supabase.table("leads_hunter").select("id", count='exact').eq("cliente_id", cliente_id).execute()
            c1, c2, c3 = st.columns(3)
            c1.metric("Leads Mapeados", res_leads.count if res_leads.count else 0)
            c2.metric("Status", dados_cliente['status_pagamento'])
            c3.metric("Vencimento", datetime.strptime(dados_cliente['data_vencimento'], '%Y-%m-%d').strftime('%d/%m/%Y'))

            # ==========================================
            # AÇÃO 1: BOTÃO PARA RODAR O ROBÔ HUNTER
            # ==========================================
            st.divider()
            st.subheader("🤖 Agente de Prospecção IA (Hunter)")
            st.write("Acione o seu robô Hunter para varrer o mercado e encontrar novos clientes baseados nas suas configurações.")
            
            if st.button("🚀 INICIAR CAÇADA DE LEADS AGORA", use_container_width=True, type="primary"):
                
                dias_op = dados_cliente.get('dias_operacao') or ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]
                h_ini = dados_cliente.get('horario_inicio') or "08:00"
                h_fim = dados_cliente.get('horario_fim') or "18:00"
                
                agora = datetime.now()
                mapa_dias = {0: "Segunda", 1: "Terça", 2: "Quarta", 3: "Quinta", 4: "Sexta", 5: "Sábado", 6: "Domingo"}
                dia_atual = mapa_dias[agora.weekday()]
                hora_atual = agora.strftime("%H:%M")

                if dia_atual not in dias_op or not (h_ini <= hora_atual <= h_fim):
                    st.warning(f"⚠️ **O robô está em repouso.**\n\nO expediente configurado é de **{', '.join(dias_op)}**, das **{h_ini}** às **{h_fim}**.\n*(Horário atual do servidor: {dia_atual} - {hora_atual})*")
                
                else:
                    with st.status("O Agente IA está trabalhando... (Isso pode levar alguns minutos)", expanded=True) as status:
                        
                        env_vars = os.environ.copy()
                        env_vars["PYTHONIOENCODING"] = "utf-8"
                        
                        processo = subprocess.Popen(
                            [sys.executable, "-u", "sales_hunter_simulador_teste.py", str(cliente_id)], 
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, 
                            text=True,
                            encoding='utf-8',
                            errors='replace',
                            env=env_vars
                        )
                        
                        for linha in processo.stdout:
                            if linha.strip():
                                st.code(linha.strip())
                        
                        processo.wait()
                        
                        if processo.returncode == 0:
                            status.update(label="Execução Finalizada com Sucesso!", state="complete", expanded=True)
                            st.success("✅ Busca concluída! Os logs foram mantidos na tela para você analisar e copiar.")
                        else:
                            status.update(label="Erro Crítico na Execução!", state="error", expanded=True)
                            st.error("❌ O robô parou devido a um erro. Leia os logs acima para descobrir o motivo.")

            # ==========================================
            # AÇÃO 2: NOVO BOTÃO PARA O ROBÔ FARMER (LINKEDIN)
            # ==========================================
            st.divider()
            st.subheader("🌾 Agente Executor (Farmer - LinkedIn)")
            st.write("Acione este robô para ler a agenda do dia e executar as visitas, curtidas e mensagens automáticas no LinkedIn.")
            
            if st.button("🤖 EXECUTAR TAREFAS DE HOJE NO LINKEDIN", use_container_width=True):
                with st.status("O Agente Farmer está conectando ao LinkedIn...", expanded=True) as status:
                    
                    env_vars = os.environ.copy()
                    env_vars["PYTHONIOENCODING"] = "utf-8"
                    
                    # Chama o script do Farmer
                    processo_farmer = subprocess.Popen(
                        [sys.executable, "-u", "sales_farmer_linkedin.py", str(cliente_id)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, 
                        text=True,
                        encoding='utf-8',
                        errors='replace',
                        env=env_vars
                    )
                    
                    for linha in processo_farmer.stdout:
                        if linha.strip():
                            st.code(linha.strip())
                    
                    processo_farmer.wait()
                    
                    if processo_farmer.returncode == 0:
                        status.update(label="Tarefas Concluídas!", state="complete", expanded=True)
                        st.success("✅ O robô finalizou o expediente no LinkedIn!")
                    else:
                        status.update(label="Erro no LinkedIn!", state="error", expanded=True)
                        st.error("❌ O robô encontrou um obstáculo no LinkedIn. Leia os logs acima.")

        # ==========================================
        # NOVO MÓDULO: CRM KANBAN (COM LAYOUT TIPO TRELLO)
        # ==========================================
        elif menu == "📊 CRM Pipeline":
            st.title("📊 CRM - Pipeline de Vendas")
            st.write("Gerencie seus leads e avance-os pelas etapas do funil de vendas.")

            # --- CSS MÁGICO PARA CRIAR A ROLAGEM HORIZONTAL E TRAVAR A LARGURA ---
            st.markdown("""
            <style>
                /* Transforma a tela em um painel com rolagem horizontal (Estilo Trello) */
                div[data-testid="stHorizontalBlock"]:has(h4) {
                    overflow-x: auto !important;
                    flex-wrap: nowrap !important;
                    padding-bottom: 20px;
                }
                /* Trava a largura de cada coluna para o texto não ser esmagado */
                div[data-testid="stHorizontalBlock"]:has(h4) > div[data-testid="column"] {
                    min-width: 280px !important;
                    max-width: 280px !important;
                    flex: 0 0 auto !important;
                    background-color: rgba(255, 255, 255, 0.03); /* Fundo sutil nas colunas */
                    padding: 15px;
                    border-radius: 8px;
                    margin-right: 15px;
                }
            </style>
            """, unsafe_allow_html=True)

            leads = supabase.table("leads_hunter").select("*").eq("cliente_id", cliente_id).execute().data
            
            if not leads:
                st.warning("Sem leads mapeados ainda. Inicie uma caçada na tela Início para encher seu funil.")
            else:
                # LISTA ATUALIZADA DE ESTÁGIOS INCLUINDO "LINKEDIN VISITADO"
                estagios = [
                    "🎯 Prospecção", 
                    "👀 LinkedIn Visitado", 
                    "💬 Contato Feito", 
                    "📅 Reunião Agendada", 
                    "📄 Proposta Enviada", 
                    "✅ Venda Fechada", 
                    "❌ Perdido"
                ]

                # Garante que leads antigos que só tinham "Prospecção" se encaixem no novo padrão
                for l in leads:
                    if l.get('status_funil') == "Prospecção":
                        l['status_funil'] = "🎯 Prospecção"
                    elif l.get('status_funil') not in estagios:
                        l['status_funil'] = "🎯 Prospecção"

                # Cria as 7 colunas dinâmicas usando toda a extensão da tela
                colunas = st.columns(len(estagios))
                
                for i, estagio in enumerate(estagios):
                    with colunas[i]:
                        leads_neste_estagio = [l for l in leads if l.get('status_funil') == estagio]
                        
                        # O h4 serve como "âncora" para o CSS aplicar o estilo correto
                        st.markdown(f"<h4 style='text-align: center; font-size: 16px; margin-bottom: 0px;'>{estagio}</h4>", unsafe_allow_html=True)
                        st.markdown(f"<p style='text-align: center; color: gray; font-size: 12px;'>{len(leads_neste_estagio)} leads</p>", unsafe_allow_html=True)
                        
                        for l in leads_neste_estagio:
                            with st.container(border=True):
                                st.markdown(f"<div style='font-size: 14px; font-weight: bold;'>{l['nome_empresa']}</div>", unsafe_allow_html=True)
                                st.caption(f"👤 {l.get('nome_socio', 'N/A')[:20]}") 
                                
                                with st.expander("Ver detalhes"):
                                    st.write(f"**Nicho:** {l.get('nicho_mercado', '')}")
                                    st.write(f"**Dor:** {l.get('dor_presumida', '')}")
                                    st.write(f"**E-mail:** {l.get('email', '')}")
                                
                                # BOTÕES DE AVANÇO RÁPIDO NO LUGAR DO SELECTBOX
                                c_voltar, c_avancar = st.columns(2)
                                with c_voltar:
                                    if i > 0: # Só mostra a seta voltar se NÃO for a primeira coluna
                                        if st.button("⬅️", key=f"back_{l['id']}", use_container_width=True, help="Voltar um estágio"):
                                            supabase.table("leads_hunter").update({"status_funil": estagios[i-1]}).eq("id", l['id']).execute()
                                            st.rerun()
                                with c_avancar:
                                    if i < len(estagios) - 1: # Só mostra a seta avançar se NÃO for a última coluna
                                        if st.button("➡️", key=f"fwd_{l['id']}", use_container_width=True, help="Avançar um estágio"):
                                            supabase.table("leads_hunter").update({"status_funil": estagios[i+1]}).eq("id", l['id']).execute()
                                            st.rerun()

        elif menu == "⚙️ Configurações do Robô":
            from setup_cliente import executar_setup
            executar_setup(cliente_id)