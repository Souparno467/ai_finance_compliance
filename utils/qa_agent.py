import os
import math
import hashlib
import re
from langchain_core.embeddings import Embeddings

VECTORSTORE_K = 5

EMBEDDINGS_DIR = "embeddings"
VECTORSTORE_PATH = os.path.join(EMBEDDINGS_DIR, "faiss_index")

_vectorstore = None
_embeddings = None
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_cache_dir = os.path.join(_project_root, ".cache")

def _hidden_docs() -> set[str]:
    raw = os.environ.get("HIDDEN_DOCS", "KYC GUIDELINES.pdf")
    items = [i.strip() for i in raw.split(",") if i.strip()]
    return set(items)

class HashEmbeddings(Embeddings):
    """
    Pure-Python fallback embeddings (no downloads, no HF cache).

    This keeps the app usable in locked-down Windows environments where HuggingFace
    model downloads/symlinks can fail. Quality is lower than transformer embeddings,
    but retrieval still works reasonably for keyword-like queries.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim

    def _embed_text(self, text: str) -> list[float]:
        tokens = re.findall(r"[A-Za-z0-9]+", (text or "").lower())
        vec = [0.0] * self.dim
        for tok in tokens[:4000]:
            h = hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest()
            hv = int.from_bytes(h, "little", signed=False)
            idx = hv % self.dim
            sign = 1.0 if (hv & 1) == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_text(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_text(text)

def get_embeddings():
    global _embeddings
    if _embeddings is None:
        os.makedirs(_cache_dir, exist_ok=True)
        # Default to a no-download embedding path (fast, no model downloads) unless explicitly overridden.
        # Useful on hosts like Render where downloads can be slow and delay port binding.
        force_hf = os.environ.get("FORCE_HF_EMBEDDINGS", "").strip().lower() in {"1", "true", "yes"}
        backend = os.environ.get("EMBEDDINGS_BACKEND", "hash").strip().lower()
        if (backend != "hf") and not force_hf:
            _embeddings = HashEmbeddings()
            return _embeddings

        try:
            # Prefer transformer embeddings when available.
            from langchain_huggingface import HuggingFaceEmbeddings
            emb = HuggingFaceEmbeddings(
                model="sentence-transformers/all-MiniLM-L6-v2",
                cache_folder=os.path.join(_cache_dir, "huggingface"),
            )
            # Force a small call to trigger lazy init/downloads early.
            emb.embed_query("ping")
            _embeddings = emb
        except Exception as e:
            print(f"[WARN] HuggingFace embeddings unavailable; using HashEmbeddings. ({e})")
            _embeddings = HashEmbeddings()
    return _embeddings

def load_document(filepath: str):
    from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader

    ext = filepath.rsplit('.', 1)[-1].lower()
    if ext == 'pdf':
        loader = PyPDFLoader(filepath)
    elif ext == 'docx':
        loader = Docx2txtLoader(filepath)
    else:
        loader = TextLoader(filepath, encoding='utf-8', autodetect_encoding=True)
    return loader.load()

def build_vectorstore_from_uploads(upload_folder: str) -> int:
    global _vectorstore
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS

    all_docs = []
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

    for filename in os.listdir(upload_folder):
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in ('pdf', 'txt', 'docx'):
            continue
        filepath = os.path.join(upload_folder, filename)
        try:
            raw_docs = load_document(filepath)
            chunks = splitter.split_documents(raw_docs)
            # Tag source
            for chunk in chunks:
                chunk.metadata['source'] = filename
            all_docs.extend(chunks)
        except Exception as e:
            print(f"[WARN] Could not load {filename}: {e}")

    if not all_docs:
        raise ValueError("No documents found in uploads folder.")

    embeddings = get_embeddings()
    _vectorstore = FAISS.from_documents(all_docs, embeddings)
    os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
    _vectorstore.save_local(VECTORSTORE_PATH)
    return len(all_docs)

def load_vectorstore():
    global _vectorstore
    from langchain_community.vectorstores import FAISS

    if _vectorstore is not None:
        return _vectorstore
    if os.path.exists(VECTORSTORE_PATH):
        embeddings = get_embeddings()
        _vectorstore = FAISS.load_local(
            VECTORSTORE_PATH, embeddings, allow_dangerous_deserialization=True
        )
        return _vectorstore
    raise FileNotFoundError("No vector index found. Add documents to the uploads folder and reindex.")

def get_llm():
    from langchain_groq import ChatGroq

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not set.")
    model = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant").strip() or "llama-3.1-8b-instant"
    return ChatGroq(
        api_key=api_key,
        model=model,
        temperature=0.2
    )

def ensure_vectorstore_ready(upload_folder: str) -> None:
    """
    Best-effort helper to ensure a vector index exists on disk.
    Safe to call on startup.
    """
    try:
        load_vectorstore()
        return
    except Exception:
        pass
    # Only attempt a rebuild if uploads contains at least one supported document.
    if not os.path.exists(upload_folder):
        return
    for filename in os.listdir(upload_folder):
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext in ('pdf', 'txt', 'docx'):
            build_vectorstore_from_uploads(upload_folder)
            return

def _retrieve_documents(retriever, question: str):
    # LangChain retrievers evolved over time; support both styles.
    if hasattr(retriever, "invoke"):
        return retriever.invoke(question)
    if hasattr(retriever, "get_relevant_documents"):
        return retriever.get_relevant_documents(question)
    raise TypeError("Unsupported retriever interface.")

def ask_question(question: str) -> dict:
    vs = load_vectorstore()
    llm = get_llm()

    retriever = vs.as_retriever(search_kwargs={"k": VECTORSTORE_K})
    docs = _retrieve_documents(retriever, question)

    hidden = _hidden_docs()
    sources = []
    context_parts = []
    for i, doc in enumerate(docs or [], start=1):
        source = (doc.metadata or {}).get("source", "Unknown")
        label = "Internal Document" if source in hidden else source
        if source not in hidden:
            sources.append(source)
        content = (doc.page_content or "").strip()
        # Keep context bounded to avoid overly large prompts.
        if len(content) > 2500:
            content = content[:2500] + "…"
        context_parts.append(f"[{i}] Document: {label}\n{content}")

    if not context_parts:
        raise ValueError("No relevant context retrieved. Rebuild the index and try again.")

    prompt = f"""You are a financial compliance expert AI assistant specialized in KYC, AML, and RBI regulations.
Use ONLY the provided context to answer. If the answer is not in the context, say so clearly.
When making a claim, cite the context item number(s) like [1], [2].

Context:
{chr(10).join(context_parts)}

Question: {question}

Answer in this format (use concise bullet points):
**Answer:**
- <bullet 1 with citations like [1]>
- <bullet 2 with citations like [2]>
**Compliance Note:**
- <bullet 1 with citations if applicable>
"""

    response = llm.invoke(prompt)
    answer_text = getattr(response, "content", str(response)).strip()

    return {"answer": answer_text, "sources": sorted(set(sources))}
