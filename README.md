# The AI/ML Interview Drop

**15 AI/ML engineer interview questions, every Monday and Thursday.** Collected automatically from what
engineers are posting right now, deduplicated, balanced across topics, with a hint for each question,
a worked "deep dive" answer and a printable PDF study sheet.

- **Website & subscribe:** https://shubham-00787.github.io/ai-interview-drop/
- **Start here (15 essentials):** https://shubham-00787.github.io/ai-interview-drop/start.html
- **Archive:** https://shubham-00787.github.io/ai-interview-drop/archive.html

Runs entirely on free tiers, with no servers to look after.

---

## What a reader gets

| | |
|---|---|
| **Email** (Mon & Thu) | Short summary: headline, the 15 questions grouped by topic, a deep-dive teaser, and buttons for the PDF and online practice |
| **PDF study sheet** | A4, 3–4 pages: every question with difficulty, source and "what a strong answer covers", tick boxes, and the deep-dive model answer |
| **Web practice mode** | Show/hide hints, "I can answer this" ticks with a progress bar (saved in the browser), topic jump links, light/dark mode |
| **Start here page** | 15 essential questions, two from each area |

## How it works

```
Every day, 03:17 UTC                                  .github/workflows/collect.yml
  Hacker News + Reddit + Tavily web search (incl. search-indexed LinkedIn / X posts)
    → Gemini pulls out real interview questions and rates them (topic, difficulty, quality 1–5)
    → duplicates in meaning are merged with local embeddings; a repeat of an older question marks it "trending"
    → data/questions.json   (Sundays: also re-reads the openly licensed question repos below)

Monday & Thursday, 06:00 UTC                          .github/workflows/publish.yml
  pick 15: ~5 asked this week + ~10 from the bank, rotating topics and mixing easy / medium / hard
    → Gemini writes the headline, a hint per question and one deep-dive answer
    → website issue page + PDF are committed and published on GitHub Pages
    → once the PDF is live, the email goes to every subscriber
```

Every source and service is optional: anything without a key is skipped, and without an LLM key questions
are tagged by keyword rules, so the pipeline always runs.

**Topics:** ML fundamentals · deep learning · LLMs & transformers · RAG & agents · MLOps & production ·
ML/AI system design · stats & math · coding & implementation.

## How the 15 questions are picked

The logic is in `select()` in [`iqg/issue.py`](iqg/issue.py).

**Eligible:** never sent before (duplicates already merged), and an AI quality rating of at least 3 out of 5.

**Pass 1: up to 5 "asked this week" questions**
- *Fresh* means found in a post from the last 7 days, **or** an older bank question that someone asked again
  this week (it's then shown as trending).
- Ranked by `score = quality + 0.5 × (times seen in different posts − 1)`, with that bonus capped at +2.
- At most 2 per topic, so one hot topic can't take over.

**Pass 2: fill up to 15 from the bank**
- **Topic rotation:** topics that appeared least in the last 4 issues go first; each topic gets at most 3
  per issue, so an issue covers most of the 8 areas.
- **Difficulty mix:** cycles easy → medium → medium → hard (roughly 4 easy / 7 medium / 4 hard).
- **Variety:** a random pick among questions within 0.5 of the best score for that topic and difficulty,
  seeded by the issue number so a re-run gives the same issue.
- If every topic reaches its cap, the cap is relaxed and the highest-scoring questions left are taken.

**Then**
- **Deep dive:** a medium or hard question, preferring one asked this week, then the highest score.
- **Order:** grouped by topic, then easy to hard.
- **No repeats:** each question is marked as sent and never picked again.

**Supply:** about 1,600 unsent questions, roughly 100 issues (a year at two a week) even with no new posts.
Daily collection adds about 5–15 new questions a day.

**Limit:** everyone gets the same 15 questions. Picks are based on the AI's quality ratings, not on what
each reader already knows, and practice-mode ticks stay in the reader's browser.

**Settings:** `QUESTIONS_PER_ISSUE` (15), `FRESH_PER_ISSUE` (5) and `FRESH_DAYS` (7) are in
`iqg/config.py`. The topic cap (3), quality cut-off (3) and difficulty cycle are in `iqg/issue.py`.

## Free services used

| Job | Service | Free limit |
|---|---|---|
| Scheduling and running | GitHub Actions (public repo) | Unlimited minutes |
| Website and PDFs | GitHub Pages | Free |
| Question extraction, tagging and hints | Google Gemini API (OpenRouter free models as backup) | Daily free quota |
| Web search | Tavily | 1,000 credits/month (6 searches/day used) |
| Subscribers, Subscribe box, sending | Brevo | 300 emails/day |
| Optional inbox-friendly sending | Your Gmail via App Password | ~450 emails/day |
| Duplicate detection | fastembed (`bge-small-en-v1.5`), runs inside Actions | Free |

## Repository layout

```
iqg/
  config.py     all settings: name, topics, search queries, seed repos, limits, model names
  sources.py    Hacker News, Reddit, Tavily and GitHub seed-repo collectors
  llm.py        Gemini / OpenRouter calls: extract, tag, write hints + headline + deep dive
  pipeline.py   daily job: collect → extract → tag → dedupe
  issue.py      pick 15, write hints, publish, send, send-test
  render.py     website, email (HTML + text) and PDF rendering
  send.py       Brevo campaign sending
  gmail.py      optional Gmail sending + email-based unsubscribes (stored hashed)
templates/      website, email and PDF templates + stylesheet
data/           question bank, issues, processed sources (committed by the workflows)
docs/           the generated website served by GitHub Pages
```

## Commands

```bash
python -m iqg collect            # daily job
python -m iqg seed               # re-read the curated question repos
python -m iqg publish --dry-run  # preview into preview/ (email, site, PDF) without sending or recording
python -m iqg publish            # publish the next issue and email it
python -m iqg send-latest        # email the newest issue if it hasn't been emailed yet
python -m iqg send-test          # email the newest issue to yourself only (Gmail)
python -m iqg site               # rebuild the website
```

PDF rendering uses WeasyPrint, which needs Pango (`brew install pango` on macOS; installed automatically in Actions).

## Setup

Secrets and variables live in **Settings → Secrets and variables → Actions**.

| What | Where to get it | Stored as |
|---|---|---|
| Gemini API key | aistudio.google.com/apikey | secret `GEMINI_API_KEY` |
| Tavily key | app.tavily.com | secret `TAVILY_API_KEY` |
| Brevo API key (Email campaigns: All, Contacts: Read) | Brevo → SMTP & API → API keys | secret `BREVO_API_KEY` |
| Brevo list ID | Brevo → Contacts → Lists | variable `BREVO_LIST_ID` |
| Sender email (verified in Brevo) | Brevo → Senders | variable `SENDER_EMAIL` |
| Subscribe form endpoint | Brevo → Contacts → Forms → Share → HTML embed `action="…"` | variable `SUBSCRIBE_FORM_ACTION` |
| Site URL | GitHub Pages | variable `SITE_URL` |
| *Optional:* OpenRouter key | openrouter.ai/keys | secret `OPENROUTER_API_KEY` |
| *Optional:* Reddit app (new apps may need Reddit's approval) | reddit.com/prefs/apps | secrets `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` |
| *Optional:* Gmail App Password | myaccount.google.com/apppasswords (needs 2-Step Verification) | secret `GMAIL_APP_PASSWORD` |
| *Optional:* attach the PDF to the email too | – | variable `ATTACH_PDF` = `true` |

GitHub Pages: **Settings → Pages → Deploy from a branch → `main` / `docs`**.

### Email delivery

Sending as a Brevo campaign from a `@gmail.com` address often lands in spam, because the email claims to be
from Gmail but comes from Brevo's servers. Two free fixes:

1. **Gmail sending (built in):** add `GMAIL_APP_PASSWORD`. Each subscriber then gets a personal email sent by
   Gmail itself, with a plain-text part and a `List-Unsubscribe` header. Subscribers are still read from the
   Brevo list. Unsubscribe requests arrive as "unsubscribe" emails, which are read over IMAP before each send,
   and only SHA-256 hashes of those addresses are stored. Run **Actions → Send me a test email** to check.
2. **Own domain:** authenticate a domain in Brevo (Senders, domains → Domains) and use an address on it.

Until then, mark the first issue as **Not spam** in your mail app.

## Tuning

Most settings are in `iqg/config.py` (selection limits are in `iqg/issue.py`): newsletter name and tagline, questions per issue (`15`) and fresh ones (`5`),
topics and keyword rules, search queries and how many run per day, seed repos, LLM model names and call budget,
duplicate threshold (`0.91`), and the Gmail daily cap.

## Credits

Seed questions come from these openly licensed repositories, and every question links back to its source:
[amitshekhariitbhu/ai-engineering-interview-questions](https://github.com/amitshekhariitbhu/ai-engineering-interview-questions) (Apache-2.0),
[amitshekhariitbhu/machine-learning-interview-questions](https://github.com/amitshekhariitbhu/machine-learning-interview-questions) (Apache-2.0),
[pallavi-shekhar/ai-engineering-interview-questions-company-wise](https://github.com/pallavi-shekhar/ai-engineering-interview-questions-company-wise) (Apache-2.0),
[ombharatiya/AI-Engineer-Interview-Questions](https://github.com/ombharatiya/AI-Engineer-Interview-Questions) (MIT),
[alirezadir/machine-learning-interviews](https://github.com/alirezadir/machine-learning-interviews) (MIT),
[alexeygrigorev/data-science-interviews](https://github.com/alexeygrigorev/data-science-interviews) (CC-BY-4.0).
Fresh questions are short rewrites of what people asked publicly, each linked to the original post.
