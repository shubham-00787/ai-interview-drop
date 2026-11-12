# The AI/ML Interview Drop

A free, fully automated newsletter: **15 AI/ML engineer interview questions, every Monday and Thursday**,
collected from what practitioners are posting, deduplicated, tagged and balanced across topics.

Everything runs on free tiers: GitHub Actions (schedule), GitHub Pages (website), Gemini / OpenRouter
free models (extraction + hints), Tavily free search, Reddit and Hacker News APIs, and Brevo's free plan
(subscribers + sending, up to 300 emails/day).

## How it works

```
daily 03:17 UTC   collect.yml   HN + Reddit + Tavily web search (incl. search-indexed LinkedIn/X posts)
                                → LLM extracts real interview questions → tag topic/difficulty/quality
                                → dedupe by meaning (local embeddings) → data/questions.json
Sundays           collect.yml   also re-reads the curated open-source question repos (licensed MIT/Apache/CC-BY)
Mon & Thu 06:00   publish.yml   pick 15 (≈5 asked this week + 10 from the bank, rotated by topic and difficulty)
                                → LLM writes "what a strong answer covers" hints + one deep-dive answer
                                → website issue page (docs/) → Brevo campaign to all subscribers
```

Any source without a key is skipped; without an LLM key, keyword rules tag questions so it still runs.

## Commands

```bash
python -m iqg collect            # daily job
python -m iqg seed               # re-read curated repos
python -m iqg publish --dry-run  # build preview/email.html + preview/site/ without sending
python -m iqg publish            # real issue
python -m iqg site               # rebuild the website
```

## One-time setup

| What | Where | Goes in GitHub as |
|---|---|---|
| Gemini API key (free) | aistudio.google.com → Get API key | secret `GEMINI_API_KEY` |
| OpenRouter key (optional fallback) | openrouter.ai → Keys | secret `OPENROUTER_API_KEY` |
| Tavily key (free 1,000 credits/mo) | app.tavily.com | secret `TAVILY_API_KEY` |
| Reddit app (optional; may need approval) | reddit.com/prefs/apps → "script" app | secrets `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` |
| Brevo API key | Brevo → SMTP & API → API keys | secret `BREVO_API_KEY` |
| Brevo list ID | Brevo → Contacts → Lists | variable `BREVO_LIST_ID` |
| Verified sender email | Brevo → Senders | variable `SENDER_EMAIL` |
| Subscribe form action URL | Brevo → Contacts → Forms → (double opt-in form) → Share → embed code `action="…"` | variable `SUBSCRIBE_FORM_ACTION` |
| Site URL | after enabling Pages | variable `SITE_URL` |
| Gmail App Password (sends issues from your Gmail, so they land in the inbox) | myaccount.google.com/apppasswords (needs 2-Step Verification) | secret `GMAIL_APP_PASSWORD` |

With `GMAIL_APP_PASSWORD` set, issues are emailed one-by-one from `SENDER_EMAIL` via Gmail (≈450/day cap);
subscribers are still read from the Brevo list. Unsubscribes arrive as "unsubscribe" emails (Gmail's built-in
button or the footer link) and are read over IMAP before each send; only hashed addresses are stored.
Without it, issues go out as Brevo campaigns. Run the **Send me a test email** workflow to check delivery.

Set secrets with `gh secret set NAME` (it prompts for the value) and variables with `gh variable set NAME`.
GitHub Pages: Settings → Pages → Deploy from branch → `main` / `docs`.

## Tuning

Everything lives in `iqg/config.py`: newsletter name, topics, search queries, seed repos, questions per issue,
LLM model names, duplicate threshold.

## Credits

Seed questions come from these openly licensed repos (each question links back to its source):
amitshekhariitbhu/ai-engineering-interview-questions (Apache-2.0),
amitshekhariitbhu/machine-learning-interview-questions (Apache-2.0),
pallavi-shekhar/ai-engineering-interview-questions-company-wise (Apache-2.0),
ombharatiya/AI-Engineer-Interview-Questions (MIT), alirezadir/machine-learning-interviews (MIT),
alexeygrigorev/data-science-interviews (CC-BY-4.0).
