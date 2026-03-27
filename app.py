import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

# Load environment variables from .env (if present) before importing modules that rely on them.
load_dotenv()

from utils.qa_agent import ask_question, build_vectorstore_from_uploads, ensure_vectorstore_ready
from utils.summarizer import generate_compliance_checklist

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

@app.route('/')
def index():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    question = data.get('question', '').strip()
    if not question:
        return jsonify({'error': 'No question provided'}), 400
    try:
        result = ask_question(question)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/checklist', methods=['POST'])
def checklist():
    data = request.get_json()
    topic = data.get('topic', '').strip()
    if not topic:
        return jsonify({'error': 'No topic provided'}), 400
    try:
        items = generate_compliance_checklist(topic)
        return jsonify({'checklist': items})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/rebuild-index', methods=['POST'])
def rebuild_index():
    try:
        count = build_vectorstore_from_uploads(app.config['UPLOAD_FOLDER'])
        return jsonify({'message': f'Index rebuilt with {count} document chunk(s).'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs('embeddings', exist_ok=True)
    # Best-effort auto-index existing uploads so Q&A works immediately after boot.
    try:
        ensure_vectorstore_ready(app.config['UPLOAD_FOLDER'])
    except Exception as e:
        print(f"[WARN] Vectorstore not ready at startup: {e}")
    app.run(debug=True)
