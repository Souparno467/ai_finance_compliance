import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

# Load environment variables from .env (if present) before importing modules that rely on them.
load_dotenv()

from utils.qa_agent import ask_question, build_vectorstore_from_uploads, ensure_vectorstore_ready
from utils.summarizer import generate_compliance_checklist

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'txt', 'docx'}

def _allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

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
    except FileNotFoundError:
        # If uploads exist but index isn't built yet, best-effort build once and retry.
        try:
            ensure_vectorstore_ready(app.config['UPLOAD_FOLDER'])
            result = ask_question(question)
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
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

@app.route('/documents', methods=['GET'])
def documents():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    items = []
    for filename in sorted(os.listdir(app.config['UPLOAD_FOLDER'])):
        if _allowed_file(filename):
            items.append(filename)
    return jsonify({'documents': items})

@app.route('/upload', methods=['POST'])
def upload():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No files provided'}), 400

    saved = []
    skipped = []
    for f in files:
        if not f or not getattr(f, "filename", ""):
            continue
        filename = secure_filename(f.filename)
        if not filename or not _allowed_file(filename):
            skipped.append(f.filename)
            continue
        dest = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(dest)
        saved.append(filename)

    if not saved and skipped:
        return jsonify({'error': 'No supported files uploaded (pdf, txt, docx).'}), 400
    return jsonify({'saved': saved, 'skipped': skipped})

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
