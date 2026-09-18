# LocalLens

A news intelligence platform that connects global and national stories to their local impact.

**Initial locale:** San Diego, CA
**Interface:** Streamlit web app
**Deploy:** Heroku (Eco dyno)

## Architecture

```
locallens/
├── app.py                    # Streamlit entrypoint
├── agents/
│   ├── discovery_agent.py    # Semantic matching via BGE-M3
│   ├── validation_agent.py   # LLM connection validation
│   └── deep_dive_agent.py    # Deep analysis generation
├── data/
│   ├── newsapi_client.py     # NewsAPI.org wrapper
│   ├── guardian_client.py    # The Guardian API wrapper
│   ├── rss_client.py         # RSS feed parser
│   ├── ingestion_scheduler.py# APScheduler for periodic ingestion
│   └── supabase_client.py    # Supabase + pgvector client
├── ui/
│   ├── components/
│   │   ├── connection_card.py
│   │   ├── card_feed.py
│   │   ├── deep_dive_modal.py
│   │   └── sidebar.py
│   └── styles.py
├── llm_client.py             # Central LLM wrapper with LangSmith tracing
├── config.py                 # Settings loaded from env vars
├── evals/
│   ├── test_connections.py
│   └── fixtures/
│       └── connection_pairs.json
├── .env.example
├── requirements.txt
├── Procfile
└── README.md
```

## Quick Start

```bash
# Clone and setup
git clone <repo> && cd locallens
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Fill in your API keys

# Run
streamlit run app.py
```

## Key Design Decisions

See [docs/DESIGN.md](docs/DESIGN.md) for full architectural decisions.

## License

MIT
