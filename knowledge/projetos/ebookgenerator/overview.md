---
title: Ebook Generator
category: projetos
tags:
- ebook-generator
- n8n
- llm
- openai
- gamma
- automacao-editorial
visibility: public
priority: 1
updated_at: '2026-06-09'
summary: Projeto autoral de automação editorial com LLMs, n8n, OpenAI, Gamma e JSON
  estruturado.
---

# Ebook Generator

O Ebook Generator é um workflow autoral em n8n para transformar briefing e dados agregados em produto editorial premium. Ele usa prompts encadeados, OpenAI API, Gamma API, JSON estruturado, parsing, normalização, controle de custo, construção de product brain e memória conversacional.

## O que o workflow faz

- Recebe tema, briefing ou dataset consolidado.
- Planeja estratégia editorial, posicionamento, público, promessa central e direção visual.
- Pesquisa padrões de comunidades, relatos e sinais de mercado.
- Sintetiza dores, linguagem, objeções, oportunidades e ângulo editorial.
- Gera blueprint estratégico em JSON.
- Aciona um escritor editorial especializado para produzir a obra final estruturada.
- Monta payload para Gamma com formato, dimensões, estilo visual, densidade de texto, quantidade de imagens e instruções editoriais.
- Cria/atualiza product brain reutilizável para agentes conversacionais e memória de produto.
- Integra Supabase para persistência de ebook, usuário, eventos de conversa e memória.

## Nós principais identificados no JSON

- (parse) output gpt organizado
- prompt gpt + conexao com o json escavado
- http request openai
- contador token
- Start
- Convert to File
- walter write
- http request openai2
- Parse Ebook Raw
- Gamma Payload Builder Raw
- Gamma Generate Direct
- Agent Brain Prompt Builder
- Knowledge Pack Builder
- Parse Agent Brain Output
- Merge Product Brain
- Convert Product Brain to File
- OpenAI Agent Brain
- Memory Resolver
- Agent Reply Prompt Builder
- OpenAI Agent Reply
- Parse Agent Reply
- Load User Input
- Supabase Upsert Ebook
- Supabase Upsert User
- Supabase Load Ebook Brain
- Supabase Load User Memory
- Supabase Insert Conversation Event
- Prepare Memory Update

## Competências demonstradas

Esse projeto demonstra engenharia de prompts, automação com n8n, uso de APIs, JSON estruturado, integração com OpenAI/Gamma/Supabase, controle de tokens/custo, tratamento de erro, pipeline editorial e pensamento de produto. O valor não está só em gerar texto, mas em transformar um processo editorial inteiro em arquitetura repetível.
