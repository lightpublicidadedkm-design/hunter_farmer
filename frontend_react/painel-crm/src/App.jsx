import React, { useState, useEffect, useRef } from 'react';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import { createClient } from '@supabase/supabase-js';
import { LayoutDashboard, Trello, Settings, LogOut, Rocket, Bot, Menu, BookOpen, Mic, Smartphone } from 'lucide-react';
import Select from 'react-select';

// --- CONFIGURAÇÃO DO SUPABASE ---
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

const estagiosPadrao = ['🎯 Prospecção', '👀 LinkedIn Visitado', '💬 Contato Feito', '📅 Reunião Agendada', '📄 Proposta Enviada', '✅ Venda Fechada', '❌ Perdido'];

export default function App() {
  const [usuarioLogado, setUsuarioLogado] = useState(null);
  const [dadosCliente, setDadosCliente] = useState(null);
  const [menuAtual, setMenuAtual] = useState('crm');
  
  // Controle de Menu Expandido/Oculto
  const [menuExpandido, setMenuExpandido] = useState(true);

  if (!usuarioLogado) {
    return <TelaLogin onLogin={setUsuarioLogado} setDadosCliente={setDadosCliente} />;
  }

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', backgroundColor: '#f4f5f7', fontFamily: 'system-ui, sans-serif', margin: 0, padding: 0, overflow: 'hidden' }}>
      
      {/* MENU LATERAL DINÂMICO */}
      <div style={{ 
        width: menuExpandido ? '250px' : '0px', 
        backgroundColor: '#172b4d', color: 'white', display: 'flex', flexDirection: 'column', 
        transition: 'width 0.3s ease', overflow: 'hidden', whiteSpace: 'nowrap', flexShrink: 0
      }}>
        <div style={{ padding: '20px', fontSize: '20px', fontWeight: 'bold', borderBottom: '1px solid #283e5f' }}>
          DJM Tecnologia
        </div>
        <nav style={{ flex: 1, padding: '20px 0' }}>
          <ItemMenu icone={<LayoutDashboard size={20} />} texto="Início" ativo={menuAtual === 'inicio'} onClick={() => setMenuAtual('inicio')} />
          <ItemMenu icone={<Trello size={20} />} texto="CRM Pipeline" ativo={menuAtual === 'crm'} onClick={() => setMenuAtual('crm')} />
          <ItemMenu icone={<Settings size={20} />} texto="Configurações" ativo={menuAtual === 'config'} onClick={() => setMenuAtual('config')} />
          <ItemMenu icone={<BookOpen size={20} />} texto="Playbook & IA" ativo={menuAtual === 'playbook'} onClick={() => setMenuAtual('playbook')} />
          <ItemMenu icone={<Smartphone size={20} />} texto="Minhas Conexões" ativo={menuAtual === 'conexoes'} onClick={() => setMenuAtual('conexoes')} />
          <ItemMenu icone={<Settings size={20} />} texto="Setup do Robô" ativo={menuAtual === 'config'} onClick={() => setMenuAtual('config')} />
        </nav>
        <div style={{ padding: '20px', borderTop: '1px solid #283e5f' }}>
          <ItemMenu icone={<LogOut size={20} />} texto="Sair" onClick={() => { setUsuarioLogado(null); setDadosCliente(null); }} />
        </div>
      </div>

      {/* ÁREA CENTRAL */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
        
        {/* BARRA SUPERIOR (TOP BAR) */}
        <div style={{ height: '60px', backgroundColor: 'white', borderBottom: '1px solid #dfe1e6', display: 'flex', alignItems: 'center', padding: '0 20px', gap: '15px', flexShrink: 0 }}>
          <button 
            onClick={() => setMenuExpandido(!menuExpandido)} 
            style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '5px' }}
            title="Ocultar/Mostrar Menu"
          >
            <Menu size={24} color="#172b4d" />
          </button>
          <strong style={{ fontSize: '16px', color: '#172b4d' }}>{dadosCliente?.nome_empresa || 'SaaS Admin'}</strong>
        </div>

        {/* CONTEÚDO DAS TELAS */}
        <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
          {menuAtual === 'inicio' && <TelaInicio cliente={dadosCliente} />}
          {menuAtual === 'crm' && <TelaCRM cliente={dadosCliente} />}
          {menuAtual === 'config' && <TelaConfig cliente={dadosCliente} />}
          {menuAtual === 'playbook' && <TelaPlaybook cliente={dadosCliente} />}
          {menuAtual === 'conexoes' && <TelaConexoes cliente={dadosCliente} />}          
        </div>
        
      </div>
    </div>
  );
}

// ==========================================
// COMPONENTES DE TELA
// ==========================================

function TelaLogin({ onLogin, setDadosCliente }) {
  const [login, setLogin] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState('');
  const [loading, setLoading] = useState(false);

  const fazerLogin = async (e) => {
    e.preventDefault();
    setLoading(true); setErro('');

    const { data, error } = await supabase.from('usuarios').select('*, clientes(*)').ilike('login', login).eq('senha', senha);
    if (error || !data || data.length === 0) {
      setErro('Credenciais inválidas ou usuário não encontrado.');
      setLoading(false); return;
    }

    const userData = data[0];
    if (userData.role === 'admin' && !userData.clientes) {
      onLogin(userData); setDadosCliente({ nome_empresa: 'Admin Master', id: 'admin' }); setLoading(false); return;
    }

    const cliente = userData.clientes;
    if (cliente && cliente.data_vencimento) {
      const difDias = Math.ceil((new Date().getTime() - new Date(cliente.data_vencimento).getTime()) / (1000 * 3600 * 24));
      if (difDias > 30) { setErro(`🛑 BLOQUEADO: Fatura vencida há ${difDias} dias.`); setLoading(false); return; }
    }

    setDadosCliente(cliente); onLogin(userData); setLoading(false);
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', width: '100vw', backgroundColor: '#f4f5f7', fontFamily: 'system-ui' }}>
      <div style={{ backgroundColor: 'white', padding: '40px', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', width: '400px' }}>
        <h2 style={{ textAlign: 'center', color: '#172b4d', marginBottom: '20px' }}>🔐 DJM Tecnologia</h2>
        {erro && <div style={{ backgroundColor: '#ffebe6', color: '#bf2600', padding: '10px', borderRadius: '4px', marginBottom: '15px', fontSize: '14px' }}>{erro}</div>}
        <form onSubmit={fazerLogin} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          <input type="text" placeholder="Login / E-mail" value={login} onChange={e => setLogin(e.target.value)} required style={{ padding: '12px', borderRadius: '4px', border: '1px solid #dfe1e6' }} />
          <input type="password" placeholder="Senha" value={senha} onChange={e => setSenha(e.target.value)} required style={{ padding: '12px', borderRadius: '4px', border: '1px solid #dfe1e6' }} />
          <button type="submit" disabled={loading} style={{ padding: '12px', backgroundColor: '#0052cc', color: 'white', border: 'none', borderRadius: '4px', fontWeight: 'bold', cursor: loading ? 'not-allowed' : 'pointer' }}>
            {loading ? 'Acessando...' : 'Entrar'}
          </button>
        </form>
      </div>
    </div>
  );
}

function ItemMenu({ icone, texto, ativo, onClick }) {
  return (
    <div onClick={onClick} style={{ display: 'flex', alignItems: 'center', gap: '15px', padding: '15px 20px', cursor: 'pointer', backgroundColor: ativo ? '#283e5f' : 'transparent', borderLeft: ativo ? '4px solid #4c9aff' : '4px solid transparent', transition: '0.2s' }}>
      {icone} <span style={{ fontWeight: ativo ? 'bold' : 'normal' }}>{texto}</span>
    </div>
  );
}

// --- TELA INÍCIO COM OS BOTÕES INTEGRADOS À API PYTHON ---
function TelaInicio({ cliente }) {
  const [totalLeads, setTotalLeads] = useState(0);
  const [statusRobo, setStatusRobo] = useState("");

  useEffect(() => {
    async function getCount() {
      const { count } = await supabase.from('leads_hunter').select('*', { count: 'exact', head: true }).eq('cliente_id', cliente.id);
      setTotalLeads(count || 0);
    }
    if (cliente && cliente.id !== 'admin') getCount();
  }, [cliente]);

  const chamarRobo = async (tipo) => {
    if (cliente.id === 'admin') { alert("O Admin não tem robôs."); return; }
    setStatusRobo(`Acordando o robô ${tipo}...`);

    try {
      const resposta = await fetch(`http://localhost:8000/api/${tipo}/${cliente.id}`, { method: 'POST' });
      const dados = await resposta.json();
      if (dados.status === 'sucesso') {
        setStatusRobo(`✅ ${dados.mensagem}`);
        setTimeout(() => setStatusRobo(""), 5000);
      }
    } catch (erro) {
      console.error(erro);
      setStatusRobo("❌ Erro ao contatar a API. O servidor Python está ligado?");
    }
  };

  return (
    <div style={{ padding: '40px' }}>
      <h1 style={{ color: '#172b4d', marginBottom: '30px' }}>🚀 Painel - Início</h1>
      <div style={{ display: 'flex', gap: '20px', marginBottom: '40px' }}>
        <CartaoMetrica titulo="Leads Mapeados" valor={totalLeads} cor="#0052cc" />
        <CartaoMetrica titulo="Status" valor={cliente?.status_pagamento || 'Ativo'} cor="#00875a" />
        <CartaoMetrica titulo="Vencimento" valor={cliente?.data_vencimento ? new Date(cliente.data_vencimento).toLocaleDateString('pt-BR') : 'N/A'} cor="#ff991f" />
      </div>

      {statusRobo && (
        <div style={{ padding: '15px', backgroundColor: '#e3fcef', color: '#006644', borderRadius: '8px', marginBottom: '20px', fontWeight: 'bold', border: '1px solid #79f2c0' }}>
          {statusRobo}
        </div>
      )}

      <div style={{ display: 'flex', gap: '30px' }}>
        <div style={{ flex: 1, backgroundColor: 'white', padding: '30px', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px', color: '#172b4d' }}><Rocket size={28} color="#0052cc" /> <h2>Agente Hunter</h2></div>
          <p style={{ color: '#5e6c84', marginBottom: '20px', fontSize: '15px' }}>Varrer o mercado e encontrar novos clientes baseados nas suas configurações.</p>
          <button onClick={() => chamarRobo('hunter')} style={{ width: '100%', padding: '15px', backgroundColor: '#0052cc', color: 'white', border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>🚀 INICIAR CAÇADA</button>
        </div>
        <div style={{ flex: 1, backgroundColor: 'white', padding: '30px', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px', color: '#172b4d' }}><Bot size={28} color="#00875a" /> <h2>Agente Farmer</h2></div>
          <p style={{ color: '#5e6c84', marginBottom: '20px', fontSize: '15px' }}>Executar visitas, curtidas e mensagens automáticas no LinkedIn.</p>
          <button onClick={() => chamarRobo('farmer')} style={{ width: '100%', padding: '15px', backgroundColor: '#00875a', color: 'white', border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>🤖 EXECUTAR TAREFAS</button>
        </div>
      </div>
    </div>
  );
}

function CartaoMetrica({ titulo, valor, cor }) {
  return (
    <div style={{ flex: 1, backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)', borderLeft: `5px solid ${cor}` }}>
      <div style={{ color: '#5e6c84', fontSize: '14px', fontWeight: 'bold', textTransform: 'uppercase', marginBottom: '10px' }}>{titulo}</div>
      <div style={{ color: '#172b4d', fontSize: '28px', fontWeight: 'bold' }}>{valor}</div>
    </div>
  );
}

// --- COMPONENTE: TELA DE CONFIGURAÇÕES (VERSÃO AVANÇADA COM IBGE) ---
// --- COMPONENTE: TELA DE CONFIGURAÇÕES (VERSÃO AVANÇADA COM DROPDOWNS E CANAIS) ---
// --- COMPONENTE: TELA DE CONFIGURAÇÕES (COM CADÊNCIA DE FUNIL) ---
function TelaConfig({ cliente }) {
  const [formData, setFormData] = useState({
    nome_empresa: '', produto_oferecido: '', meta_de_leads: 10, data_vencimento: '',
    dias_operacao: ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"], horario_inicio: '08:00', horario_fim: '18:00',
    estados_alvo: [], cidades_alvo: [], grupos_cnae: [], cnaes_especificos: [],
    canais_prospeccao: ['linkedin', 'email'], whatsapp_numero: '', linkedin_conta: '',
    email_remetente_disparo: '', senha_email_disparo: '', email_destino_alertas: '',
    trello_api_key: '', trello_token: '', trello_board_id: '',
    
    // NOVO: Processo de Funil / Cadência
    funil_visualizar_linkedin: true,
    funil_curtir_linkedin: false, funil_dias_curtir: 1,
    funil_enviar_email: false, funil_dias_email: 2,
    funil_conectar_linkedin: false, funil_dias_conectar: 3,
    funil_enviar_whatsapp: false, funil_dias_whatsapp: 2,
    funil_remarketing: false, funil_dias_remarketing: 180
  });

  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [mensagem, setMensagem] = useState(null);

  const [opcoesEstados, setOpcoesEstados] = useState([]);
  const [opcoesCidades, setOpcoesCidades] = useState([]);
  const [opcoesSecoes, setOpcoesSecoes] = useState([]);
  const [opcoesSubclasses, setOpcoesSubclasses] = useState([]);

  const diasSemana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];

  useEffect(() => {
    async function inicializar() {
      if (!cliente || cliente.id === 'admin') { setCarregando(false); return; }
      
      const { data } = await supabase.from('clientes').select('*').eq('id', cliente.id).single();
      if (data) {
        setFormData(prev => ({ 
          ...prev, ...data,
          // Garante que o placeholder do remarketing inicie correto se não houver no banco
          funil_dias_remarketing: data.funil_dias_remarketing || 180 
        }));
      }

      fetch("https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome")
        .then(res => res.json())
        .then(data => setOpcoesEstados(data.map(e => ({ value: e.sigla, label: `${e.sigla} - ${e.nome}` }))));

      fetch("https://servicodados.ibge.gov.br/api/v2/cnae/secoes")
        .then(res => res.json())
        .then(data => {
          const secoesOrdenadas = data.sort((a, b) => a.descricao.localeCompare(b.descricao));
          setOpcoesSecoes(secoesOrdenadas.map(s => ({ value: s.descricao, label: `Seção ${s.id}: ${s.descricao}` })));
        });

      setCarregando(false);
    }
    inicializar();
  }, [cliente]);

  useEffect(() => {
    async function buscarCidades() {
      if (!formData.estados_alvo || formData.estados_alvo.length === 0) { setOpcoesCidades([]); return; }
      let todasCidades = [];
      for (let sigla of formData.estados_alvo) {
        try {
          const res = await fetch(`https://servicodados.ibge.gov.br/api/v1/localidades/estados/${sigla}/municipios`);
          const cidades = await res.json();
          todasCidades.push(...cidades.map(c => ({ value: `${c.nome} - ${sigla}`, label: `${c.nome} - ${sigla}` })));
        } catch (e) { console.error(e); }
      }
      setOpcoesCidades(todasCidades.sort((a, b) => a.label.localeCompare(b.label)));
    }
    buscarCidades();
  }, [formData.estados_alvo]);

  useEffect(() => {
    async function buscarSubclasses() {
      if (!formData.grupos_cnae || formData.grupos_cnae.length === 0) { setOpcoesSubclasses([]); return; }
      let todasSubclasses = [];
      const descricoesBuscadas = formData.grupos_cnae;
      
      for (let opSecao of opcoesSecoes) {
        if (descricoesBuscadas.includes(opSecao.value)) {
          const idSecao = opSecao.label.split(':')[0].replace('Seção ', '');
          try {
            const res = await fetch(`https://servicodados.ibge.gov.br/api/v2/cnae/secoes/${idSecao}/subclasses`);
            const subs = await res.json();
            todasSubclasses.push(...subs.map(s => ({ value: `${s.id} - ${s.descricao}`, label: `${s.id} - ${s.descricao}` })));
          } catch (e) { console.error(e); }
        }
      }
      const unicas = Array.from(new Set(todasSubclasses.map(a => a.value)))
        .map(v => todasSubclasses.find(a => a.value === v))
        .sort((a, b) => a.label.localeCompare(b.label));
      
      setOpcoesSubclasses(unicas);
    }
    if (opcoesSecoes.length > 0) buscarSubclasses();
  }, [formData.grupos_cnae, opcoesSecoes]);

  const toggleArrayItem = (campo, valor) => {
    setFormData(prev => {
      const atual = prev[campo] || [];
      const novoArray = atual.includes(valor) ? atual.filter(i => i !== valor) : [...atual, valor];
      return { ...prev, [campo]: novoArray };
    });
  };

  // VALIDAÇÃO MATEMÁTICA DO REMARKETING
  const calcularSomaDiasFunil = () => {
    let soma = 0;
    if (formData.funil_curtir_linkedin) soma += Number(formData.funil_dias_curtir) || 0;
    if (formData.funil_enviar_email) soma += Number(formData.funil_dias_email) || 0;
    if (formData.funil_conectar_linkedin) soma += Number(formData.funil_dias_conectar) || 0;
    if (formData.funil_enviar_whatsapp) soma += Number(formData.funil_dias_whatsapp) || 0;
    return soma;
  };

  const calcularMinimoRemarketing = () => {
    return calcularSomaDiasFunil() + 30;
  };

  const salvarConfig = async (e) => {
    e.preventDefault();
    setSalvando(true); setMensagem(null);

    // Bloqueia o salvamento se o remarketing estiver ativo com dias abaixo do mínimo
    if (formData.funil_remarketing) {
      const minDias = calcularMinimoRemarketing();
      if (Number(formData.funil_dias_remarketing) < minDias) {
        setMensagem({ tipo: 'erro', texto: `⚠️ O remarketing exige no mínimo ${minDias} dias (soma das etapas ativas + 30 dias). Ajuste o valor e tente novamente.` });
        setSalvando(false);
        return;
      }
    }

    const dadosParaSalvar = {
      ...formData,
      cidades_alvo: formData.cidades_alvo.length > 0 ? formData.cidades_alvo : ["TODAS"],
      cnaes_especificos: formData.cnaes_especificos.length > 0 ? formData.cnaes_especificos : ["TODOS"]
    };

    const { error } = await supabase.from('clientes').update(dadosParaSalvar).eq('id', cliente.id);

    setSalvando(false);
    if (error) setMensagem({ tipo: 'erro', texto: 'Erro ao salvar: ' + error.message });
    else {
      setMensagem({ tipo: 'sucesso', texto: '✅ Configurações e Cadência salvas com sucesso!' });
      setTimeout(() => setMensagem(null), 5000);
    }
  };

  const customStyles = {
    control: (base) => ({ ...base, borderColor: '#dfe1e6', padding: '2px', fontSize: '14px' }),
    menu: (base) => ({ ...base, fontSize: '14px' })
  };

  if (carregando) return <h2 style={{ padding: '40px' }}>⏳ Carregando banco e IBGE...</h2>;
  if (cliente?.id === 'admin') return <div style={{ padding: '40px' }}><h2>Acesse como cliente para ver esta tela.</h2></div>;

  return (
    <div style={{ padding: '40px', maxWidth: '900px', margin: '0 auto', display: 'flex', flexDirection: 'column' }}>
      <h1 style={{ color: '#172b4d', margin: '0 0 10px 0' }}>🏗️ Setup Avançado do Robô</h1>
      <p style={{ color: '#5e6c84', margin: '0 0 30px 0' }}>Edite os parâmetros de inteligência da empresa: <b>{formData.nome_empresa}</b></p>

      {mensagem && (
        <div style={{ padding: '15px', marginBottom: '20px', borderRadius: '6px', fontWeight: 'bold', backgroundColor: mensagem.tipo === 'sucesso' ? '#e3fcef' : '#ffebe6', color: mensagem.tipo === 'sucesso' ? '#006644' : '#bf2600', border: `1px solid ${mensagem.tipo === 'sucesso' ? '#79f2c0' : '#ff8f73'}` }}>
          {mensagem.texto}
        </div>
      )}

      <form onSubmit={salvarConfig} style={{ backgroundColor: 'white', padding: '30px', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)', display: 'flex', flexDirection: 'column', gap: '30px' }}>
        
        {/* SESSÃO: CANAIS DE COMUNICAÇÃO */}
        <div>
          <h3 style={{ color: '#172b4d', borderBottom: '1px solid #dfe1e6', paddingBottom: '10px', marginBottom: '15px' }}>🚀 Canais Ativos da Empresa</h3>
          <div style={{ display: 'flex', gap: '20px', marginBottom: '20px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer', fontWeight: 'bold', color: '#172b4d' }}>
              <input type="checkbox" checked={(formData.canais_prospeccao || []).includes('linkedin')} onChange={() => toggleArrayItem('canais_prospeccao', 'linkedin')} style={{ width: '18px', height: '18px' }} /> 🔵 LinkedIn
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer', fontWeight: 'bold', color: '#172b4d' }}>
              <input type="checkbox" checked={(formData.canais_prospeccao || []).includes('whatsapp')} onChange={() => toggleArrayItem('canais_prospeccao', 'whatsapp')} style={{ width: '18px', height: '18px' }} /> 🟢 WhatsApp
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer', fontWeight: 'bold', color: '#172b4d' }}>
              <input type="checkbox" checked={(formData.canais_prospeccao || []).includes('email')} onChange={() => toggleArrayItem('canais_prospeccao', 'email')} style={{ width: '18px', height: '18px' }} /> ✉️ E-mail
            </label>
          </div>
          <div style={{ display: 'flex', gap: '20px' }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 'bold', color: '#5e6c84', marginBottom: '5px' }}>Conta LinkedIn da Empresa</label>
              <input type="text" placeholder="Ex: joao.silva" value={formData.linkedin_conta} onChange={e => setFormData({...formData, linkedin_conta: e.target.value})} style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #dfe1e6' }} />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 'bold', color: '#5e6c84', marginBottom: '5px' }}>Número do WhatsApp (Com DDD)</label>
              <input type="text" placeholder="Ex: 11999998888" value={formData.whatsapp_numero} onChange={e => setFormData({...formData, whatsapp_numero: e.target.value})} style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #dfe1e6' }} />
            </div>
          </div>
        </div>

        {/* NOVA SESSÃO: PROCESSO DO FUNIL (CADÊNCIA) */}
        <div>
          <h3 style={{ color: '#172b4d', borderBottom: '1px solid #dfe1e6', paddingBottom: '10px', marginBottom: '15px' }}>🔄 Cadência de Prospecção (Flow)</h3>
          <p style={{ fontSize: '13px', color: 'gray', marginBottom: '20px' }}>Configure a ordem e os intervalos entre as ações dos Agentes. Se uma etapa não for marcada, o robô pulará automaticamente para a próxima ativa.</p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            
            {/* ETAPA 1 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px', backgroundColor: '#f4f5f7', padding: '15px', borderRadius: '6px' }}>
              <input type="checkbox" checked={formData.funil_visualizar_linkedin} onChange={e => setFormData({...formData, funil_visualizar_linkedin: e.target.checked})} style={{ width: '18px', height: '18px' }} />
              <strong style={{ color: '#172b4d', fontSize: '14px', width: '280px' }}>1. Visualizar perfil no LinkedIn</strong>
              <span style={{ fontSize: '13px', color: '#5e6c84' }}>Ação inicial (Dia 0)</span>
            </div>

            {/* ETAPA 2 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px', backgroundColor: '#f4f5f7', padding: '15px', borderRadius: '6px' }}>
              <input type="checkbox" checked={formData.funil_curtir_linkedin} onChange={e => setFormData({...formData, funil_curtir_linkedin: e.target.checked})} style={{ width: '18px', height: '18px' }} />
              <strong style={{ color: '#172b4d', fontSize: '14px', width: '280px' }}>2. Curtir último Post/Comentário</strong>
              {formData.funil_curtir_linkedin && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '13px', color: '#5e6c84' }}>Aguardar</span>
                  <input type="number" min="0" value={formData.funil_dias_curtir} onChange={e => setFormData({...formData, funil_dias_curtir: e.target.value})} style={{ width: '60px', padding: '5px', borderRadius: '4px', border: '1px solid #dfe1e6' }} />
                  <span style={{ fontSize: '13px', color: '#5e6c84' }}>dias após a etapa anterior</span>
                </div>
              )}
            </div>

            {/* ETAPA 3 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px', backgroundColor: '#f4f5f7', padding: '15px', borderRadius: '6px' }}>
              <input type="checkbox" checked={formData.funil_enviar_email} onChange={e => setFormData({...formData, funil_enviar_email: e.target.checked})} style={{ width: '18px', height: '18px' }} />
              <strong style={{ color: '#172b4d', fontSize: '14px', width: '280px' }}>3. Enviar E-mail de Disparo</strong>
              {formData.funil_enviar_email && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '13px', color: '#5e6c84' }}>Aguardar</span>
                  <input type="number" min="0" value={formData.funil_dias_email} onChange={e => setFormData({...formData, funil_dias_email: e.target.value})} style={{ width: '60px', padding: '5px', borderRadius: '4px', border: '1px solid #dfe1e6' }} />
                  <span style={{ fontSize: '13px', color: '#5e6c84' }}>dias após a etapa anterior</span>
                </div>
              )}
            </div>

            {/* ETAPA 4 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px', backgroundColor: '#f4f5f7', padding: '15px', borderRadius: '6px' }}>
              <input type="checkbox" checked={formData.funil_conectar_linkedin} onChange={e => setFormData({...formData, funil_conectar_linkedin: e.target.checked})} style={{ width: '18px', height: '18px' }} />
              <strong style={{ color: '#172b4d', fontSize: '14px', width: '280px' }}>4. Enviar Conexão c/ Nota (LinkedIn)</strong>
              {formData.funil_conectar_linkedin && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '13px', color: '#5e6c84' }}>Aguardar</span>
                  <input type="number" min="0" value={formData.funil_dias_conectar} onChange={e => setFormData({...formData, funil_dias_conectar: e.target.value})} style={{ width: '60px', padding: '5px', borderRadius: '4px', border: '1px solid #dfe1e6' }} />
                  <span style={{ fontSize: '13px', color: '#5e6c84' }}>dias após a etapa anterior</span>
                </div>
              )}
            </div>

            {/* ETAPA 5 */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px', backgroundColor: '#f4f5f7', padding: '15px', borderRadius: '6px' }}>
              <input type="checkbox" checked={formData.funil_enviar_whatsapp} onChange={e => setFormData({...formData, funil_enviar_whatsapp: e.target.checked})} style={{ width: '18px', height: '18px' }} />
              <strong style={{ color: '#172b4d', fontSize: '14px', width: '280px' }}>5. Enviar Mensagem via WhatsApp</strong>
              {formData.funil_enviar_whatsapp && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '13px', color: '#5e6c84' }}>Aguardar</span>
                  <input type="number" min="0" value={formData.funil_dias_whatsapp} onChange={e => setFormData({...formData, funil_dias_whatsapp: e.target.value})} style={{ width: '60px', padding: '5px', borderRadius: '4px', border: '1px solid #dfe1e6' }} />
                  <span style={{ fontSize: '13px', color: '#5e6c84' }}>dias após a etapa anterior</span>
                </div>
              )}
            </div>

            {/* ETAPA 6: REMARKETING */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '15px', backgroundColor: '#e3fcef', border: '1px solid #79f2c0', padding: '15px', borderRadius: '6px', marginTop: '10px' }}>
              <input type="checkbox" checked={formData.funil_remarketing} onChange={e => setFormData({...formData, funil_remarketing: e.target.checked})} style={{ width: '18px', height: '18px' }} />
              <strong style={{ color: '#006644', fontSize: '14px', width: '280px' }}>6. Remarketing (Reaquecer Lead Frio)</strong>
              {formData.funil_remarketing && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '13px', color: '#006644' }}>Aguardar</span>
                  <input type="number" placeholder="180" value={formData.funil_dias_remarketing} onChange={e => setFormData({...formData, funil_dias_remarketing: e.target.value})} style={{ width: '70px', padding: '5px', borderRadius: '4px', border: '1px solid #79f2c0' }} />
                  <span style={{ fontSize: '13px', color: '#006644' }}>
                    dias após última ação (Mínimo exigido: {calcularMinimoRemarketing()} dias)
                  </span>
                </div>
              )}
            </div>

          </div>
        </div>

        {/* ... OUTRAS SESSÕES (Metas, IBGE, Credenciais) ... */}
        {/* Adicione aqui as divisões de Segmentação que já criamos no passo anterior com os dropdowns */}
        
        <button 
          type="submit" disabled={salvando}
          style={{ width: '100%', padding: '15px', backgroundColor: '#0052cc', color: 'white', border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: salvando ? 'not-allowed' : 'pointer', fontSize: '16px', marginTop: '10px' }}
        >
          {salvando ? '💾 PROCESSANDO...' : '💾 SALVAR TODAS AS ALTERAÇÕES'}
        </button>

      </form>
    </div>
  );
}

// --- COMPONENTE TELA CRM (COM SCROLL GLOBAL DE TECLADO) ---
function TelaCRM({ cliente }) {
  const [dados, setDados] = useState(null);
  const [carregando, setCarregando] = useState(true);
  const [mostrarArquivados, setMostrarArquivados] = useState({});
  
  const scrollRef = useRef(null);

  useEffect(() => {
    async function carregarLeads() {
      if (!cliente || cliente.id === 'admin') { setCarregando(false); return; }
      const { data: leadsBanco } = await supabase.from('leads_hunter').select('*').eq('cliente_id', cliente.id);
      if (!leadsBanco) return;

      const estrutura = { estagios: {}, leads: {}, ordemEstagios: estagiosPadrao };
      estagiosPadrao.forEach(t => { estrutura.estagios[t] = { id: t, titulo: t, leadIds: [], arquivadosIds: [] }; });

      leadsBanco.forEach(lead => {
        const idStr = String(lead.id);
        const status = lead.status_funil || '🎯 Prospecção';
        const isArq = status.endsWith(' - Arquivado') || status === '🗄️ Arquivado';
        let colOrig = status.replace(' - Arquivado', '');
        if (status === '🗄️ Arquivado') colOrig = '🎯 Prospecção';
        const colCerta = estagiosPadrao.includes(colOrig) ? colOrig : '🎯 Prospecção';

        estrutura.leads[idStr] = { id: idStr, empresa: lead.nome_empresa, socio: lead.nome_socio || 'N/A', dor: lead.dor_presumida || 'Não mapeada' };
        if (isArq) estrutura.estagios[colCerta].arquivadosIds.push(idStr);
        else estrutura.estagios[colCerta].leadIds.push(idStr);
      });
      setDados(estrutura); setCarregando(false);
    }
    carregarLeads();
  }, [cliente]);

  // NOVO: Ouvinte de teclado global (Funciona sem precisar clicar na div)
  useEffect(() => {
    const handleGlobalKeyDown = (e) => {
      if (!scrollRef.current) return;
      if (e.key === 'ArrowRight') {
        scrollRef.current.scrollBy({ left: 320, behavior: 'smooth' });
      } else if (e.key === 'ArrowLeft') {
        scrollRef.current.scrollBy({ left: -320, behavior: 'smooth' });
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  const arquivarLead = async (lId, cId) => {
    if (!window.confirm("Arquivar lead?")) return;
    const n = { ...dados }; const i = n.estagios[cId].leadIds.indexOf(lId);
    if (i > -1) { n.estagios[cId].leadIds.splice(i, 1); n.estagios[cId].arquivadosIds.push(lId); setDados({ ...n }); }
    await supabase.from('leads_hunter').update({ status_funil: `${cId} - Arquivado` }).eq('id', lId);
  };

  const restaurarLead = async (lId, cId) => {
    const n = { ...dados }; const i = n.estagios[cId].arquivadosIds.indexOf(lId);
    if (i > -1) { n.estagios[cId].arquivadosIds.splice(i, 1); n.estagios[cId].leadIds.push(lId); setDados({ ...n }); }
    await supabase.from('leads_hunter').update({ status_funil: cId }).eq('id', lId);
  };

  const onDragEnd = async (res) => {
    const { destination, source, draggableId } = res;
    if (!destination || (destination.droppableId === source.droppableId && destination.index === source.index)) return;

    const colO = dados.estagios[source.droppableId]; const colD = dados.estagios[destination.droppableId];
    const n = { ...dados }; const idsO = Array.from(colO.leadIds); idsO.splice(source.index, 1);
    
    if (colO === colD) {
      idsO.splice(destination.index, 0, draggableId); n.estagios[colO.id].leadIds = idsO;
    } else {
      const idsD = Array.from(colD.leadIds); idsD.splice(destination.index, 0, draggableId);
      n.estagios[colO.id].leadIds = idsO; n.estagios[colD.id].leadIds = idsD;
      await supabase.from('leads_hunter').update({ status_funil: colD.id }).eq('id', draggableId);
    }
    setDados(n);
  };

  if (carregando) return <h2 style={{padding: '40px'}}>⏳ Carregando Kanban...</h2>;

  return (
    <div style={{ padding: '40px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <h1 style={{ color: '#172b4d', marginBottom: '20px' }}>📊 Pipeline de Vendas</h1>
      <p style={{ color: 'gray', marginTop: '-15px', marginBottom: '20px' }}>Dica: Use as setas ⬅️ ➡️ do teclado para navegar entre as colunas.</p>
      
      <DragDropContext onDragEnd={onDragEnd}>
        <div 
          ref={scrollRef}
          style={{ display: 'flex', gap: '20px', overflowX: 'auto', paddingBottom: '20px', flex: 1 }}
        >
          {dados.ordemEstagios.map((estId) => {
            const col = dados.estagios[estId];
            return (
              <div key={col.id} style={{ backgroundColor: '#ebecf0', borderRadius: '8px', minWidth: '300px', maxWidth: '300px', padding: '15px', display: 'flex', flexDirection: 'column' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
                  <h3 style={{ fontSize: '15px', color: '#172b4d', margin: 0 }}>{col.titulo} <span style={{ color: 'gray', fontSize: '12px' }}>({col.leadIds.length})</span></h3>
                  {col.arquivadosIds.length > 0 && (
                    <button onClick={() => setMostrarArquivados(p => ({ ...p, [col.id]: !p[col.id] }))} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '11px', color: '#5e6c84', fontWeight: 'bold' }}>
                      {mostrarArquivados[col.id] ? '🙈 Ocultar' : `👁️ Arquivados (${col.arquivadosIds.length})`}
                    </button>
                  )}
                </div>
                
                <Droppable droppableId={col.id}>
                  {(prov) => (
                    <div ref={prov.innerRef} {...prov.droppableProps} style={{ minHeight: '20px', flexGrow: 1 }}>
                      {col.leadIds.map((id, idx) => {
                        const l = dados.leads[id];
                        return (
                          <Draggable key={l.id} draggableId={l.id} index={idx}>
                            {(prov, snap) => (
                              <div ref={prov.innerRef} {...prov.draggableProps} {...prov.dragHandleProps} style={{ position: 'relative', padding: '16px', margin: '0 0 12px 0', backgroundColor: 'white', borderRadius: '6px', borderLeft: '4px solid #0052cc', boxShadow: snap.isDragging ? '0 5px 10px rgba(0,0,0,0.2)' : '0 1px 3px rgba(0,0,0,0.1)', ...prov.draggableProps.style }}>
                                <button onClick={() => arquivarLead(l.id, col.id)} style={{ position: 'absolute', top: '10px', right: '10px', background: 'none', border: 'none', cursor: 'pointer', fontSize: '16px', opacity: '0.6' }}>📦</button>
                                <strong style={{ display: 'block', color: '#172b4d', fontSize: '14px', paddingRight: '20px' }}>{l.empresa}</strong>
                                <span style={{ fontSize: '12px', color: '#5e6c84' }}>👤 {l.socio.substring(0, 20)}</span><br/>
                                <span style={{ fontSize: '12px', color: '#ff5630', display: 'block', marginTop: '5px' }}>Dor: {l.dor.length > 90 ? l.dor.substring(0, 90) + '...' : l.dor}</span>
                              </div>
                            )}
                          </Draggable>
                        );
                      })}
                      {prov.placeholder}
                    </div>
                  )}
                </Droppable>
              </div>
            );
          })}
        </div>
      </DragDropContext>
    </div>
  );
}

// ==========================================
// TELA: PLAYBOOK E CLONAGEM DE VOZ
// ==========================================
function TelaPlaybook({ cliente }) {
  const [salvando, setSalvando] = useState(false);
  const [mensagem, setMensagem] = useState(null);
  
  // Estrutura de Dados
  const [objecoes, setObjecoes] = useState([
    { id: 1, gatilho: 'Tá caro / Sem orçamento', resposta: '' },
    { id: 2, gatilho: 'Já tenho fornecedor', resposta: '' },
    { id: 3, gatilho: 'Me liga mês que vem', resposta: '' }
  ]);
  
  const [agendamento, setAgendamento] = useState({ ativo: false, link_agenda: '' });
  const [posVenda, setPosVenda] = useState({ ativo: false, meses: 6, copy: '' });

  // Carregar do Banco
  useEffect(() => {
    async function carregar() {
      if (!cliente || cliente.id === 'admin') return;
      const { data } = await supabase.from('clientes').select('playbook_objecoes, playbook_agendamento, playbook_pos_venda').eq('id', cliente.id).single();
      
      if (data) {
        if (data.playbook_objecoes && data.playbook_objecoes.length > 0) setObjecoes(data.playbook_objecoes);
        if (data.playbook_agendamento) setAgendamento(data.playbook_agendamento);
        if (data.playbook_pos_venda) setPosVenda(data.playbook_pos_venda);
      }
    }
    carregar();
  }, [cliente]);

  const salvarPlaybook = async (e) => {
    e.preventDefault();
    setSalvando(true);
    
    const { error } = await supabase.from('clientes').update({
      playbook_objecoes: objecoes,
      playbook_agendamento: agendamento,
      playbook_pos_venda: posVenda
    }).eq('id', cliente.id);

    setSalvando(false);
    if (error) setMensagem({ tipo: 'erro', texto: 'Erro ao salvar: ' + error.message });
    else {
      setMensagem({ tipo: 'sucesso', texto: '✅ Playbook da Inteligência Artificial atualizado!' });
      setTimeout(() => setMensagem(null), 5000);
    }
  };

  const sugerirRespostaIA = (index, gatilho) => {
    const novasObjecoes = [...objecoes];
    const sugestoes = {
      'Tá caro / Sem orçamento': "Entendo perfeitamente. A maioria dos nossos parceiros pensou o mesmo no início. Mas e se eu te mostrar como a nossa solução se paga nos primeiros 60 dias apenas com a economia gerada? Faz sentido um papo de 10 minutos para eu provar isso?",
      'Já tenho fornecedor': "Que ótimo! Sinal de que vocês já entendem o valor disso. O nosso objetivo não é substituir seu fornecedor agora, mas sim te apresentar uma 'opção B' no mercado. Tem espaço na agenda quinta para um café virtual rápido?",
      'Me liga mês que vem': "Sem problemas, a rotina é corrida mesmo! Vou colocar um lembrete aqui. Só para eu não te tomar tempo no mês que vem com algo que não faz sentido: qual é a sua maior prioridade hoje nesse setor?"
    };
    
    novasObjecoes[index].resposta = sugestoes[gatilho] || "Entendo o seu ponto. Posso te enviar um material rápido por aqui mesmo só para você avaliar com calma quando puder?";
    setObjecoes(novasObjecoes);
  };

  // NOVA FUNÇÃO: Sugestão de IA para o Upsell / Pós-venda
  const sugerirUpsellIA = () => {
    setPosVenda({
      ...posVenda,
      copy: "Olá! Tudo bem? Vi aqui no meu sistema que já faz um tempo desde a nossa última parceria. Passando para saber como estão os resultados por aí e compartilhar que lançamos algumas novidades que podem escalar ainda mais a sua operação. Faz sentido um bate-papo rápido esta semana?"
    });
  };

  return (
    <div style={{ padding: '40px', maxWidth: '900px', margin: '0 auto' }}>
      <h1 style={{ color: '#172b4d', margin: '0 0 10px 0' }}>📚 Sales Playbook & Cérebro IA</h1>
      <p style={{ color: '#5e6c84', margin: '0 0 30px 0' }}>Ensine o seu Agente a contornar objeções, agendar reuniões e enviar áudios humanizados.</p>

      {mensagem && (
        <div style={{ padding: '15px', marginBottom: '20px', borderRadius: '6px', fontWeight: 'bold', backgroundColor: mensagem.tipo === 'sucesso' ? '#e3fcef' : '#ffebe6', color: mensagem.tipo === 'sucesso' ? '#006644' : '#bf2600', border: `1px solid ${mensagem.tipo === 'sucesso' ? '#79f2c0' : '#ff8f73'}` }}>
          {mensagem.texto}
        </div>
      )}

      <form onSubmit={salvarPlaybook} style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
        
        {/* 1. CLONAGEM DE VOZ */}
        <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)', borderLeft: '4px solid #8e44ad' }}>
          <h3 style={{ color: '#172b4d', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Mic size={24} color="#8e44ad" /> Clonagem de Voz (WhatsApp)
          </h3>
          <p style={{ fontSize: '13px', color: 'gray', marginBottom: '20px' }}>
            Faça upload de um áudio limpo de 1 minuto da sua voz. A IA enviará áudios no meio da conversa como se fosse você.
          </p>
          <div style={{ padding: '20px', border: '2px dashed #dfe1e6', borderRadius: '8px', textAlign: 'center', backgroundColor: '#f4f5f7' }}>
            <input type="file" accept="audio/*" id="audio-upload" style={{ display: 'none' }} onChange={(e) => alert("O upload de áudio será conectado à API de voz na próxima etapa!")} />
            <label htmlFor="audio-upload" style={{ cursor: 'pointer', padding: '10px 20px', backgroundColor: '#8e44ad', color: 'white', borderRadius: '4px', fontWeight: 'bold', display: 'inline-block' }}>
              🎙️ Enviar Áudio Base (.mp3)
            </label>
            <p style={{ fontSize: '12px', marginTop: '10px', color: '#5e6c84' }}>Ainda não configurado. Requer integração no backend.</p>
          </div>
        </div>

        {/* 2. QUEBRA DE OBJEÇÕES */}
        <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)' }}>
          <h3 style={{ color: '#172b4d', borderBottom: '1px solid #dfe1e6', paddingBottom: '10px', marginBottom: '20px' }}>🛡️ Quebra de Objeções (Treinamento)</h3>
          <p style={{ fontSize: '13px', color: 'gray', marginBottom: '20px' }}>Como o robô deve responder sozinho quando o lead recuar no WhatsApp?</p>
          
          {objecoes.map((obj, index) => (
            <div key={obj.id} style={{ marginBottom: '25px', backgroundColor: '#f9fafc', padding: '15px', borderRadius: '8px', border: '1px solid #dfe1e6' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                <strong style={{ color: '#172b4d' }}>🚨 Quando o lead disser: "{obj.gatilho}"</strong>
                <button type="button" onClick={() => sugerirRespostaIA(index, obj.gatilho)} style={{ background: 'none', border: 'none', color: '#0052cc', fontWeight: 'bold', cursor: 'pointer', fontSize: '13px' }}>
                  ✨ Sugerir com IA
                </button>
              </div>
              <textarea 
                rows="3" 
                placeholder="Ex: Entendo perfeitamente, a maioria diz isso. Mas veja bem..."
                value={obj.resposta} 
                onChange={(e) => {
                  const novas = [...objecoes];
                  novas[index].resposta = e.target.value;
                  setObjecoes(novas);
                }}
                style={{ width: '100%', padding: '12px', borderRadius: '4px', border: '1px solid #dfe1e6', fontSize: '14px', fontFamily: 'system-ui', resize: 'vertical' }} 
              />
            </div>
          ))}
        </div>

        {/* 3. CONCIERGE E AGENDAMENTO */}
        <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)' }}>
          <h3 style={{ color: '#172b4d', borderBottom: '1px solid #dfe1e6', paddingBottom: '10px', marginBottom: '15px' }}>📅 Concierge de Agendamento</h3>
          
          <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', fontWeight: 'bold', color: '#172b4d', marginBottom: '15px' }}>
            <input type="checkbox" checked={agendamento.ativo} onChange={e => setAgendamento({...agendamento, ativo: e.target.checked})} style={{ width: '18px', height: '18px' }} /> 
            Permitir que o robô tente agendar reuniões (Enviar Link)
          </label>
          
          {agendamento.ativo && (
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 'bold', color: '#5e6c84', marginBottom: '5px' }}>Link da sua Agenda (Calendly, Google Calendar, etc)</label>
              <input type="url" placeholder="Ex: https://calendly.com/minha-empresa/reuniao-30-min" value={agendamento.link_agenda} onChange={e => setAgendamento({...agendamento, link_agenda: e.target.value})} style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #dfe1e6' }} />
              <span style={{ fontSize: '12px', color: 'gray', marginTop: '5px', display: 'block' }}>O robô usará este link quando o cliente demonstrar interesse na resposta.</span>
            </div>
          )}
        </div>

        {/* 4. UPSELL E PÓS-VENDA AJUSTADO */}
        <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)', borderLeft: '4px solid #00875a' }}>
          <h3 style={{ color: '#172b4d', borderBottom: '1px solid #dfe1e6', paddingBottom: '10px', marginBottom: '15px' }}>💸 Automação de Pós-Venda (Upsell/LTV)</h3>
          
          <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', fontWeight: 'bold', color: '#172b4d', marginBottom: '20px' }}>
            <input type="checkbox" checked={posVenda.ativo} onChange={e => setPosVenda({...posVenda, ativo: e.target.checked})} style={{ width: '18px', height: '18px' }} /> 
            Ativar re-engajamento para quem já comprou (Venda Fechada)
          </label>
          
          {posVenda.ativo && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              
              <div style={{ width: '200px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 'bold', color: '#5e6c84', marginBottom: '5px' }}>Após quantos meses?</label>
                <input type="number" min="1" value={posVenda.meses} onChange={e => setPosVenda({...posVenda, meses: e.target.value})} style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #dfe1e6' }} />
              </div>
              
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px' }}>
                  <label style={{ display: 'block', fontSize: '13px', fontWeight: 'bold', color: '#5e6c84' }}>Mensagem de Upsell (Cross-sell)</label>
                  <button type="button" onClick={sugerirUpsellIA} style={{ background: 'none', border: 'none', color: '#0052cc', fontWeight: 'bold', cursor: 'pointer', fontSize: '13px' }}>
                    ✨ Sugerir com IA
                  </button>
                </div>
                <textarea 
                  rows="4" 
                  placeholder="Ex: Oi! Já faz 6 meses que você comprou nosso plano. Tivemos várias atualizações, topa ver a versão premium?" 
                  value={posVenda.copy} 
                  onChange={e => setPosVenda({...posVenda, copy: e.target.value})} 
                  style={{ width: '100%', padding: '12px', borderRadius: '4px', border: '1px solid #dfe1e6', resize: 'vertical', fontFamily: 'system-ui', fontSize: '14px' }} 
                />
              </div>
            </div>
          )}
        </div>

        <button type="submit" disabled={salvando} style={{ width: '100%', padding: '15px', backgroundColor: '#0052cc', color: 'white', border: 'none', borderRadius: '6px', fontWeight: 'bold', cursor: salvando ? 'not-allowed' : 'pointer', fontSize: '16px' }}>
          {salvando ? '💾 SALVANDO CÉREBRO DA IA...' : '💾 SALVAR PLAYBOOK DE VENDAS'}
        </button>

      </form>
    </div>
  );
}

// ==========================================
// TELA: MINHAS CONEXÕES (FROTA DE REMETENTES)
// ==========================================
function TelaConexoes({ cliente }) {
  const [contas, setContas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [formData, setFormData] = useState({
    plataforma: 'whatsapp', nome_perfil: '', identificador: '', senha_ou_token: '', limite_diario: 50
  });

  useEffect(() => {
    carregarContas();
  }, [cliente]);

  const carregarContas = async () => {
    if (!cliente || cliente.id === 'admin') return;
    setLoading(true);
    const { data } = await supabase.from('contas_remetentes').select('*').eq('cliente_id', cliente.id).order('created_at', { ascending: false });
    if (data) setContas(data);
    setLoading(false);
  };

  const adicionarConta = async (e) => {
    e.preventDefault();
    setSalvando(true);
    
    // Força o limite_diario a ser um número inteiro para não dar erro no banco
    const novaConta = { 
      cliente_id: cliente.id, 
      plataforma: formData.plataforma,
      nome_perfil: formData.nome_perfil,
      identificador: formData.identificador,
      senha_ou_token: formData.senha_ou_token,
      limite_diario: parseInt(formData.limite_diario),
      status: 'ativo', 
      disparos_hoje: 0 
    };

    const { error } = await supabase.from('contas_remetentes').insert([novaConta]);
    
    setSalvando(false);
    if (!error) {
      setFormData({ plataforma: 'whatsapp', nome_perfil: '', identificador: '', senha_ou_token: '', limite_diario: 50 });
      carregarContas(); 
    } else {
      alert("Erro ao salvar conta: " + error.message);
    }
  };

  const removerConta = async (id) => {
    if(!window.confirm("Tem certeza que deseja remover esta conexão? O robô não poderá mais usá-la.")) return;
    await supabase.from('contas_remetentes').delete().eq('id', id);
    carregarContas();
  };

  if (cliente?.id === 'admin') return <div style={{ padding: '40px' }}><h2>Acesse como cliente para ver esta tela.</h2></div>;

  return (
    <div style={{ padding: '40px', maxWidth: '1000px', margin: '0 auto' }}>
      <h1 style={{ color: '#172b4d', margin: '0 0 10px 0' }}>📱 Minhas Conexões (Frota)</h1>
      <p style={{ color: '#5e6c84', margin: '0 0 30px 0' }}>Cadastre múltiplos chips de WhatsApp ou E-mails. O robô fará o rodízio automático para evitar bloqueios.</p>

      {/* FORMULÁRIO DE NOVA CONTA */}
      <form onSubmit={adicionarConta} style={{ backgroundColor: 'white', padding: '25px', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)', display: 'flex', gap: '15px', alignItems: 'flex-end', marginBottom: '30px', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: '150px' }}>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 'bold', color: '#5e6c84', marginBottom: '5px' }}>Canal</label>
          <select value={formData.plataforma} onChange={e => setFormData({...formData, plataforma: e.target.value})} style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #dfe1e6' }}>
            <option value="whatsapp">🟢 WhatsApp</option>
            <option value="linkedin">🔵 LinkedIn</option>
            <option value="email">✉️ E-mail</option>
          </select>
        </div>
        
        <div style={{ flex: 2, minWidth: '200px' }}>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 'bold', color: '#5e6c84', marginBottom: '5px' }}>Nome (Apelido)</label>
          <input type="text" placeholder="Ex: WhatsApp Vendedor João" required value={formData.nome_perfil} onChange={e => setFormData({...formData, nome_perfil: e.target.value})} style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #dfe1e6' }} />
        </div>
        
        <div style={{ flex: 2, minWidth: '200px' }}>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 'bold', color: '#5e6c84', marginBottom: '5px' }}>
            {formData.plataforma === 'whatsapp' ? 'Número (com DDD)' : formData.plataforma === 'email' ? 'Endereço de E-mail' : 'Usuário / URL'}
          </label>
          <input type="text" placeholder={formData.plataforma === 'email' ? "email@empresa.com" : "Ex: 5511999999999"} required value={formData.identificador} onChange={e => setFormData({...formData, identificador: e.target.value})} style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #dfe1e6' }} />
        </div>

        {/* CAMPO DE SENHA APARECE APENAS SE FOR E-MAIL */}
        {formData.plataforma === 'email' && (
          <div style={{ flex: 2, minWidth: '200px' }}>
            <label style={{ display: 'block', fontSize: '13px', fontWeight: 'bold', color: '#5e6c84', marginBottom: '5px' }}>Senha de App (SMTP)</label>
            <input type="password" placeholder="Senha do E-mail" required value={formData.senha_ou_token} onChange={e => setFormData({...formData, senha_ou_token: e.target.value})} style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #dfe1e6' }} />
          </div>
        )}

        <div style={{ flex: 1, minWidth: '100px' }}>
          <label style={{ display: 'block', fontSize: '13px', fontWeight: 'bold', color: '#5e6c84', marginBottom: '5px' }}>Limite / Dia</label>
          <input type="number" min="1" max="1000" required value={formData.limite_diario} onChange={e => setFormData({...formData, limite_diario: e.target.value})} style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #dfe1e6' }} />
        </div>
        
        <button type="submit" disabled={salvando} style={{ padding: '10px 20px', backgroundColor: '#0052cc', color: 'white', border: 'none', borderRadius: '4px', fontWeight: 'bold', cursor: 'pointer', height: '40px', minWidth: '120px' }}>
          {salvando ? '⏳...' : '➕ ADICIONAR'}
        </button>
      </form>

      {/* LISTA DE CONTAS */}
      <div style={{ backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 2px 5px rgba(0,0,0,0.05)', overflow: 'hidden' }}>
        {loading ? <p style={{ padding: '20px' }}>Carregando frota...</p> : contas.length === 0 ? <p style={{ padding: '20px', color: 'gray' }}>Nenhuma conexão cadastrada ainda.</p> : (
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead style={{ backgroundColor: '#f4f5f7', color: '#5e6c84', fontSize: '13px' }}>
              <tr>
                <th style={{ padding: '15px' }}>Canal</th>
                <th style={{ padding: '15px' }}>Apelido</th>
                <th style={{ padding: '15px' }}>Identificador</th>
                <th style={{ padding: '15px' }}>Uso Hoje (Anti-Ban)</th>
                <th style={{ padding: '15px', textAlign: 'right' }}>Ação</th>
              </tr>
            </thead>
            <tbody>
              {contas.map(conta => (
                <tr key={conta.id} style={{ borderBottom: '1px solid #dfe1e6', fontSize: '14px', color: '#172b4d' }}>
                  <td style={{ padding: '15px' }}>
                    {conta.plataforma === 'whatsapp' ? '🟢 WPP' : conta.plataforma === 'linkedin' ? '🔵 IN' : '✉️ MAIL'}
                  </td>
                  <td style={{ padding: '15px', fontWeight: 'bold' }}>{conta.nome_perfil}</td>
                  <td style={{ padding: '15px' }}>{conta.identificador}</td>
                  <td style={{ padding: '15px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div style={{ flex: 1, backgroundColor: '#ebecf0', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{ width: `${(conta.disparos_hoje / conta.limite_diario) * 100}%`, backgroundColor: conta.disparos_hoje >= conta.limite_diario ? '#ff5630' : '#36b37e', height: '100%' }}></div>
                      </div>
                      <span style={{ fontSize: '12px', color: '#5e6c84', width: '45px' }}>{conta.disparos_hoje} / {conta.limite_diario}</span>
                    </div>
                  </td>
                  <td style={{ padding: '15px', textAlign: 'right' }}>
                    <button onClick={() => removerConta(conta.id)} style={{ background: 'none', border: 'none', color: '#ff5630', cursor: 'pointer', fontWeight: 'bold' }}>Excluir</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}