---
title: Autobot - Agente pessoal com RAG e voz
category: projetos
tags:
- autobot
- rag
- voz
- fastapi
- react
- langchain
- postgresql
- pgvector
- webrtc
visibility: public
priority: 1
updated_at: '2026-06-27'
summary: Projeto do portfólio conversacional com RAG, voz, relatórios estáticos e
  pacote recrutador.
---

# Autobot - Agente pessoal com RAG e voz

Autobot é o projeto deste portfólio conversacional: um agente pessoal que simula uma entrevista comigo para recrutadores, respondendo em primeira pessoa com base em uma base Markdown pública e curada.

## Stack e Arquitetura

- Backend em Python, FastAPI e LangChain para orquestração de agente multimodal.
- PostgreSQL como banco relacional, com pgVector para armazenamento e busca vetorial.
- Text-embedding-3-large para conversão vetorial de documentos e consultas.
- GPT Realtime 2 com WebRTC para agentes conversacionais de voz em tempo real.
- Gpt-4o-mini-tts para conversão de texto em voz.
- OpenAI API com uso dos modelos disponíveis conforme a necessidade do fluxo, sem fixar um único modelo específico de LLM para chat.
- Frontend em Vite + React.
- Deploy de frontend em Vercel, backend Python em Render e database em PostgreSQL.
- Base de dados textual em MD com versionamento Git.
- Ciclo automatizado para avaliação de respostas com feedback loop, curadoria RAG, seleção de documentos por proximidade semântica e distância vetorial, injeção de documentos externos convertidos em embeddings no banco vetorial relacionados por pontes semânticas ao contexto da curadoria, prompt para sugestão de mudança na base de dados, edição e avaliação de diff gerado por IA, alteração canônica versionada via Git e reindexação RAG para aplicação canônica das mudanças no agente.

## Desenvolvimento e arquitetura AI First

O desenvolvimento segue uma abordagem AI First, com frontend em Vite + React, backend em Python, REST API e FastAPI, banco de dados em PostgreSQL, versionamento Git e metodologias ágeis para evolução do produto.