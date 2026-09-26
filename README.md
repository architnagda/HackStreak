# DocuMind - Multi-Source Enterprise Document Intelligence & RAG Platform

DocuMind is an enterprise-grade AI-powered Document Intelligence application. It provides page-level grounded Question Answering, multi-document synthesis, and semantic search across PDFs, scanned documents (OCR), images, and Word documents using Sentence Transformers, ChromaDB, FastAPI, React, and Google Gemini.

---

## 🌟 Key Features

- **Document-Scoped Retrieval**: Choose between querying a specific document, multiple selected documents, or performing global search across all uploaded files.
- **Strict Grounding & Zero Hallucination**: RAG responses are strictly derived from retrieved evidence with exact page numbers and evidence snippets.
- **Concise Multi-Document Synthesis**: Compare figures, policies, and topics across multiple documents with coherent synthesis.
- **Multimodal OCR Extraction**: Ingest and process digital PDFs, scanned PDFs (Tesseract OCR), images (`.png`, `.jpg`, `.jpeg`), and `.docx` documents.
- **Fine-Grained Semantic Retrieval**: Vector search with `sentence-transformers/all-MiniLM-L6-v2` stored in ChromaDB vector database.
- **Enterprise UI / UX**: Built with React, TypeScript, Tailwind CSS, and Lucide icons.

---

## 🏗️ Architecture

```
Frontend (React + Vite + TypeScript)
       ↓  (Axios REST API)
FastAPI Backend
       ↓
Semantic Chunking + Embeddings (MiniLM-L6-v2)
       ↓
ChromaDB Vector Store + MySQL DB (Conversations, Citations, Documents)
       ↓
Grounded RAG Reasoning (Google Gemini 3.8 Flash)
```

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- MySQL Server (running on `localhost:3306`)
- *(Optional)* Tesseract OCR for scanned PDF/image OCR

---

### 1. Backend Setup

```bash
cd backend

# Create & activate virtual environment
python -m venv venv
.\venv\Scripts\activate      # On Windows
# source venv/bin/activate   # On Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env to configure your MySQL password and GEMINI_API_KEY

# Initialize database schema & tables
python app/db_init.py

# Start FastAPI development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Backend will be live at `http://127.0.0.1:8000` (API Docs at `http://127.0.0.1:8000/docs`).

---

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

Frontend will be live at `http://127.0.0.1:5173`.

---

## 🛡️ Security & Privacy

- `.env` and sensitive API keys are excluded via `.gitignore`.
- Password hashing with `bcrypt`.
- JWT authentication with Bearer tokens.
- User document isolation enforced at database and vector filter levels.
