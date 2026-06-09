---
title: DGE fonte - DGE 2.0 - ML, Fine-Tuning e Operational Product Backbone
category: projetos
tags:
- dge
- fonte-original
- arquitetura
visibility: public
priority: 3
updated_at: '2026-06-09'
summary: 'Documento original importado da base DGE 2.0: docs/architecture/dge-2.0-ml-fine-tuning-and-operational-product-backbone.md.'
source_path: docs/architecture/dge-2.0-ml-fine-tuning-and-operational-product-backbone.md
---

# DGE 2.0 - ML, Fine-Tuning e Operational Product Backbone

Fonte original DGE 2.0: `docs/architecture/dge-2.0-ml-fine-tuning-and-operational-product-backbone.md`.

---

# DGE 2.0 - ML, Fine-Tuning e Operational Product Backbone

## Objetivo

Registrar o norte arquitetural da DGE 2.0 para duas espinhas que devem crescer juntas:

1. Preparar a DGE para ML, avaliacao e fine-tuning futuro sem treinar modelos em cima de dado bruto, solto ou nao auditado.
2. Pensar a DGE como sistema operacional interno da operacao: cockpit, filas, cadastros, permissoes, responsabilidades e governanca por tenant.

Este blueprint nao cria frontend ainda. Ele define criterios para os proximos backbones, contratos de dados, rotas e telas futuras.

## Norte para ML e Fine-Tuning

A DGE deve nascer preparada para aprendizado, mas nao deve iniciar fine-tuning antes de existir curadoria, avaliacao e aprovacao dos dados.

Principios:

- Nenhum dado bruto deve virar exemplo de treino automaticamente.
- Todo exemplo elegivel deve vir de registros auditados, traces RAI aprovados, snapshots consistentes ou decisoes operacionais validadas.
- O caminho cognitivo dos agentes RAI deve ser registrado como trace estruturado, mas apenas traces curados e higienizados podem alimentar datasets.
- Dados sensiveis, dados pessoais e informacoes comerciais estrategicas devem passar por mascaramento, reducao ou exclusao antes de qualquer uso em dataset.
- Fine-tuning deve ser especifico por agente ou classe de tarefa, nao um modelo unico treinado com tudo.
- Toda versao de dataset deve ter origem, escopo, criterios de inclusao, criterios de exclusao, aprovador, data e metricas de avaliacao.
- Antes de fine-tuning, a DGE precisa de harness de avaliacao para comparar resposta base, resposta ajustada, riscos, ganho real e regressao.

Backbone futuro recomendado:

- ML Data Foundation: contratos de eventos, snapshots, traces, decisoes e resultados reais.
- Training Example Registry: registro versionado de exemplos candidatos, aprovados, rejeitados e publicados.
- RAI Trace Curation: selecao de traces bons, ruins, ambiguos e instrutivos.
- Evaluation Harness: conjunto fixo de casos para testar agentes antes e depois de ajustes.
- Dataset Approval Flow: fluxo governado para liberar datasets por tenant, agente e finalidade.
- Agent Feedback Loop: avaliacao humana e operacional sobre qualidade das respostas, decisoes e recomendacoes.
- Fine-Tuning Pipeline: etapa futura, acionada apenas quando houver massa critica e ganho mensuravel.

## Norte para a DGE como Operacao

A DGE deve ser desenhada como cockpit operacional e sistema de governanca, nao como uma copia do ecommerce, ERP, WMS, TMS ou ferramenta de automacao.

Responsabilidade central da DGE:

- Consolidar dados operacionais, financeiros, comerciais e logisticos.
- Normalizar entradas vindas de cadastro manual, Bling, ecommerce, Frenet, Loggi, n8n e outras fontes futuras.
- Controlar aprovacao, auditoria, rastreabilidade e freshness dos dados.
- Detectar gargalos e riscos.
- Projetar cenarios e impactos.
- Exibir a operacao por papel, unidade, franquia, hub, periodo e responsabilidade.
- Gerar recomendacoes, relatorios e traces explicaveis.

Responsabilidades que nao devem ficar na DGE na primeira fase:

- Checkout transacional do ecommerce.
- Emissao operacional direta de etiqueta como fonte primaria.
- Execucao logistica fisica como WMS/TMS completo.
- Cadastro visual/publicavel de produto para consumidor final.
- Automacoes externas como ferramenta principal de disparo, quando isso for melhor orquestrado por n8n.

## Cadastro de Unidades, Franquias e Hubs

A DGE deve possuir cadastro proprio de unidades operacionais porque precisa controlar escopo, permissao, auditoria e leitura por tenant.

Entidades operacionais esperadas:

- Tenant ou grupo operacional.
- Unidade propria.
- Franquia.
- Hub logistico.
- Loja com retirada.
- Centro de estoque.
- Regiao operacional.
- Responsavel operacional.
- Relacao entre unidade, hub, estoque e tenant.

O ERP/ecommerce podem ter suas proprias referencias, mas a DGE deve manter o mapeamento interno para analise, governanca e roteamento de visibilidade.

## Cadastro e Importacao de Produtos

Fonte recomendada por responsabilidade:

- ERP/Bling: fonte operacional para SKU, estoque, movimentacoes, vendas fiscais e cadastro base.
- Ecommerce: fonte para vitrine, conteudo publicavel, imagem, descricao comercial, preco exibido, promocao e comportamento do usuario.
- DGE: camada de normalizacao, auditoria, atributos analiticos, classificacao operacional, rastreio de margem, risco, cobertura de estoque, gargalo e impacto projetado.

A DGE pode permitir correcao ou enriquecimento analitico, mas deve evitar virar a origem primaria do catalogo comercial enquanto Bling/ecommerce forem as fontes transacionais.

## Telas Futuras da DGE

As telas devem nascer por responsabilidade operacional, nao por tabela.

Layers recomendadas:

- Command Center: visao geral de saude, riscos, prioridades, freshness e recomendacoes.
- Fila Operacional: tarefas pendentes por usuario, unidade, cargo e prazo.
- Coleta Diaria: entrada manual de KPIs e dados operacionais durante implantacao e contingencia.
- Aprovacoes e Auditoria: fluxo de superior, auditor final e liberacao de dado auditado.
- Unidades, Franquias e Hubs: cadastro e governanca da malha operacional.
- Produtos e Estoque: leitura de SKU, estoque por unidade, cobertura, ruptura, excesso e descentralizacao.
- Commerce Operations: pedidos, usuarios, funil, eventos, pagamentos, conversao e comportamento.
- Fulfillment e Logistica: separacao, nota, etiqueta, postagem, retirada, reversa, cancelamento e SLA.
- Frete e Margem Logistica: taxa de frete por pedido, percentual do frete sobre pedido, peso global do frete, transportadoras e impacto em margem.
- Integracoes e Automacoes: Bling, Frenet, Loggi, ecommerce, n8n, jobs, falhas e freshness.
- Projecoes e Reforecast: projecao oficial, previews, impactos, sugestoes adaptativas e aprovacao humana.
- Relatorios: diarios, semanais, mensais, diretoria, operacao, estoque, frete e financeiro.
- RAI Console: agentes, traces, fontes, raciocinio registrado, decisao e revisao humana.
- ML Readiness: datasets candidatos, exemplos aprovados, avaliacao, versoes e governanca de treino.
- Administracao: usuarios, papeis, permissoes, tenant, unidades, escopos e politicas.

## Modelo de Visibilidade por Tenant e Papel

A visibilidade deve seguir escopo operacional e responsabilidade:

- Operador de unidade: ve e preenche dados da propria unidade; nao aprova final; nao ve dados financeiros sensiveis globais.
- Gestor de unidade: ve unidade completa, aprova entradas locais e acompanha pendencias.
- Gestor regional: ve agregados e pendencias das unidades da regiao.
- Operacoes: ve cadeia operacional, estoque, fulfillment, frete, gargalos e SLAs.
- Financeiro: ve margens, projecoes, impactos, premissas, payback e reforecast.
- Estoque: ve produtos, SKUs, cobertura, ruptura, movimentacoes e descentralizacao.
- Integracoes: ve importacoes, jobs, automacoes, erros e contingencias; nao aprova dado final sozinho.
- Auditor: ve historico, aprova fechamento, rastreia fontes e bloqueia dado inconsistente.
- Admin/owner: ve e governa tudo dentro do tenant.
- Usuario de sistema: envia dados automatizados com escopo limitado e rastreavel; nao substitui auditoria humana.

## Regra de Ouro

O dado pode entrar por muitos caminhos, mas so deve alimentar inteligencia oficial quando estiver normalizado, rastreavel, aprovado ou marcado com confianca suficiente.

O cockpit deve mostrar nao apenas o numero, mas tambem:

- De onde veio.
- Quem registrou.
- Quem aprovou.
- Quando foi atualizado.
- Qual regra calculou.
- Qual modulo foi impactado.
- Quais projecoes mudariam.
- Qual risco operacional foi detectado.

## Proximo Passo Arquitetural Recomendado

Criar o Operational Product Backbone v1, cobrindo:

- mapa de telas;
- mapa de papeis e permissoes;
- ownership DGE vs ecommerce vs ERP vs n8n vs Frenet/Loggi;
- fluxos operacionais por etapa;
- eventos operacionais minimos;
- criterios de visibilidade;
- contratos de dados que precisam existir antes do frontend.
