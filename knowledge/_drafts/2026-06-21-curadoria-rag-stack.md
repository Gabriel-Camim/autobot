---
title: 'Curadoria RAG: stack'
category: curadoria
tags:
- feedback
- rag
- draft
visibility: draft
priority: 3
updated_at: '2026-06-21'
summary: Sugestão de ajuste na curadoria de stack técnica a partir de instrução direta de Gabriel.
---

# Curadoria RAG: stack

## Origem da sugestão

Feedback/instrução de Gabriel:

- Remover GPT-4o como item explícito de stack, pois o modelo já fica subentendido dentro de OpenAI/OpenAI API.
- Adicionar "metodologias ágeis" em desenvolvimento.

## Diagnóstico

A resposta anterior listava GPT-4o como item de stack em IA generativa e LLMs. O documento canônico `knowledge/skills/stack-tecnico.md` também contém o trecho "OpenAI API com GPT-4o". Para evitar granularidade excessiva e duplicidade conceitual, a stack deve citar OpenAI API sem destacar GPT-4o como item separado.

O documento `knowledge/skills/hard-skills.md` possui a seção "Desenvolvimento e arquitetura", que é o alvo mais adequado para incluir "metodologias ágeis" conforme a instrução.

## Patch proposto

1. Em `knowledge/skills/stack-tecnico.md`, substituir:

- `OpenAI API com GPT-4o.`

por:

- `OpenAI API.`

2. Em `knowledge/skills/hard-skills.md`, adicionar `metodologias ágeis` na seção "Desenvolvimento e arquitetura".

## Observação

Não há necessidade de criar novo documento público. A correção deve ser aplicada nos documentos canônicos existentes.