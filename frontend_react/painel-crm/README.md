🚀 DJM Tecnologia - Agentes Autônomos de Vendas B2B
📌 Visão Geral
Uma plataforma SaaS de prospecção B2B de ponta a ponta (End-to-End). O sistema utiliza Inteligência Artificial para mapear leads qualificados (Hunter) e um motor de automação invisível para executar a cadência de contato, contornar objeções e agendar reuniões de forma 100% autônoma (Farmer).

🛠️ Stack Tecnológico
Frontend: React (Vite) com painéis dinâmicos e Kanban.

Backend API: FastAPI (Python) para comunicação assíncrona.

Banco de Dados: Supabase (PostgreSQL) operando como o cérebro de estado.

Automação RPA: Playwright (Python) com recursos anti-detect.

Inteligência Artificial: Google Gemini 2.5 Flash (Raciocínio, Web Search e Copywriting).

Clonagem de Voz: ElevenLabs API (Plug and Play, preparado para motores Open-Source Locais).

🏗️ Arquitetura do Sistema (Macro)
O sistema é dividido em 3 grandes pilares que funcionam em harmonia através do Supabase:

1. O Centro de Comando (React Frontend)
Interface onde o cliente configura as regras do jogo.

TelaConfig: Define o Nicho (Integração IBGE), os canais de contato permitidos e desenha o Funil de Cadência (intervalo de dias entre visualização, curtida, e-mail e WhatsApp).

TelaConexoes: Gerenciador da "Frota". Permite plugar múltiplos chips de WhatsApp e contas de LinkedIn com limites diários de envio (Anti-Ban).

TelaPlaybook: O "Cérebro de Vendas". Cliente cadastra respostas para objeções, link do Calendly (Concierge) e regras de Pós-Venda. Tem botão de "Sugerir com IA".

TelaCRM: Kanban de arrastar e soltar que espelha o status do lead em tempo real.

2. Agente Hunter (sales_hunter_simulador_teste.py)
O Mapeador de Mercado e Estrategista.

Fluxo: Lê o nicho do cliente -> Pesquisa no Google -> Encontra a empresa, o decisor, e-mail adivinhado e WhatsApp -> Vasculha a web para encontrar uma dor daquela empresa -> Cria as mensagens persuasivas para todas as etapas do funil -> Salva na tabela leads_hunter.

Agendamento Inteligente: Lê os dias definidos no Frontend e cria a linha do tempo de contato na tabela cadencia_agendada.

3. Agente Farmer (sales_farmer.py)
O Executor e Fechador de Vendas. Opera em duas fases diárias:

Fase 1: Outbound (Ataque): Lê a cadencia_agendada de hoje. Utiliza o algoritmo de Round Robin para escolher o chip da frota mais ocioso. Envia a mensagem (digitando de forma humanizada via Playwright) ou clona a voz do cliente na hora e envia um .mp3 via WhatsApp se identificar a tag [AUDIO]. Atualiza o Kanban no final.

Fase 2: Inbound (Defesa): O "Sentinela". Abre o WhatsApp Web, lê mensagens não lidas, envia para o Gemini cruzar com o Playbook de Objeções do cliente, gera a resposta perfeita com o link de agendamento e digita de volta para o lead.

🗄️ Modelo de Dados (Supabase PostgreSQL)
As regras de negócio dependem destas 4 tabelas principais conectadas de forma relacional:

clientes: Guarda os setups, credenciais de e-mail e os JSONs dinâmicos (playbook_objecoes, canais_prospeccao, etc).

contas_remetentes: A "Frota". Guarda os chips/contas extras com os campos limite_diario e disparos_hoje.

leads_hunter: O CRM. Guarda os dados do lead, dor encontrada, links extraídos e a coluna principal: status_funil (Prospecção, Contato Feito, Respondeu, Fechado).

cadencia_agendada: A fila de trabalho. O Hunter cria, o Farmer consome e deleta. Possui as instruções de tipo_acao, data_agendada, alvo e a copy.

🛡️ Protocolos de Segurança e Anti-Ban Implementados
Rodízio de Contas (Round Robin): O sistema nunca sobrecarrega um número. Se há 5 chips cadastrados com limite de 50 mensagens/dia, ele divide o volume uniformemente.

Digitação Humanizada: O Playwright possui delays randômicos (40ms a 90ms) entre as teclas pressionadas e pausas de "leitura" antes de responder.

Arquitetura Plug & Play (Voz): O arquivo .env possui a chave MOTOR_DE_VOZ. O sistema transita de ElevenLabs (Nuvem) para servidor local XTTS v2 mudando apenas 1 string, garantindo viabilidade econômica na escala.

🚀 Como Iniciar a Operação
Ativar Backend: Rodar uvicorn api:app --reload no terminal para ligar o ouvinte de requisições e a IA.

Ativar Frontend: Rodar npm run dev na pasta React.

Fluxo de Uso:

O Cliente configura as credenciais e o Playbook no React.

O Cliente cadastra a Frota em "Minhas Conexões".

O Cliente clica em "Gerar Leads" (O Hunter popula o banco).

O Cliente clica em "Iniciar Expediente" (O Farmer abre o Playwright invisível e executa o dia).