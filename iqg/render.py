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


def _ctx(**kw):
    return dict(name=config.NEWSLETTER_NAME, tagline=config.TAGLINE, site_url=config.SITE_URL,
                form_action=config.SUBSCRIBE_FORM_ACTION, topics=config.TOPICS, **kw)


def email_html(issue, preview=False):
    return env.get_template("email.html").render(**_ctx(issue=issue, preview=preview))


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
