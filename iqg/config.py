"""All tunable settings in one place. Secrets come from environment variables."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SITE = ROOT / "docs"  # GitHub Pages serves this folder
TEMPLATES = ROOT / "templates"

# ---- Newsletter identity (edit these) -------------------------------------
NEWSLETTER_NAME = (os.getenv("NEWSLETTER_NAME") or "The AI/ML Interview Drop")
TAGLINE = "15 AI/ML engineer interview questions, twice a week. Collected from what practitioners are asking right now."
SITE_URL = (os.getenv("SITE_URL") or "https://shubham-00787.github.io/ai-interview-drop")
# Brevo hosted-form endpoint for the Subscribe box (Brevo > Contacts > Forms > Share > embed "action" URL)
SUBSCRIBE_FORM_ACTION = (os.getenv("SUBSCRIBE_FORM_ACTION") or "")
QUESTIONS_PER_ISSUE = 15
FRESH_PER_ISSUE = 5          # questions found in the last FRESH_DAYS
FRESH_DAYS = 7

# ---- Topics ----------------------------------------------------------------
TOPICS = {
    "ml_fundamentals": "ML Fundamentals",
    "deep_learning": "Deep Learning",
    "llms": "LLMs & Transformers",
    "rag_agents": "RAG & Agents",
    "mlops": "MLOps & Production",
    "system_design": "ML / AI System Design",
    "stats_math": "Stats & Math",
    "coding": "Coding & Implementation",
}
# keyword -> topic, used when no LLM is available
TOPIC_KEYWORDS = [
    ("rag_agents", ["rag", "retriev", "agent", "tool use", "tool-use", "mcp", "vector", "embedding", "rerank", "chunk"]),
    ("llms", ["llm", "transformer", "attention", "token", "prompt", "fine-tun", "lora", "rlhf", "dpo", "hallucinat", "quantiz", "gpt", "bert", "kv cache", "decoding", "context window"]),
    ("system_design", ["design a", "design an", "system design", "architecture", "recommend", "ranking system", "at scale"]),
    ("mlops", ["deploy", "production", "monitor", "drift", "pipeline", "serving", "latency", "mlops", "llmops", "a/b", "feature store"]),
    ("deep_learning", ["neural", "cnn", "rnn", "lstm", "backprop", "gradient", "batch norm", "dropout", "activation", "gan", "diffusion", "convolution", "vanishing"]),
    ("stats_math", ["probability", "distribution", "variance", "bayes", "hypothesis", "p-value", "statistic", "expected value", "eigen", "matrix", "likelihood"]),
    ("coding", ["implement", "write a function", "code", "python", "numpy", "pytorch", "sql"]),
]
DEFAULT_TOPIC = "ml_fundamentals"

# ---- Sources ---------------------------------------------------------------
HN_QUERIES = ["machine learning interview", "ML engineer interview", "AI engineer interview", "LLM interview question", "data scientist interview"]
REDDIT_SUBS = ["MachineLearning", "learnmachinelearning", "cscareerquestions", "datascience", "LocalLLaMA"]
TAVILY_QUERIES = [  # rotated, TAVILY_PER_DAY used each day (free plan ~1000 credits/month)
    'site:linkedin.com/posts "machine learning engineer" interview questions',
    'site:linkedin.com/posts "AI engineer" interview questions asked',
    'site:x.com "ML interview" question',
    'site:x.com "LLM" interview question asked',
    "AI engineer interview experience questions asked 2026",
    "machine learning engineer interview experience onsite questions",
    "LLM engineer interview questions RAG agents asked",
    "ML system design interview question asked recently",
    "MLOps interview questions asked this week",
    "GenAI engineer interview questions blog",
]
TAVILY_PER_DAY = 6

# Seed repos: only permissively licensed ones. (repo, branch path filter, license, attribution)
SEED_REPOS = [
    ("amitshekhariitbhu/ai-engineering-interview-questions", "", "Apache-2.0"),
    ("amitshekhariitbhu/machine-learning-interview-questions", "", "Apache-2.0"),
    ("pallavi-shekhar/ai-engineering-interview-questions-company-wise", "", "Apache-2.0"),
    ("ombharatiya/AI-Engineer-Interview-Questions", "questions.md", "MIT"),
    ("alirezadir/machine-learning-interviews", "src/", "MIT"),
    ("alexeygrigorev/data-science-interviews", "theory.md", "CC-BY-4.0"),
]

# ---- LLM (free tiers) ------------------------------------------------------
GEMINI_MODEL = (os.getenv("GEMINI_MODEL") or "gemini-flash-lite-latest")
OPENROUTER_MODEL = (os.getenv("OPENROUTER_MODEL") or "meta-llama/llama-3.3-70b-instruct:free")
MAX_LLM_CALLS_PER_RUN = int((os.getenv("MAX_LLM_CALLS_PER_RUN") or "40"))
TAG_BATCH = 40          # untagged seed questions tagged per LLM call
DEDUPE_THRESHOLD = 0.91  # cosine similarity above which two questions are "the same"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"

# ---- Email (Brevo free plan) -----------------------------------------------
BREVO_LIST_ID = (os.getenv("BREVO_LIST_ID") or "")
SENDER_NAME = (os.getenv("SENDER_NAME") or NEWSLETTER_NAME)
SENDER_EMAIL = (os.getenv("SENDER_EMAIL") or "")
