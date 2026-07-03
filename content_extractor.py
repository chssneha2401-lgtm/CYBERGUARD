import ipaddress
import socket
import subprocess
import tempfile
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024
MAX_EXTRACTED_CHARS = 5000


class ExtractionError(ValueError):
    pass


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data):
        if not self.hidden_depth and data.strip():
            self.parts.append(data.strip())


def _clean(text):
    text = " ".join((text or "").split())
    if not text:
        raise ExtractionError("No readable or spoken text was found in this source.")
    return text[:MAX_EXTRACTED_CHARS]


def extract_url(url):
    parsed = urllib.parse.urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ExtractionError("Enter a complete public http:// or https:// URL.")

    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443)
    except socket.gaierror as error:
        raise ExtractionError("The website address could not be resolved.") from error
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ExtractionError("Private, local, and reserved network URLs cannot be scanned.")

    req = urllib.request.Request(url, headers={"User-Agent": "CyberGuardAI/1.0"})
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            raise ExtractionError("This page redirects; paste its final public URL instead.")
    try:
        with urllib.request.build_opener(_NoRedirect).open(req, timeout=10) as response:
            content_type = response.headers.get_content_type()
            if content_type not in {"text/html", "text/plain"}:
                raise ExtractionError("That URL does not point to a readable web page.")
            raw = response.read(MAX_DOWNLOAD_BYTES + 1)
            if len(raw) > MAX_DOWNLOAD_BYTES:
                raise ExtractionError("The web page is too large to scan (maximum 5 MB).")
            charset = response.headers.get_content_charset() or "utf-8"
    except ExtractionError:
        raise
    except Exception as error:
        raise ExtractionError("The web page could not be downloaded.") from error

    decoded = raw.decode(charset, errors="replace")
    if content_type == "text/plain":
        return _clean(decoded)
    parser = _VisibleTextParser()
    parser.feed(decoded)
    return _clean(" ".join(parser.parts))


def extract_file(file_storage, suffix):
    suffix = suffix.lower()
    if suffix in {".txt", ".csv", ".md"}:
        return _clean(file_storage.read().decode("utf-8", errors="replace"))
    if suffix == ".pdf":
        from pypdf import PdfReader
        return _clean(" ".join(page.extract_text() or "" for page in PdfReader(file_storage).pages))
    if suffix == ".docx":
        from docx import Document
        return _clean(" ".join(paragraph.text for paragraph in Document(file_storage).paragraphs))
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
        try:
            import pytesseract
            from PIL import Image
            return _clean(pytesseract.image_to_string(Image.open(file_storage.stream)))
        except pytesseract.TesseractNotFoundError as error:
            raise ExtractionError("Image OCR needs Tesseract installed on the server.") from error
    if suffix in {".wav", ".mp3", ".m4a", ".ogg", ".mp4", ".mov", ".webm", ".mkv"}:
        return _extract_media(file_storage, suffix)
    raise ExtractionError("This file format is not supported.")


def _extract_media(file_storage, suffix):
    import speech_recognition as sr

    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / f"source{suffix}"
        wav = Path(folder) / "speech.wav"
        file_storage.save(source)
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000", str(wav)],
                check=True,
                capture_output=True,
                timeout=60,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as error:
            raise ExtractionError("Audio/video transcription needs ffmpeg and a valid media file.") from error

        recognizer = sr.Recognizer()
        try:
            with sr.AudioFile(str(wav)) as audio:
                recording = recognizer.record(audio)
            return _clean(recognizer.recognize_google(recording))
        except sr.UnknownValueError as error:
            raise ExtractionError("No clear speech could be recognized in this media.") from error
        except sr.RequestError as error:
            raise ExtractionError("The speech-to-text service is currently unavailable.") from error
