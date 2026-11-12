"""Collectors. Each fresh source returns documents: {id, url, source_name, text}.
Sources whose API key is missing are skipped, so the pipeline always runs."""
import html
import os
import re
import time
from datetime import date

import requests

from . import config

UA = {"User-Agent": "ai-interview-drop/0.1 (open-source newsletter bot)"}
log = print


def _clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------- Hacker News
def hacker_news(days=2):
    since = int(time.time()) - days * 86400
    docs = {}
    for q in config.HN_QUERIES:
        try:
            r = requests.get("https://hn.algolia.com/api/v1/search_by_date", headers=UA, timeout=30, params={
                "query": q, "tags": "(story,comment)", "hitsPerPage": 50,
                "numericFilters": f"created_at_i>{since}"})
            r.raise_for_status()
        except requests.RequestException as e:
            log(f"  hn: {q!r} failed: {e}")
            continue
        for h in r.json()["hits"]:
            text = _clean(" ".join(filter(None, [h.get("title"), h.get("story_text"), h.get("comment_text")])))
            if len(text) < 80 or "interview" not in text.lower():
                continue
            docs[f"hn:{h['objectID']}"] = {
                "id": f"hn:{h['objectID']}", "source_name": "Hacker News", "text": text[:4000],
                "url": f"https://news.ycombinator.com/item?id={h['objectID']}"}
    log(f"  hn: {len(docs)} docs")
    return list(docs.values())


# ---------------------------------------------------------------- Reddit
def reddit(days=2):
    cid, secret = os.getenv("REDDIT_CLIENT_ID"), os.getenv("REDDIT_CLIENT_SECRET")
    if not (cid and secret):
        log("  reddit: skipped (no REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET)")
        return []
    tok = requests.post("https://www.reddit.com/api/v1/access_token", auth=(cid, secret), headers=UA,
                        data={"grant_type": "client_credentials"}, timeout=30).json()["access_token"]
    h = {**UA, "Authorization": f"bearer {tok}"}
    since = time.time() - days * 86400
    docs = []
    for sub in config.REDDIT_SUBS:
        r = requests.get(f"https://oauth.reddit.com/r/{sub}/search", headers=h, timeout=30, params={
            "q": "interview", "restrict_sr": 1, "sort": "new", "t": "week", "limit": 50})
        if r.status_code != 200:
            log(f"  reddit r/{sub}: HTTP {r.status_code}")
            continue
        for c in r.json()["data"]["children"]:
            p = c["data"]
            if p["created_utc"] < since:
                continue
            text = _clean(f"{p['title']}. {p.get('selftext', '')}")
            if len(text) > 80:
                docs.append({"id": f"reddit:{p['id']}", "source_name": f"r/{sub}", "text": text[:4000],
                             "url": "https://www.reddit.com" + p["permalink"], "score": p.get("score", 0)})
    log(f"  reddit: {len(docs)} docs")
    return docs


# ---------------------------------------------------------------- Tavily web search
def tavily():
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        log("  tavily: skipped (no TAVILY_API_KEY)")
        return []
    n, k = len(config.TAVILY_QUERIES), config.TAVILY_PER_DAY
    start = (date.today().toordinal() * k) % n          # rotate through the query list day by day
    queries = [config.TAVILY_QUERIES[(start + i) % n] for i in range(k)]
    docs = []
    for q in queries:
        r = requests.post("https://api.tavily.com/search", timeout=60, json={
            "query": q, "search_depth": "basic", "max_results": 8, "time_range": "week"},
            headers={"Authorization": f"Bearer {key}"})
        if r.status_code != 200:
            log(f"  tavily: {q!r} HTTP {r.status_code}")
            continue
        for res in r.json().get("results", []):
            url = res["url"]
            name = ("LinkedIn" if "linkedin.com" in url else "X" if re.search(r"//(www\.)?(x|twitter)\.com", url)
                    else re.sub(r"^www\.", "", url.split("/")[2]))
            docs.append({"id": f"web:{url}", "url": url, "source_name": name,
                         "text": _clean(f"{res.get('title', '')}. {res.get('content', '')}")[:4000]})
    log(f"  tavily: {len(docs)} docs")
    return docs


# ---------------------------------------------------------------- GitHub seed repos
_Q_LINE = re.compile(r"^\s*(?:#{1,6}\s*|[-*+]\s+|\d+[.)]\s+|\*\*)?\s*(?:\*\*)?\s*(?:Q?\d+[:.)]\s*)?(.+?\?)[^\w\s]*\s*(?:\*\*)?[^\w]*$")
_DIFF_EMOJI = {"👶": "easy", "⭐": "medium", "🚀": "hard"}
_HEADING = re.compile(r"^(#{1,6})\s+(.+)$")


def _gh(path, raw=False):
    h = {**UA, "Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json"}
    if os.getenv("GITHUB_TOKEN"):
        h["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    r = requests.get(f"https://api.github.com/{path}", headers=h, timeout=30)
    r.raise_for_status()
    return r.text if raw else r.json()


def parse_markdown_questions(md):
    """Yield (question, nearest_heading, difficulty_or_None) from a markdown file."""
    heading = ""
    in_code = False
    for line in md.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        m = _HEADING.match(line)
        if m and not line.rstrip().endswith("?"):
            heading = _clean(m.group(2))
            continue
        m = _Q_LINE.match(line)
        if not m:
            continue
        q = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", m.group(1))   # markdown links -> text
        q = _clean(q.replace("**", "").replace("`", ""))
        q = re.sub(r"^(?:Q?\d+[:.)]\s*)", "", q)
        if q.lower().startswith(("follow-up", "why should you", "want to", "did you", "do you know how")):
            continue
        if 20 <= len(q) <= 300:
            diff = next((d for e, d in _DIFF_EMOJI.items() if e in line), None)
            yield q, heading, diff


def github_seed():
    """Return [{text, heading, difficulty, url, repo, license}] from the curated seed repos."""
    out = []
    for repo, path_filter, lic in config.SEED_REPOS:
        try:
            tree = _gh(f"repos/{repo}/git/trees/HEAD?recursive=1")["tree"]
        except requests.RequestException as e:
            log(f"  seed {repo}: {e}")
            continue
        files = [t["path"] for t in tree if t["path"].endswith(".md") and path_filter in t["path"]
                 and not re.search(r"(^|/)(cn|fa|zh|ja|ko|es)/|README-[A-Z]{2}|CONTRIBUT|LICENSE|CODE_OF", t["path"])]
        n = 0
        for f in files[:80]:
            md = _gh(f"repos/{repo}/contents/{f}", raw=True)
            for q, heading, diff in parse_markdown_questions(md):
                out.append({"text": q, "heading": heading, "difficulty": diff, "license": lic, "repo": repo,
                            "url": f"https://github.com/{repo}/blob/HEAD/{f}"})
                n += 1
        log(f"  seed {repo}: {n} questions from {len(files)} files")
    return out
