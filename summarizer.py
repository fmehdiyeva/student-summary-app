"""Summarization backends.

YouTube summaries use youtube-transcript-api, PDF summaries use pypdf, and
both route extracted text through the Anthropic SDK.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import anthropic
from dotenv import load_dotenv
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

load_dotenv()

_MODEL = "openai/gpt-oss-20b:free"
_MAX_TOKENS = 8192

_SYSTEM_PROMPT = """You are a study assistant that writes clear, well-structured summaries for university students.

Given a transcript or document, produce a summary that:
- Opens with a 2-3 sentence overview of what the material covers.
- Lists the key concepts as a bulleted list, each with a one-line explanation.
- Calls out any formulas, definitions, or technical terms worth memorizing.
- Ends with 3-5 study questions the student could use for self-testing.

Infer the subject from the material itself. Do not invent content that is not in the source — if the source is thin, say so briefly."""

_HUMANIZE_PROMPT = """You rewrite AI-generated text so it reads as if written by a thoughtful human.

Goals:
- Vary sentence length and structure; avoid the uniform rhythm typical of AI output.
- Replace stiff connectors ("Furthermore", "Moreover", "In conclusion") with natural transitions.
- Cut filler phrases ("It is important to note that", "delve into", "navigate the landscape of").
- Prefer concrete nouns and active verbs over abstract noun phrases.
- Keep the original meaning, facts, and length roughly the same. Do not add new claims.
- Preserve the original language. Match the original register (formal/casual) unless it's obviously off.

Return only the rewritten text — no preface, no explanation, no quotes around it."""


def summarize_pdf(path: Path, language: str = "English") -> str:
    try:
        text = _extract_pdf_text(path)
    except ValueError as e:
        return str(e)
    except PdfReadError as e:
        return f"Could not read PDF: {e}"
    except FileNotFoundError:
        return "PDF file was not found on disk."

    if not text.strip():
        return "No extractable text was found in the PDF — it may be a scanned image. Try an OCR step before summarizing."

    return _summarize_text(text, kind="pdf", language=language)


def summarize_youtube(url: str, language: str = "English") -> str:
    try:
        video_id = _extract_youtube_id(url)
    except ValueError as e:
        return f"Could not parse YouTube URL: {e}"

    try:
        transcript = _fetch_youtube_transcript(video_id)
    except TranscriptsDisabled:
        return "This video has transcripts disabled — no captions are available."
    except NoTranscriptFound:
        return "No transcript could be found for this video in a supported language."
    except VideoUnavailable:
        return "This video is unavailable."
    except Exception as e:
        return f"Failed to fetch transcript: {e}"

    return _summarize_text(transcript, kind="youtube", language=language)


def _extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as e:
            raise ValueError(f"PDF is password-protected: {e}")

    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)
    return "\n\n".join(pages).strip()


def _extract_youtube_id(url: str) -> str:
    url = url.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url):
        return url

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if host == "youtu.be":
        vid = parsed.path.lstrip("/")
        if vid:
            return vid
    if "youtube.com" in host:
        qs = parse_qs(parsed.query)
        if qs.get("v"):
            return qs["v"][0]
        m = re.match(r"^/(?:embed|shorts|live|v)/([^/?#]+)", parsed.path)
        if m:
            return m.group(1)

    raise ValueError("not a recognizable YouTube URL or 11-character video ID")


def _fetch_youtube_transcript(video_id: str) -> str:
    api = YouTubeTranscriptApi()
    fetched = api.fetch(video_id)
    return " ".join(snippet.text for snippet in fetched).strip()


def humanize_text(text: str) -> str:
    if not text.strip():
        return "No text was provided to humanize."

    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return "OPENROUTER_API_KEY is not set — add it to your .env file and restart the app."
        client = anthropic.Anthropic(base_url="https://openrouter.ai/api", api_key=api_key)
        response = client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": _HUMANIZE_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": text}],
        )
    except anthropic.AuthenticationError:
        return "OPENROUTER_API_KEY is invalid — check your .env file."
    except anthropic.APIError as e:
        return f"API error: {e.message}"

    return "\n".join(block.text for block in response.content if block.type == "text").strip()


def _summarize_text(text: str, kind: str, language: str = "English") -> str:
    if not text.strip():
        return "No content was found to summarize."

    user_prompt = (
        f"Source type: {kind}\n"
        f"Write the summary in {language}. All sections (overview, key concepts, study questions) must be in {language}.\n\n"
        f"Source material:\n{text}"
    )

    try:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            return "OPENROUTER_API_KEY is not set — add it to your .env file and restart the app."
        client = anthropic.Anthropic(base_url="https://openrouter.ai/api", api_key=api_key)
        response = client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.AuthenticationError:
        return "ANTHROPIC_API_KEY is missing or invalid — set it in your environment and try again."
    except anthropic.APIError as e:
        return f"Claude API error: {e.message}"

    return "\n".join(block.text for block in response.content if block.type == "text").strip()
