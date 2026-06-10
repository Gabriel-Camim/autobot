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
- chroma
visibility: public
priority: 1
updated_at: '2026-06-09'
summary: Projeto do portfólio conversacional com RAG, voz, relatórios estáticos e
  pacote recrutador.
---

# Autobot - Agente pessoal com RAG e voz

Autobot é o projeto deste portfólio conversacional: um agente pessoal que simula uma entrevista comigo para recrutadores, respondendo em primeira pessoa com base em uma base Markdown pública e curada.

## Stack

- Backend em Python, FastAPI e LangChain.
- Banco vetorial ChromaDB local.
- OpenAI API para chat, embeddings, Whisper e TTS.
- Frontend em React/Vite.
- Interface com mapa mental, chat, voz opcional, relatórios por nó, galeria pessoal e botão Extrair Gabriel.

## Decisões de produto

O projeto separa conteúdo editorial público da lógica do agente. Os Markdown ficam em `/knowledge`, a ingestão é manual, o Chroma é recriado de forma limpa e o frontend mostra respostas sem poluir a UI com fontes. Há relatórios estáticos por nó para consulta rápida sem gastar token.

## O que o projeto demonstra

Autobot mostra capacidade de arquitetar uma aplicação full stack com IA, RAG, UX, tratamento de erro, voz, segurança de chave, API REST, pacotes de download e deploy planejado. Também mostra uma preocupação importante: quando o agente não tem contexto suficiente, ele deve admitir limite em vez de inventar.
