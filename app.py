import os
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename

from summarizer import humanize_text, summarize_pdf, summarize_youtube

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_PDF = {".pdf"}
MAX_UPLOAD_MB = 25

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024

limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["60 per hour"],
)


def _save_upload(file_storage, allowed_ext: set[str]) -> Path:
    name = secure_filename(file_storage.filename or "")
    ext = Path(name).suffix.lower()
    if ext not in allowed_ext:
        raise ValueError(f"Unsupported file type: {ext or '(none)'}")
    target = UPLOAD_DIR / f"{uuid4().hex}{ext}"
    file_storage.save(target)
    return target


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/summarize/pdf")
@limiter.limit("5 per minute")
def handle_pdf():
    if "file" not in request.files:
        return jsonify(error="No file uploaded"), 400
    language = request.form.get("language", "").strip() or "English"
    try:
        path = _save_upload(request.files["file"], ALLOWED_PDF)
    except ValueError as e:
        return jsonify(error=str(e)), 400
    summary = summarize_pdf(path, language=language)
    return jsonify(summary=summary, source=path.name)


@app.post("/summarize/youtube")
@limiter.limit("5 per minute")
def handle_youtube():
    data = request.get_json(silent=True) or request.form
    url = (data.get("url") or "").strip()
    language = (data.get("language") or "").strip() or "English"
    if not url:
        return jsonify(error="No URL provided"), 400
    summary = summarize_youtube(url, language=language)
    return jsonify(summary=summary, source=url)


@app.post("/humanize")
@limiter.limit("5 per minute")
def handle_humanize():
    data = request.get_json(silent=True) or request.form
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify(error="No text provided"), 400
    result = humanize_text(text)
    return jsonify(result=result)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
