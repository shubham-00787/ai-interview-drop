"""Twice-weekly job: pick 15 questions, write hints, publish to the site, email subscribers."""
import json
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


def _fallback_title(qs):
    topics = [config.TOPICS[t] for t, _ in Counter(q["topic"] for q in qs).most_common(3)]
    return f"{', '.join(topics[:-1])} and {topics[-1]}" if len(topics) > 1 else topics[0]


def publish(dry_run=False, send_now=True):
    bank = Bank()
    number = len(bank.issues) + 1
    qs = select(bank, number)
    if len(qs) < config.QUESTIONS_PER_ISSUE:
        print(f"only {len(qs)} questions available")
    candidates = [q for q in qs if q["difficulty"] in ("medium", "hard")] or qs
    deep = max(candidates, key=lambda q: (q["origin"] == "fresh", _score(q)))
    hints, deep_answer, title = llm.write_hints(qs, deep["id"]) if llm.available() else ({}, None, None)
    missing = [q for q in qs if not hints.get(q["id"])]
    if missing and llm.available():  # the model sometimes skips one; ask again for just those
        more, _, _ = llm.write_hints(missing, missing[0]["id"])
        hints.update(more)
    title = title or _fallback_title(qs)
    issue = {
        "number": number,
        "date": now_iso(),
        "title": title,
        "subject": f"#{number}: {title}",
        "topics": sorted({q["topic"] for q in qs}),
        "questions": [{
            "id": q["id"], "text": q["text"], "topic": q["topic"], "difficulty": q["difficulty"],
            "hint": hints.get(q["id"], ""), "source_url": q["source_url"], "source_name": q["source_name"],
            "fresh": q["origin"] == "fresh" or _recent(q.get("last_seen"), config.FRESH_DAYS),
        } for q in qs],
        "deep_dive": {"id": deep["id"], "text": deep["text"], "answer": deep_answer} if deep_answer else None,
    }
    if dry_run:
        out = config.ROOT / "preview"
        out.mkdir(exist_ok=True)
        (out / "email.html").write_text(render.email_html(issue, preview=True))
        (out / "issue.json").write_text(json.dumps(issue, indent=1, ensure_ascii=False))
        render.build_site(extra_issue=issue, out_dir=out / "site")
        render.build_pdf(issue, out_dir=out / "site")
        print(f"dry run: preview/email.html, preview/site/ and the PDF written ({issue['subject']})")
        return issue

    issue["campaign_id"] = None
    for q in qs:
        q["sent_in"] = number
    bank.issues.append(issue)
    bank.save()
    render.build_pdf(issue)
    render.build_site()
    print(f"published issue #{number} to the site: {issue['subject']}")
    if send_now:
        send_latest()
    return issue


def send_latest():
    """Email the newest issue if it hasn't been emailed yet (run after the site + PDF are live)."""
    bank = Bank()
    if not bank.issues:
        print("send: no issues yet")
        return
    issue = bank.issues[-1]
    if issue.get("campaign_id"):
        print(f"send: issue #{issue['number']} was already emailed (campaign {issue['campaign_id']})")
        return
    from . import gmail
    if gmail.configured():
        html = render.email_html(issue, unsubscribe_url=gmail.unsubscribe_mailto())
        n = gmail.send_issue(issue["subject"], html, render.email_text(issue))
        issue["campaign_id"] = f"gmail:{n}" if n else None
    else:
        attach = render.pdf_url(issue) if config.ATTACH_PDF else None
        issue["campaign_id"] = send.send_campaign(issue["subject"], render.email_html(issue), attachment_url=attach)
    bank.save()


def send_test():
    """Send the latest issue to yourself only. Nothing is recorded."""
    from . import gmail
    bank = Bank()
    issue = bank.issues[-1]
    if gmail.configured():
        html = render.email_html(issue, unsubscribe_url=gmail.unsubscribe_mailto())
        gmail.send_issue(f"[Test] {issue['subject']}", html, render.email_text(issue), recipients=[config.SENDER_EMAIL])
    else:
        print("send-test: GMAIL_APP_PASSWORD is not set")
