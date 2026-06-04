import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for
from markupsafe import Markup, escape

from model import CATEGORY_ORDER, build_classifier


app = Flask(__name__)
classifier = build_classifier()
IS_VERCEL = bool(os.getenv("VERCEL"))
HISTORY_PATH = Path("data/analysis_history.json")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_TABLE = "analysis_history"
MAX_TEXT_LENGTH = 5000


SAMPLE_ANALYSES = [
    {
        "message": "If you show up in the class group again, I will make sure everyone turns against you.",
        "category": "harassment",
        "category_label": "Harassment",
        "danger_level": "Critical",
        "confidence": 96.4,
        "danger_score": 96.4,
        "keywords": ["everyone", "turns", "against"],
        "explanation": "Critical risk: the message shows direct harassment and coordinated intimidation toward a student.",
    },
    {
        "message": "People from your religion do not belong in our chat.",
        "category": "hate_speech",
        "category_label": "Hate Speech",
        "danger_level": "Critical",
        "confidence": 94.8,
        "danger_score": 94.8,
        "keywords": ["religion", "belong"],
        "explanation": "Critical risk: the message targets identity and excludes someone based on religion.",
    },
    {
        "message": "Keep talking and I will hurt you after school.",
        "category": "threat",
        "category_label": "Threat",
        "danger_level": "High",
        "confidence": 89.2,
        "danger_score": 89.2,
        "keywords": ["hurt", "after school"],
        "explanation": "High risk: the message contains a direct threat of physical harm.",
    },
    {
        "message": "You are such a dumb loser, nobody wants your opinion.",
        "category": "insult",
        "category_label": "Insult",
        "danger_level": "High",
        "confidence": 86.7,
        "danger_score": 86.7,
        "keywords": ["dumb", "loser", "nobody"],
        "explanation": "High risk: the message uses repeated personal insults and rejection language.",
    },
    {
        "message": "Do not invite her to the project chat. She does not fit with us.",
        "category": "exclusion",
        "category_label": "Exclusion",
        "danger_level": "Medium",
        "confidence": 73.5,
        "danger_score": 73.5,
        "keywords": ["invite", "fit"],
        "explanation": "Medium risk: the message encourages exclusion from a shared school activity.",
    },
    {
        "message": "Your post was embarrassing and everyone probably laughed at it.",
        "category": "harassment",
        "category_label": "Harassment",
        "danger_level": "Medium",
        "confidence": 68.1,
        "danger_score": 68.1,
        "keywords": ["embarrassing", "laughed"],
        "explanation": "Medium risk: the message attempts to shame the student publicly.",
    },
    {
        "message": "That answer was kind of stupid, but the rest of your work is okay.",
        "category": "insult",
        "category_label": "Insult",
        "danger_level": "Low",
        "confidence": 58.3,
        "danger_score": 58.3,
        "keywords": ["stupid"],
        "explanation": "Low risk: the message includes mild insulting language but not sustained bullying.",
    },
    {
        "message": "Let's make a separate group without him for now.",
        "category": "exclusion",
        "category_label": "Exclusion",
        "danger_level": "Low",
        "confidence": 54.9,
        "danger_score": 54.9,
        "keywords": ["separate", "without"],
        "explanation": "Low risk: the message may signal exclusion, though context could change the interpretation.",
    },
    {
        "message": "I disagree with your idea, but thanks for explaining it clearly.",
        "category": "safe",
        "category_label": "Safe",
        "danger_level": "Safe",
        "confidence": 91.6,
        "danger_score": 8.4,
        "keywords": [],
        "explanation": "Safe content: the message disagrees respectfully without bullying indicators.",
    },
    {
        "message": "Please stop posting personal comments and keep the discussion respectful.",
        "category": "safe",
        "category_label": "Safe",
        "danger_level": "Safe",
        "confidence": 88.9,
        "danger_score": 11.1,
        "keywords": [],
        "explanation": "Safe content: the message sets a boundary and asks for respectful discussion.",
    },
]


def serialize_entry(entry):
    clean = dict(entry)
    clean["timestamp"] = clean["timestamp"].isoformat()
    clean.pop("highlighted_message", None)
    return clean


def create_share_summary(entry):
    keywords = ", ".join(entry.get("keywords") or ["None"])
    timestamp = entry["timestamp"].strftime("%d %b %Y, %I:%M %p")
    return (
        "CyberGuard AI Analysis\n"
        f"Category: {entry['category_label']}\n"
        f"Danger Level: {entry['danger_level']}\n"
        f"Confidence: {entry['confidence']}%\n"
        f"Flagged Words: {keywords}\n"
        f"Timestamp: {timestamp}\n"
        f"Explanation: {entry['explanation']}"
    )


def hydrate_entry(entry):
    entry["highlighted_message"] = highlight_keywords(
        entry.get("message", ""),
        entry.get("keywords", []),
    )
    entry["share_summary"] = create_share_summary(entry)
    return entry


def build_sample_history():
    now = datetime.now()
    entries = []
    for index, sample in enumerate(SAMPLE_ANALYSES, start=1):
        entry = {
            "id": index,
            "label": "non_bullying" if sample["danger_level"] == "Safe" else "bullying",
            "scores": {
                "bullying": sample["danger_score"] / 100,
                "non_bullying": 1 - (sample["danger_score"] / 100),
            },
            "is_bullying": sample["danger_level"] != "Safe",
            "timestamp": now - timedelta(days=(index - 1) % 7, hours=index),
            **sample,
        }
        entries.append(hydrate_entry(entry))
    return entries


def supabase_configured():
    return bool(SUPABASE_URL and SUPABASE_SECRET_KEY)


def supabase_headers():
    return {
        "apikey": SUPABASE_SECRET_KEY,
        "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def supabase_table_url():
    return f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"


def supabase_request(method, params=None, body=None, prefer=None):
    url = supabase_table_url()
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    headers = supabase_headers()
    if prefer:
        headers["Prefer"] = prefer

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    request_data = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request_data, timeout=8) as response:
        raw_body = response.read().decode("utf-8")
        return json.loads(raw_body) if raw_body else []


def load_supabase_history():
    try:
        rows = supabase_request(
            "GET",
            params={
                "select": "id,payload,created_at",
                "order": "created_at.desc",
                "limit": "50",
            },
        )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return build_sample_history()

    entries = []
    for row in rows:
        payload = row.get("payload") or {}
        payload["id"] = row.get("id", payload.get("id", 0))
        payload["timestamp"] = payload.get("timestamp") or row.get("created_at")
        try:
            payload["timestamp"] = datetime.fromisoformat(str(payload["timestamp"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            payload["timestamp"] = datetime.now()
        entries.append(hydrate_entry(payload))
    return entries or build_sample_history()


def save_supabase_entry(entry):
    payload = serialize_entry(entry)
    payload.pop("id", None)
    try:
        rows = supabase_request(
            "POST",
            body={"payload": payload},
            prefer="return=representation",
        )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return entry

    if rows:
        entry["id"] = rows[0].get("id", entry.get("id", 0))
    return entry


def clear_supabase_history():
    try:
        supabase_request(
            "DELETE",
            params={"id": "not.is.null"},
        )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return False
    return True


def save_entries(entries):
    if supabase_configured():
        return

    if IS_VERCEL:
        return

    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("w", encoding="utf-8") as file:
        json.dump([serialize_entry(item) for item in entries], file, indent=2)


def load_history():
    if supabase_configured():
        return load_supabase_history()

    if IS_VERCEL:
        return build_sample_history()

    if not HISTORY_PATH.exists():
        sample_history = build_sample_history()
        save_entries(sample_history)
        return sample_history

    try:
        with HISTORY_PATH.open(encoding="utf-8") as file:
            entries = json.load(file)
    except (json.JSONDecodeError, OSError):
        return []

    restored = []
    for entry in entries:
        try:
            entry["timestamp"] = datetime.fromisoformat(entry["timestamp"])
        except (KeyError, ValueError):
            entry["timestamp"] = datetime.now()
        restored.append(hydrate_entry(entry))
    return restored


def save_history():
    save_entries(analysis_log)


def highlight_keywords(message, keywords):
    if not keywords:
        return Markup(escape(message))

    escaped_message = escape(message)
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(escape(keyword)) for keyword in keywords) + r")\b",
        re.IGNORECASE,
    )
    highlighted = pattern.sub(r'<mark class="flag-highlight">\1</mark>', str(escaped_message))
    return Markup(highlighted)


analysis_log = load_history()


def create_analysis(message):
    result = classifier.predict(message)
    entry = {
        "id": max([item.get("id", 0) for item in analysis_log], default=0) + 1,
        "message": message,
        "timestamp": datetime.now(),
        **result,
    }
    hydrate_entry(entry)
    if supabase_configured():
        save_supabase_entry(entry)
    analysis_log.insert(0, entry)
    if not supabase_configured():
        save_history()
    return entry


def dashboard_context():
    total = len(analysis_log)
    flagged = sum(1 for item in analysis_log if item["danger_level"] != "Safe")
    safe = total - flagged
    critical = sum(1 for item in analysis_log if item["danger_level"] == "Critical")

    category_counts = Counter({label: 0 for label in [
        "Harassment",
        "Hate Speech",
        "Threat",
        "Insult",
        "Exclusion",
        "Safe",
    ]})
    category_counts.update(item["category_label"] for item in analysis_log)
    danger_counts = Counter({level: 0 for level in [
        "Critical",
        "High",
        "Medium",
        "Low",
        "Safe",
    ]})
    danger_counts.update(item["danger_level"] for item in analysis_log)
    days = [(datetime.now().date() - timedelta(days=offset)) for offset in range(6, -1, -1)]
    weekly = []

    for day in days:
        counts = defaultdict(int)
        for item in analysis_log:
            if item["timestamp"].date() == day and item["category"] in CATEGORY_ORDER:
                counts[item["category_label"]] += 1
        weekly.append(
            {
                "day": day.strftime("%a"),
                "Harassment": counts["Harassment"],
                "Hate Speech": counts["Hate Speech"],
                "Threat": counts["Threat"],
                "Insult": counts["Insult"],
                "Exclusion": counts["Exclusion"],
            }
        )

    report_logs = [
        {
            "id": item["id"],
            "message": item["message"],
            "timestamp": item["timestamp"].strftime("%d %b %Y, %I:%M %p"),
            "category_label": item["category_label"],
            "danger_level": item["danger_level"],
            "confidence": item["confidence"],
            "danger_score": item["danger_score"],
            "explanation": item["explanation"],
            "keywords": item["keywords"],
        }
        for item in analysis_log
    ]

    return {
        "stats": {
            "total": total,
            "flagged": flagged,
            "safe": safe,
            "critical": critical,
        },
        "category_counts": dict(category_counts),
        "danger_counts": dict(danger_counts),
        "weekly": weekly,
        "logs": analysis_log,
        "report_logs": report_logs,
        "report_date": datetime.now().strftime("%Y-%m-%d"),
    }


@app.route("/", methods=["GET"])
def detect():
    return render_template(
        "index.html",
        page="detect",
        message="",
        result=None,
        error=None,
        **dashboard_context(),
    )


@app.route("/analyze", methods=["POST"])
def analyze():
    message = request.form.get("message", "").strip()
    result = None
    error = None
    if not message:
        error = "Please enter text to analyze"
    elif len(message) > MAX_TEXT_LENGTH:
        error = "Text exceeds maximum length. Please shorten your input."
    else:
        try:
            result = create_analysis(message)
        except Exception:
            error = "Analysis failed. Please try again."

    return render_template(
        "index.html",
        page="detect",
        message=message,
        result=result,
        error=error,
        **dashboard_context(),
    )


@app.route("/dashboard")
def dashboard():
    return render_template(
        "index.html",
        page="dashboard",
        message="",
        result=None,
        error=None,
        **dashboard_context(),
    )


@app.route("/resources")
def resources():
    return render_template(
        "index.html",
        page="resources",
        message="",
        result=None,
        error=None,
        **dashboard_context(),
    )


@app.route("/clear-history", methods=["POST"])
def clear_history():
    analysis_log.clear()
    if supabase_configured():
        clear_supabase_history()
    else:
        save_history()
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
