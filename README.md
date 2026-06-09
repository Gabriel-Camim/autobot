# Gabriel Portfolio Agent

Portfólio conversacional com RAG e voz, feito com FastAPI, LangChain, ChromaDB local, OpenAI API e React.

## Estrutura

```txt
backend/      API, agente, ingestáo, voz e download do pacote recrutador
frontend/     Interface React com mapa mental, chat e microfone
knowledge/    Base Markdown publica e curada para RAG
materials/    Pacote baixado pelo botão Extrair Gabriel
```

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Preencha `backend/.env` com uma chave OpenAI rotacionada. O arquivo `.env` está no `.gitignore`.

Validar documentos públicos:

```powershell
python ingest.py --check
```

Indexar a base no ChromaDB:

```powershell
python ingest.py
```

Rodar API:

```powershell
uvicorn main:app --reload --port 8000
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

O frontend usa `VITE_API_URL`, com padrao `http://localhost:8000`.

## Conteudo

Edite os Markdown em `knowledge/`. Apenas arquivos com `visibility: public` no frontmatter entram no RAG.

O botão `Extrair Gabriel` baixa os arquivos de `materials/recruiter-pack`, não a base inteira.

## Deploy

- Frontend: Vercel.
- Backend: Railway ou Render.
- Configure `OPENAI_API_KEY` apenas no backend.
- Rode a ingestáo manualmente quando alterar a base Markdown.
