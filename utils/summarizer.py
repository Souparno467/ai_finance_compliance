import os




def get_llm():
    from langchain_groq import ChatGroq

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not set.")
    model = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant").strip() or "llama-3.1-8b-instant"
    return ChatGroq(
        api_key=api_key,
        model=model,
        temperature=0.3,
    )


def load_document(filepath: str):
    from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader

    ext = filepath.rsplit(".", 1)[-1].lower()
    if ext == "pdf":
        loader = PyPDFLoader(filepath)
    elif ext == "docx":
        loader = Docx2txtLoader(filepath)
    else:
        loader = TextLoader(filepath, encoding="utf-8", autodetect_encoding=True)
    return loader.load()


def summarize_document(filepath: str) -> str:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    llm = get_llm()
    raw_docs = load_document(filepath)

    splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    docs = splitter.split_documents(raw_docs)

    # Limit chunks to avoid token overload
    docs = docs[:10]

    section_summaries = []
    for i, doc in enumerate(docs, start=1):
        text = (doc.page_content or "").strip()
        if not text:
            continue
        if len(text) > 8000:
            text = text[:8000] + "…"

        prompt = f"""You are a compliance analyst. Summarize the following section of a financial policy document.
Focus on: key rules, obligations, thresholds, and compliance requirements.

Section {i}:
{text}

Concise Summary (3-6 bullets):"""
        resp = llm.invoke(prompt)
        section_summaries.append(getattr(resp, "content", str(resp)).strip())

    if not section_summaries:
        return "Summary not available."

    combine_prompt = f"""You are a senior compliance officer. Based on the following section summaries,
write a clear and structured executive summary of this financial policy/regulation document.

Include:
- Purpose of the document
- Key compliance requirements
- Important thresholds or limits mentioned
- Key risks or obligations for the institution

Section Summaries:
{chr(10).join(section_summaries)}

Executive Summary:"""

    result = llm.invoke(combine_prompt)
    return getattr(result, "content", str(result)).strip() or "Summary not available."


def generate_compliance_checklist(topic: str) -> list:
    llm = get_llm()

    prompt = f"""You are a RegTech compliance expert for Indian fintech companies.
Generate a detailed compliance checklist for: "{topic}"

Focus on RBI guidelines, KYC/AML requirements, and fintech regulations.
Return ONLY a JSON array of checklist items (strings), no explanation.
Example format: ["Item 1", "Item 2", "Item 3"]

Checklist (JSON array only):"""

    response = llm.invoke(prompt)
    content = getattr(response, "content", str(response)).strip()

    # Parse JSON array
    import json
    import re

    match = re.search(r"\[.*\]", content, re.DOTALL)
    if match:
        try:
            items = json.loads(match.group())
            return [str(item) for item in items]
        except Exception:
            pass

    # Fallback: split by newlines
    lines = [
        l.strip().lstrip("-•*123456789. ")
        for l in content.split("\n")
        if l.strip()
    ]
    return lines if lines else ["Could not generate checklist. Please try again."]
