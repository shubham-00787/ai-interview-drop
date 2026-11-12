"""Question bank stored as plain JSON files in data/ (diffable, committed by the workflows)."""
import hashlib
import json
import re
from datetime import datetime, timezone

from . import config

QUESTIONS = config.DATA / "questions.json"
SEEN = config.DATA / "seen_sources.json"
ISSUES = config.DATA / "issues.json"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load(path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default


def _save(path, obj):
    config.DATA.mkdir(exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def normalize(text):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", text.lower())).strip()


def qid(text):
    return hashlib.sha1(normalize(text).encode()).hexdigest()[:12]


class Bank:
    def __init__(self):
        self.questions = _load(QUESTIONS, [])
        self.seen = set(_load(SEEN, []))
        self.issues = _load(ISSUES, [])
        self._ids = {q["id"] for q in self.questions}

    def save(self):
        self.questions.sort(key=lambda q: q["first_seen"])
        _save(QUESTIONS, self.questions)
        _save(SEEN, sorted(self.seen))
        _save(ISSUES, self.issues)

    def has(self, text):
        return qid(text) in self._ids

    def add(self, text, *, source_url, source_name, origin, topic=None, difficulty=None,
            quality=None, license=None, heading=None, tagged_by=None):
        """origin: 'seed' (curated repo) or 'fresh' (found in recent posts)."""
        text = re.sub(r"\s+", " ", text).strip()
        i = qid(text)
        if i in self._ids:
            return None
        q = {
            "id": i, "text": text, "topic": topic, "difficulty": difficulty,
            "quality": quality, "tagged_by": tagged_by, "origin": origin, "source_url": source_url,
            "source_name": source_name, "license": license, "heading": heading,
            "first_seen": now_iso(), "last_seen": None, "seen_count": 1, "deduped": False,
            "sent_in": None, "duplicate_of": None,
        }
        self.questions.append(q)
        self._ids.add(i)
        return q

    def available(self):
        return [q for q in self.questions if not q["sent_in"] and not q["duplicate_of"]]
