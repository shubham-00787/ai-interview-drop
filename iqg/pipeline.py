"""Daily job: collect -> extract questions -> tag -> remove duplicates -> save."""
import re

import numpy as np

from . import config, llm, sources
from .store import Bank, now_iso

ML_WORDS = re.compile(r"\b(model|llm|rag|agent|neural|gradient|transformer|embedding|training|loss|overfit|"
                      r"regression|classif|feature|inference|attention|token|fine-?tun|ml|machine learning)\b", re.I)


def heuristic_topic(text, heading=""):
    s = f"{text} {heading}".lower()
    for topic, words in config.TOPIC_KEYWORDS:
        if any(w in s for w in words):
            return topic
    return config.DEFAULT_TOPIC


def _heuristic_extract(doc):
    """Fallback when no LLM key is set: sentences that end in '?' and mention ML terms."""
    out = []
    for s in re.split(r"(?<=[?.!])\s+", doc["text"]):
        if s.endswith("?") and 30 <= len(s) <= 220 and ML_WORDS.search(s):
            out.append({"question": s, "topic": heuristic_topic(s), "difficulty": "medium", "quality": 2})
    return out


# ------------------------------------------------------------------ steps
def seed(bank):
    added = 0
    for s in sources.github_seed():
        if bank.add(s["text"], source_url=s["url"], source_name=s["repo"], origin="seed",
                    difficulty=s["difficulty"], license=s["license"], heading=s["heading"]):
            added += 1
    print(f"seed: +{added} new questions")


def collect_fresh(bank):
    docs = sources.hacker_news() + sources.reddit() + sources.tavily()
    docs = [d for d in docs if d["id"] not in bank.seen]
    print(f"fresh: {len(docs)} unseen docs")
    added = 0
    batch_size = 12
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i + batch_size]
        if llm.available():
            found = llm.extract_questions(batch)
            if not found and llm._calls >= config.MAX_LLM_CALLS_PER_RUN:
                print("fresh: LLM budget used up; remaining docs wait for tomorrow")
                break
            tagged_by = "llm"
        else:
            found = {d["id"]: _heuristic_extract(d) for d in batch}
            tagged_by = "heuristic"
        for d in batch:
            bank.seen.add(d["id"])
            for q in found.get(d["id"], []):
                text = (q.get("question") or "").strip()
                if not text or q.get("topic") not in config.TOPICS:
                    continue
                if bank.add(text, source_url=d["url"], source_name=d["source_name"], origin="fresh",
                            topic=q["topic"], difficulty=q.get("difficulty"), quality=q.get("quality"),
                            tagged_by=tagged_by):
                    added += 1
    print(f"fresh: +{added} new questions")


def tag(bank):
    """Give every question a topic/difficulty/quality. LLM when available, else keyword rules."""
    todo = [q for q in bank.questions if q["tagged_by"] != "llm" and not q["duplicate_of"]]
    done = 0
    if llm.available():
        for i in range(0, len(todo), config.TAG_BATCH):
            batch = todo[i:i + config.TAG_BATCH]
            tags = llm.tag_questions(batch)
            if not tags:
                break
            for q in batch:
                t = tags.get(q["id"])
                if t and t.get("topic") in config.TOPICS:
                    q.update(topic=t["topic"], difficulty=t.get("difficulty") or q["difficulty"],
                             quality=t.get("quality"), tagged_by="llm")
                    done += 1
    for q in bank.questions:  # anything still untagged gets the keyword fallback
        if not q["topic"]:
            q.update(topic=heuristic_topic(q["text"], q.get("heading") or ""),
                     difficulty=q["difficulty"] or "medium",
                     quality=q["quality"] or (3 if q["origin"] == "seed" else 2), tagged_by="heuristic")
    print(f"tag: {done} tagged by LLM, {len(todo) - done} waiting for LLM tagging")


_embedder = None


def _embed(texts):
    global _embedder
    if _embedder is None:
        from fastembed import TextEmbedding
        _embedder = TextEmbedding(config.EMBED_MODEL)
    v = np.array(list(_embedder.embed(texts)), dtype=np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def dedupe(bank):
    """Mark near-duplicates (same meaning, different wording). The older question survives.
    If a fresh post repeats an existing question, the existing one counts as 'trending'."""
    live = [q for q in bank.questions if not q["duplicate_of"]]
    new = [q for q in live if not q["deduped"]]
    if not new:
        print("dedupe: nothing new")
        return
    vecs = _embed([q["text"] for q in live])
    index = {q["id"]: i for i, q in enumerate(live)}
    order = sorted(live, key=lambda q: q["first_seen"])
    rank = {q["id"]: r for r, q in enumerate(order)}
    dupes = 0
    for q in new:
        if q["duplicate_of"]:
            continue
        sims = vecs @ vecs[index[q["id"]]]
        for j in np.argsort(-sims)[1:6]:
            other = live[j]
            if sims[j] < config.DEDUPE_THRESHOLD:
                break
            if other["duplicate_of"] or rank[other["id"]] > rank[q["id"]]:
                continue  # only fold into an older, surviving question
            q["duplicate_of"] = other["id"]
            if q["origin"] == "fresh":
                other["last_seen"] = now_iso()
                other["seen_count"] = other.get("seen_count", 1) + 1
            dupes += 1
            break
        q["deduped"] = True
    print(f"dedupe: {dupes} duplicates folded into existing questions")


def run_daily():
    bank = Bank()
    if not any(q["origin"] == "seed" for q in bank.questions):
        seed(bank)
    collect_fresh(bank)
    tag(bank)
    dedupe(bank)
    bank.save()
    live = bank.available()
    print(f"bank: {len(bank.questions)} total, {len(live)} unsent & unique")


def run_seed_refresh():
    bank = Bank()
    seed(bank)
    tag(bank)
    dedupe(bank)
    bank.save()
