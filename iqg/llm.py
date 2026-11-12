"""Free-tier LLM calls: Gemini first, OpenRouter free models as fallback.
Every call returns parsed JSON, or None when no provider is configured / all fail."""
import json
import os
import re
import time

import requests

from . import config

_calls = 0


def available():
    return bool(os.getenv("GEMINI_API_KEY") or os.getenv("OPENROUTER_API_KEY"))


def _parse_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"(\{.*\}|\[.*\])", text, re.S)
        return json.loads(m.group(1)) if m else None


def _gemini(prompt):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent"
    for attempt in range(3):
        r = requests.post(url, headers={"x-goog-api-key": key}, timeout=120, json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}})
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(20 * (attempt + 1))
            continue
        if r.status_code != 200:
            print(f"  gemini HTTP {r.status_code}: {r.text[:200]}")
            return None
        parts = r.json()["candidates"][0]["content"]["parts"]
        return _parse_json("".join(p.get("text", "") for p in parts))
    print("  gemini: rate-limited, giving up for this call")
    return None


def _openrouter(prompt):
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return None
    r = requests.post("https://openrouter.ai/api/v1/chat/completions", timeout=120,
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": config.OPENROUTER_MODEL, "temperature": 0.2,
                            "messages": [{"role": "user", "content": prompt + "\n\nReply with JSON only."}]})
    if r.status_code != 200:
        print(f"  openrouter HTTP {r.status_code}: {r.text[:200]}")
        return None
    return _parse_json(r.json()["choices"][0]["message"]["content"])


def ask_json(prompt):
    global _calls
    if _calls >= config.MAX_LLM_CALLS_PER_RUN:
        return None
    _calls += 1
    try:
        out = _gemini(prompt)
        if out is None:
            out = _openrouter(prompt)
        return out
    except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"  llm error: {e}")
        return None


TOPIC_LIST = "\n".join(f'- "{k}": {v}' for k, v in config.TOPICS.items())


def extract_questions(docs):
    """docs: [{id, text}] -> {doc_id: [{question, topic, difficulty, quality}]}"""
    body = "\n\n".join(f"<doc id=\"{d['id']}\">\n{d['text'][:2500]}\n</doc>" for d in docs)
    prompt = f"""You curate interview questions for people preparing for AI Engineer / ML Engineer jobs.
Below are recent posts from social media, forums and the web. For each doc, extract the technical interview
questions it contains or clearly reports being asked (e.g. "they asked me how KV caching works" ->
"How does KV caching work in LLM inference?"). Rewrite each as one clear, self-contained question.
Skip: job ads, opinions, career/salary/behavioral questions, questions unrelated to AI/ML engineering,
and anything too vague to answer. Most docs will have zero questions; that is fine.

For each question give:
- topic: one of
{TOPIC_LIST}
- difficulty: "easy" | "medium" | "hard"
- quality: 1-5 (5 = a sharp question a strong interviewer would really ask; 1 = vague or trivial)

Return JSON: {{"results": [{{"doc_id": "...", "questions": [{{"question": "...", "topic": "...", "difficulty": "...", "quality": 4}}]}}]}}

{body}"""
    out = ask_json(prompt) or {}
    return {r.get("doc_id"): r.get("questions", []) for r in out.get("results", []) if isinstance(r, dict)}


def tag_questions(qs):
    """qs: [{id, text, heading}] -> {id: {topic, difficulty, quality}}"""
    body = "\n".join(json.dumps({"id": q["id"], "q": q["text"], "section": q.get("heading", "")}) for q in qs)
    prompt = f"""Tag each AI/ML engineering interview question.
topic: one of
{TOPIC_LIST}
difficulty: "easy" | "medium" | "hard" (for a mid-level ML/AI engineer interview)
quality: 1-5 (5 = sharp, realistic interview question; 1 = vague, trivial, or not really an interview question)

Return JSON: {{"tags": [{{"id": "...", "topic": "...", "difficulty": "...", "quality": 3}}]}}

{body}"""
    out = ask_json(prompt) or {}
    return {t["id"]: t for t in out.get("tags", []) if isinstance(t, dict) and "id" in t}


def write_hints(qs, deep_dive_id):
    """qs: [{id, text}] -> ({id: hint}, deep_dive_markdown_or_None)"""
    body = "\n".join(json.dumps({"id": q["id"], "q": q["text"]}) for q in qs)
    prompt = f"""You are a senior ML engineer helping candidates prepare for AI/ML engineer interviews.
For every question write "hint": 1-2 sentences (max 45 words) naming the key points a strong answer covers.
Do not write the full answer.
For the question with id "{deep_dive_id}" also write "deep_dive": a concise model answer (150-220 words,
plain text with short paragraphs or "- " bullets, no headings) as a strong candidate would give it.

Return JSON: {{"hints": [{{"id": "...", "hint": "..."}}], "deep_dive": "..."}}

{body}"""
    out = ask_json(prompt) or {}
    hints = {h["id"]: h.get("hint", "") for h in out.get("hints", []) if isinstance(h, dict) and "id" in h}
    return hints, out.get("deep_dive")
