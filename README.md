# ⚖️ ComplianceAI — AI Financial Policy Assistant

A solo fresher fintech startup project: an AI-powered compliance copilot for KYC, AML, and RBI regulation Q&A.

Built with **Flask + LangChain + Groq + FAISS**.

---

## 🚀 Features

- 💬 **Policy Q&A** — Ask natural language questions with cited answers from your documents
- ✅ **Compliance Checklist Generator** — Instant RBI/KYC/AML checklists by topic
- 🔍 **Vector Search** — FAISS-powered semantic retrieval for fast clause lookup

---

## 🛠️ Setup

### 1. Clone & Install

```bash
git clone <your-repo>
cd ai_finance_compliance
pip install -r requirements.txt
```

### 2. Set your Groq API key

```bash
cp .env.example .env
# Edit .env and paste your GROQ_API_KEY
```

Get a free API key at: https://console.groq.com

### 3. Add documents

Place your KYC/AML/RBI PDF files in the `uploads/` folder.

### 4. Run

```bash
python app.py
```

Visit `http://localhost:5000`

---

## 🌐 Deployment

### Render (Free Tier)
1. Push to GitHub
2. Create a new **Web Service** on Render
3. Set `GROQ_API_KEY` in Environment Variables
4. Build command: `pip install -r requirements.txt`
5. Start command: `python app.py`

### HuggingFace Spaces
1. Create a new Space with **Gradio/Docker** SDK
2. Upload all project files
3. Add `GROQ_API_KEY` as a Space Secret

---

## 📂 Project Structure

```
ai_finance_compliance/
├── app.py                  # Flask app & routes
├── requirements.txt
├── .env.example
├── templates/
│   └── index.html          # Frontend UI
├── static/
│   ├── style.css
│   └── script.js
├── uploads/                # Place policy docs here
├── embeddings/             # Auto-generated FAISS index
└── utils/
    ├── qa_agent.py         # LangChain QA + vector search
    └── summarizer.py       # Summarization + checklist generation
```

---

## 🔑 Tech Stack

| Layer | Tech |
|-------|------|
| Backend | Flask |
| LLM | Groq (Llama3-8B) |
| Orchestration | LangChain |
| Vector Store | FAISS |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Frontend | HTML/CSS/JS |

---

## 💡 Example Questions

- *"What checks are required for a ₹50,000 transfer?"*
- *"What documents are needed for full KYC verification?"*
- *"What are the AML reporting obligations for suspicious transactions?"*
- *"What is the threshold for enhanced due diligence?"*
