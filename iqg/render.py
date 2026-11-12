"""Render the email and the static website (GitHub Pages serves docs/)."""
import shutil
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import config
from .store import Bank

env = Environment(loader=FileSystemLoader(config.TEMPLATES), autoescape=select_autoescape(["html"]),
                  trim_blocks=True, lstrip_blocks=True)
env.filters["nicedate"] = lambda s: datetime.fromisoformat(s).strftime("%b %-d, %Y")
env.filters["paras"] = lambda s: [p.strip() for p in (s or "").split("\n") if p.strip()]


def _srclabel(q):
    name, url = q.get("source_name") or "", q.get("source_url") or ""
    if "github.com" in url and "/" in name:
        return "GitHub · " + name.split("/")[-1].replace("-", " ")
    if name.startswith("r/"):
        return "Reddit · " + name
    return name.replace("www.", "")


def _bytopic(questions):
    """Group questions by topic, keeping the configured topic order."""
    out = {}
    for q in questions:
        out.setdefault(q["topic"], []).append(q)
    order = list(config.TOPICS)
    return sorted(out.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else 99)


env.filters["srclabel"] = _srclabel
env.filters["bytopic"] = _bytopic
env.filters["title_of"] = lambda i: i.get("title") or i["subject"].split(": ", 1)[-1]


_STATS = {}


def _ctx(**kw):
    return dict(name=config.NEWSLETTER_NAME, tagline=config.TAGLINE, site_url=config.SITE_URL,
                form_action=config.SUBSCRIBE_FORM_ACTION, topics=config.TOPICS, stats=_STATS, **kw)


def email_html(issue, preview=False, unsubscribe_url=None):
    """unsubscribe_url: None = Brevo's own unsubscribe tag (Brevo campaigns); a mailto for Gmail sending."""
    if unsubscribe_url is None:
        unsubscribe_url = "#" if preview else "{{ unsubscribe }}"
    return env.get_template("email.html").render(**_ctx(issue=issue, pdf_url=pdf_url(issue),
                                                        unsubscribe_url=unsubscribe_url))


def email_text(issue):
    return env.get_template("email.txt").render(**_ctx(issue=issue, pdf_url=pdf_url(issue)))


def pdf_path(issue, out_dir=None):
    return (out_dir or config.SITE) / "pdf" / f"issue-{issue['number']}.pdf"


def pdf_url(issue):
    return f"{config.SITE_URL}/pdf/issue-{issue['number']}.pdf"


def build_pdf(issue, out_dir=None):
    """Printable A4 study sheet for one issue (hints always shown, tick boxes, deep-dive answer)."""
    from weasyprint import HTML
    path = pdf_path(issue, out_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    html = env.get_template("pdf.html").render(**_ctx(issue=issue))
    HTML(string=html, base_url=str(config.ROOT)).write_pdf(path)
    print(f"pdf: {path.relative_to(config.ROOT)} ({path.stat().st_size // 1024} KB)")
    return path


def starter_pack(bank, n=15):
    """'Start here' page: the strongest fundamentals, two per topic."""
    picked = []
    for t in config.TOPICS:
        cands = [q for q in bank.questions if q["topic"] == t and not q["duplicate_of"]
                 and q["difficulty"] in ("easy", "medium") and q["origin"] == "seed"]
        cands.sort(key=lambda q: (-(q.get("quality") or 3), q["difficulty"] != "easy", len(q["text"])))
        picked += cands[:2]
    return picked[:n]


def build_site(extra_issue=None, out_dir=None):
    out = out_dir or config.SITE
    bank = Bank()
    live = [q for q in bank.questions if not q["duplicate_of"]]
    _STATS.update(bank=len(live), bank_round=f"{len(live) // 100 * 100:,}+",
                  fresh=sum(1 for q in live if q["origin"] == "fresh"))
    issues = list(bank.issues) + ([extra_issue] if extra_issue else [])
    issues.sort(key=lambda i: i["number"], reverse=True)
    (out / "issues").mkdir(parents=True, exist_ok=True)
    shutil.copy(config.TEMPLATES / "style.css", out / "style.css")
    pages = {
        "index.html": env.get_template("index.html").render(**_ctx(latest=issues[0] if issues else None,
                                                                   recent=issues[1:6], root="")),
        "archive.html": env.get_template("archive.html").render(**_ctx(issues=issues, root="")),
        "start.html": env.get_template("start.html").render(**_ctx(questions=starter_pack(bank), root="")),
    }
    for iss in issues:
        pages[f"issues/{iss['number']}.html"] = env.get_template("issue_page.html").render(
            **_ctx(issue=iss, root="../"))
    for path, html in pages.items():
        (out / path).write_text(html)
    (out / ".nojekyll").write_text("")
    print(f"site: {len(pages)} pages written to {out}")
