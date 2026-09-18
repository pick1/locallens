# LocalLens

A **news intelligence platform** that connects global and national stories to their local impact.

**Initial locale:** San Diego, CA  
**Interface:** Streamlit web app  
**AI Stack:** LangGraph + GPT-4o + BGE-M3 embeddings  
**Storage:** Supabase + pgvector  
**Deploy:** Heroku (Eco dyno)

---

## Quick Start

```bash
# 1. Clone and set up
git clone <repo> && cd locallens
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Install spaCy model (for NER in deep-dive analysis)
python -m spacy download en_core_web_sm

# 3. Configure
cp .env.example .env
# Fill in your API keys (see below)

# 4. Set up Supabase
# Run the SQL in data/schema.sql in your Supabase SQL editor

# 5. Run
streamlit run app.py
# Or: streamlit run app.py --server.port=8501

# 6. Run tests
pytest evals/ -v
```

## Demo Mode

LocalLens works **without any API keys** in demo mode. It includes:
- **3 seed connection cards** (Iran tensions → San Diego Muslim community,
  Sierra Nevada drought → Imperial Valley water, Port automation →
  San Diego port shift)
- **20 eval fixtures** for testing the validation agent
- **Mock embeddings** (deterministic, no HF API needed)

Demo mode activates automatically when Supabase credentials are not set.

## Architecture

```
locallens/
├── app.py                    # Streamlit entrypoint
├── config.py                 # Settings from env vars (no hardcoded secrets)
├── llm_client.py             # Central LLM wrapper with LangSmith tracing
├── agents/
│   ├── discovery_agent.py    # Stage 1: BGE-M3 semantic matching
│   ├── validation_agent.py   # Stage 2: GPT-4o connection validation
│   └── deep_dive_agent.py    # Deep analysis: timeline, stakeholders, precedents
├── data/
│   ├── supabase_client.py    # Supabase + pgvector client
│   ├── newsapi_client.py     # NewsAPI.org wrapper
│   ├── guardian_client.py    # The Guardian API wrapper
│   ├── rss_client.py         # RSS feed parser (local SD sources)
│   ├── ingestion_scheduler.py# APScheduler for periodic ingestion
│   └── schema.sql            # SQL migration for Supabase
├── ui/
│   ├── styles.py             # Custom CSS design system
│   └── components/
│       ├── connection_card.py # Single card renderer
│       ├── card_feed.py       # Ranked card feed
│       ├── deep_dive_modal.py # st.dialog() modal analysis
│       └── sidebar.py         # Locale switcher + topic filters
├── evals/
│   ├── test_connections.py   # Pytest eval suite
│   └── fixtures/
│       └── connection_pairs.json  # 20 labeled eval pairs
├── docs/
│   └── DESIGN.md             # Architecture and design decisions
├── .env.example
├── requirements.txt
├── Procfile
└── README.md
```

## Two-Stage Connection Pipeline

### Stage 1: Discovery (`agents/discovery_agent.py`)
- Fetches recent global/national and local articles from Supabase
- Embeds un-embedded articles using BGE-M3 (via HuggingFace API)
- Runs cosine similarity search via pgvector
- Returns candidate pairs above threshold (default: 0.35)

### Stage 2: Validation (`agents/validation_agent.py`)
- For each candidate pair, calls GPT-4o with structured output
- Assesses: is there a real connection? How confident?
- Generates: card title, body, mechanism text, topic categories
- Flags politically sensitive content for balanced framing

## Demo Mode Seed Cards

| # | Global Story | Local Impact | Confidence |
|---|-------------|--------------|------------|
| 1 | US-Iran tensions, Strait of Hormuz | San Diego Muslim-American community | 🔴 High |
| 2 | Sierra Nevada drought (40% snowpack) | Imperial Valley farmers, SD water | 🔴 High |
| 3 | Federal port automation rules | Port of San Diego, ILWU Local 29 | 🟡 Medium |

## API Keys Required (for production)

| Key | Source | Used For |
|-----|--------|----------|
| `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com) | GPT-4o connection validation & deep dive |
| `SUPABASE_URL` | [supabase.com](https://supabase.com) | PostgreSQL + pgvector |
| `SUPABASE_KEY` | Supabase dashboard | Database access |
| `NEWSAPI_KEY` | [newsapi.org](https://newsapi.org) | Global news headlines |
| `GUARDIAN_API_KEY` | [open-platform.theguardian.com](https://open-platform.theguardian.com) | International news |
| `HF_API_TOKEN` (optional) | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) | BGE-M3 embeddings |
| `TAVILY_API_KEY` (optional) | [tavily.com](https://tavily.com) | Historical context search |
| `LANGCHAIN_API_KEY` (optional) | [smith.langchain.com](https://smith.langchain.com) | LLM tracing & evals |

## Deployment

### Heroku
```bash
heroku create locallens
heroku addons:create heroku-postgresql:mini  # not needed if using Supabase
heroku config:set OPENAI_API_KEY=...
heroku config:set SUPABASE_URL=...
heroku config:set SUPABASE_KEY=...
# ... set all env vars from .env.example
git push heroku main
```

### GitHub Actions CI
Tests run automatically on push to `main`:
```yaml
# See .github/workflows/test.yml (create if needed)
```

## Eval Suite

Run the evaluation harness:
```bash
pytest evals/ -v
```

Three eval dimensions:
1. **Connection validity** — does the agent correctly identify real connections?
2. **RAGAS faithfulness** — is the synthesis faithful to source articles?
3. **RAGAS answer relevancy** — is the local angle genuinely relevant?

## Known Limitations

- **99/day NewsAPI requests** on free tier — MVP prioritizes headlines
- **No real embeddings** without `HF_API_TOKEN` — uses mock vectors
- **Single-dyno ingestion** — stops when no user is running the app
- **San Diego seed data** — other locales need curated RSS feeds
- **No user accounts** — bookmarks are session-only

## License

MIT

---

*Built with Streamlit, LangGraph, Supabase + pgvector, and GPT-4o.*
