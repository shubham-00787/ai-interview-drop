"""Twice-weekly job: pick 15 questions, write hints, publish to the site, email subscribers."""
import random
from collections import Counter
from datetime import datetime, timedelta, timezone

from . import config, llm, render, send
from .store import Bank, now_iso

DIFF_CYCLE = ["easy", "medium", "medium", "hard"]


def _recent(ts, days):
    if not ts:
        return False
    return datetime.fromisoformat(ts) >= datetime.now(timezone.utc) - timedelta(days=days)


def _score(q):
    return (q.get("quality") or 2) + 0.5 * min(q.get("seen_count", 1) - 1, 4)


def select(bank, number):
    rng = random.Random(number)
    pool = [q for q in bank.available() if (q.get("quality") or 3) >= 3 or q["tagged_by"] != "llm"]
    picked, per_topic = [], Counter()

    def take(q):
        picked.append(q)
        per_topic[q["topic"]] += 1
        pool.remove(q)

    # 1) fresh: new this week, or an older question people are asking again right now
    fresh = [q for q in pool if (q["origin"] == "fresh" and _recent(q["first_seen"], config.FRESH_DAYS))
             or _recent(q.get("last_seen"), config.FRESH_DAYS)]
    fresh.sort(key=_score, reverse=True)
    for q in fresh:
        if len(picked) >= config.FRESH_PER_ISSUE:
            break
        if per_topic[q["topic"]] < 2:
            take(q)

    # 2) bank: rotate topics, least-covered recently first, mixing difficulty
    recent_topics = Counter()
    for iss in bank.issues[-4:]:
        recent_topics.update(iss.get("topics", []))
    topics = sorted(config.TOPICS, key=lambda t: (recent_topics[t], rng.random()))
    d = 0
    while len(picked) < config.QUESTIONS_PER_ISSUE and pool:
        progressed = False
        for t in topics:
            if len(picked) >= config.QUESTIONS_PER_ISSUE:
                break
            if per_topic[t] >= 3:
                continue
            cands = [q for q in pool if q["topic"] == t]
            if not cands:
                continue
            want = DIFF_CYCLE[d % len(DIFF_CYCLE)]
            match = [q for q in cands if q["difficulty"] == want] or cands
            best = max(_score(q) for q in match)
            take(rng.choice([q for q in match if _score(q) >= best - 0.5]))
            d += 1
            progressed = True
        if not progressed:  # every topic capped: relax the cap
            take(max(pool, key=_score))
    order = list(config.TOPICS)
    picked.sort(key=lambda q: (order.index(q["topic"]), DIFF_CYCLE.index(q["difficulty"] or "medium")))
    return picked


def _subject(number, qs, deep):
    topics = [config.TOPICS[t] for t, _ in Counter(q["topic"] for q in qs).most_common(3)]
    return f"#{number}: {len(qs)} questions. {', '.join(topics)} + more"


def publish(dry_run=False):
    bank = Bank()
    number = len(bank.issues) + 1
    qs = select(bank, number)
    if len(qs) < config.QUESTIONS_PER_ISSUE:
        print(f"only {len(qs)} questions available")
    candidates = [q for q in qs if q["difficulty"] in ("medium", "hard")] or qs
    deep = max(candidates, key=lambda q: (q["origin"] == "fresh", _score(q)))
    hints, deep_answer = llm.write_hints(qs, deep["id"]) if llm.available() else ({}, None)
    issue = {
        "number": number,
        "date": now_iso(),
        "subject": _subject(number, qs, deep),
        "topics": sorted({q["topic"] for q in qs}),
        "questions": [{
            "id": q["id"], "text": q["text"], "topic": q["topic"], "difficulty": q["difficulty"],
            "hint": hints.get(q["id"], ""), "source_url": q["source_url"], "source_name": q["source_name"],
            "fresh": q["origin"] == "fresh" or _recent(q.get("last_seen"), config.FRESH_DAYS),
        } for q in qs],
        "deep_dive": {"id": deep["id"], "text": deep["text"], "answer": deep_answer} if deep_answer else None,
    }
    html = render.email_html(issue)
    if dry_run:
        out = config.ROOT / "preview"
        out.mkdir(exist_ok=True)
        (out / "email.html").write_text(render.email_html(issue, preview=True))
        render.build_site(extra_issue=issue, out_dir=out / "site")
        print(f"dry run: preview/email.html and preview/site/ written ({issue['subject']})")
        return issue

    campaign = send.send_campaign(issue["subject"], html)
    issue["campaign_id"] = campaign
    for q in qs:
        q["sent_in"] = number
    bank.issues.append(issue)
    bank.save()
    render.build_site()
    print(f"published issue #{number}: {issue['subject']}")
    return issue
