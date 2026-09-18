# LocalLens — Architecture & Design Decisions

## Overview

LocalLens is a news intelligence platform that connects global and national
stories to their predicted local impact. It uses a **direct generation**
pipeline: global headlines + locale profile → AI generates local impact analysis.
There is no matching to existing local articles — the system **scoops** local
media by predicting impacts before they're reported.

## Architecture

```
User (Browser)
    │
    ▼
┌─────────────────────────────────────────────┐
│              Streamlit (app.py)             │
│                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Sidebar  │  │ CardFeed │  │DeepDive  │  │
│  │          │  │  (Scoop  │  │  Modal   │  │
│  │          │  │  Cards)  │  │          │  │
│  └──────────┘  └──────────┘  └──────────┘  │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│           Connection Pipeline               │
│                                             │
│  ┌──────────────────┐  ┌─────────────────┐  │
│  │HeadlineMonitor   │─▶│LocalImpactGen   │  │
│  │(relevance scorer)│  │(GPT-4o struct)  │  │
│  └──────────────────┘  └────────┬─────────┘  │
│                                 │             │
│  ┌──────────────────────────────▼──────────┐  │
│  │          Deep Dive Agent                │  │
│  │  (LLM + NER + Tavily web search)        │  │
│  └──────────────────┬──────────────────────┘  │
└─────────────────────┼─────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│               Data Layer                     │
│                                             │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐  │
│  │ Supabase │ │ NewsAPI  │ │ Locale      │  │
│  │+pgvector │ │ Guardian │ │ Profiles    │  │
│  │          │ │ Feeds    │ │ (JSONB)     │  │
│  └──────────┘ └──────────┘ └─────────────┘  │
└─────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Why "scoop" architecture instead of article matching?

**Old approach:** Match global articles to local articles via embedding
similarity → LLM validates pairs → card. This requires a local article to
already exist, meaning LocalLens was just summarizing existing coverage.

**New approach (scoop):** Global headline + locale profile → AI generates
local impact analysis directly. The locale profile contains rich context
about a city's demographics, economy, geography, infrastructure, military
presence, and active local issues. The AI uses this to PREDICT what the
local impact will be — producing original analysis before local journalists
cover the angle.

**Why this matters:** LocalLens can now generate analysis that would "scoop"
traditional media. Example: when federal port automation rules were announced,
LocalLens could predict the cargo diversion effects on Port of San Diego,
ILWU Local 29 labor implications, and Barrio Logan environmental justice
concerns — before Voice of San Diego or KPBS covered the local angle.

### 2. One-stage generation vs. two-stage matching

Instead of O(n×m) embedding similarity + O(candidates) LLM validation,
we use a single O(headlines) generation pass:

1. **HeadlineMonitorAgent** scores each global headline for local relevance
   using the locale profile (keyword heuristics in demo, LLM scoring in prod)
2. **LocalImpactGenerator** generates full impact analysis for relevant headlines

**Trade-off:** We lose the semantic matching signal (e.g., finding a local
article that corroborates the predicted impact). Mitigated by storing locale
profiles with deep enough context that the AI makes specific, grounded
predictions.

### 3. Why LangGraph instead of a simple chain?

Each agent needs to handle retries, partial failures, and state
persistence between steps. LangGraph's node-edge graph lets the
DeepDiveAgent parallelize the Tavily web search and NER extraction,
then merge results — not possible with a linear chain.

**Current implementation:** Agents use a function-call pattern rather
than full LangGraph graphs. This is acceptable for the MVP; a true
LangGraph StateGraph should replace the orchestrator when the project
needs more sophisticated branching or human-in-the-loop feedback.

### 4. Why Supabase + pgvector instead of Pinecone?

Supabase gives both the relational store (articles, connections,
locale profiles) and optional vector index in a single free-tier service,
simplifying ops. pgvector is used for article search (still useful for
finding related stories), not for connection discovery.

### 5. Why APScheduler inside Streamlit instead of a separate worker?

For an MVP on Heroku Eco dyno (single dyno), a separate worker dyno
costs extra. APScheduler runs the ingestion job as a background thread
inside the Streamlit process.

**Trade-off:** Ingestion stops when no one is using the app. Acceptable
for MVP. Documented in README so it can be promoted to a separate worker
when the project grows.

### 6. Why no user accounts?

Accounts add auth complexity, GDPR surface area, and onboarding friction
with zero benefit for a read-only aggregator MVP. Session state handles
bookmarks. Add auth (Supabase Auth) only if user-specific saved feeds
become a priority feature.

### 7. Why Streamlit (not React/Next.js)?

Streamlit provides:
- Zero frontend build step
- Python-only development
- Built-in state management via st.session_state
- Fast iteration for data-heavy apps
- Heroku-friendly deployment with a Procfile

**Trade-off:** Less flexible UI customization than a dedicated frontend.
Custom CSS and the st.dialog component mitigate this for the MVP.

## Data Model

```
articles
├── id: UUID (PK)
├── url: TEXT (unique)
├── title: TEXT
├── body: TEXT
├── source: TEXT
├── source_level: ENUM(global|national|state|local)
├── locale: TEXT
├── published_at: TIMESTAMPTZ
├── created_at: TIMESTAMPTZ
└── embedding: VECTOR(1024)  — optional, for article search

connections
├── id: UUID (PK)
├── global_article_id: UUID (FK → articles)
├── local_article_id: UUID (FK → articles, NULLABLE)  — optional in scoop mode
├── locale: TEXT
├── confidence: ENUM(low|medium|high)
├── mechanism_text: TEXT
├── card_title: TEXT
├── card_body: TEXT
├── topics: TEXT[]
├── is_sensitive: BOOLEAN
├── scoop_angle: TEXT          — what makes this analysis original
├── neighborhoods_affected: TEXT
├── created_at: TIMESTAMPTZ
└── cached_until: TIMESTAMPTZ

locale_profiles
├── id: UUID (PK)
├── locale_slug: TEXT (unique)
├── display_name: TEXT
├── metro_code: TEXT
├── context_json: JSONB        — rich: demographics, economy, geography,
│                                 infrastructure, military, community orgs
└── updated_at: TIMESTAMPTZ
```

## Locale Profile — The Engine of Scoop Analysis

The locale profile is the most important piece of the architecture. It
provides the AI with hyper-local context to generate specific, grounded
predictions. Each profile includes:

| Section | Content | Example (San Diego) |
|---------|---------|-------------------|
| Demographics | Population, income, ethnic groups, languages, diaspora communities | 26% foreign-born, 12K Iranian diaspora, 15K Somali |
| Economy | GDP, sectors, major exports, trade data | $255B GDP, $60B cross-border trade |
| Employers | Major employers with headcounts | UC San Diego 35K, NAVWAR 45K |
| Industries | Key sectors with specifics | Defense contracting, biotech, wireless |
| Geography | Region, climate, water sources, wildfire/seismic risk | 70mi coastline, Colorado River dependent |
| Infrastructure | Port, airport, transit, energy grid, water | 2 cargo terminals, 1 runway, SDG&E |
| Military | Bases, personnel count, contractors | 100K+ personnel, $20B economic impact |
| Governance | City council, county, special districts | 9 council districts, Port District, MTS |
| Active Issues | Current local debates | Housing, sewage crisis, airport capacity |
| Community | Key community orgs per neighborhood | CAIR SD, Environmental Health Coalition |

## San Diego Profile Highlights (Seed)

The seed profile for San Diego, CA has 12 major sections covering the
most detail-rich locale context of any US city. This enables the AI to
make specific predictions like:
- *Which neighborhoods are affected* (Barrio Logan, City Heights, El Cajon)
- *Which organizations are involved* (CAIR SD, ILWU Local 29, SDG&E)
- *Which infrastructure is impacted* (Port of SD terminals, Carlsbad Desal, I-5 corridor)
- *Which demographic groups* (Iranian diaspora, Imperial Valley farmworkers)

## Connections Confidence Rubric

| Confidence | Criteria |
|------------|----------|
| **High**   | Direct causal chain with named local entities (port policy → Port of SD, federal funding → specific SDG&E project) |
| **Medium** | Plausible mechanism, indirect evidence (tariff changes → price effects on local consumers) |
| **Low**    | Thematic overlap only, speculative link |

## Topic Categories

- Economy
- Environment
- Community & Demographics
- Public Health
- Policy
- Infrastructure

## Politically Sensitive Topics

Topics flagged as sensitive trigger a balanced-framing system prompt:
- Foreign conflicts
- Immigration and border policy
- Policing and criminal justice
- Abortion policy

The prompt variant presents multiple perspectives, avoids attributing
intent to named political figures, and flags the card with a
"Multiple perspectives" badge in the UI.

## Performance Targets

| Operation | Target |
|-----------|--------|
| Connection card generation | < 8 seconds |
| Streamlit page load | < 2 seconds |

## Known Limitations

1. **Single-dyno ingestion:** Ingestion stops when no user is running
   the app. Needs a separate worker dyno for 24/7 ingestion.

2. **99/day NewsAPI limit:** Free tier allows only 100 requests/day.
   The MVP prioritizes global headlines over search endpoints.

3. **Demo mode uses heuristic scoring:** Without OPENAI_API_KEY, the
   relevance scorer uses keyword heuristics. These are less accurate
   than LLM-based scoring.

4. **No historical data:** Only articles ingested after deployment
   are available. A one-time backfill script is needed for historical
   connection discovery.

5. **San Diego seed data only:** Other locales have basic demographics
   but no curated RSS feeds or seed connection cards. The architecture
   supports adding any US city.

6. **AI predictions are not journalism:** Generated local impact
   analyses are AI-synthesized predictions. They should be verified
   with original sources before being treated as factual.

## Future Improvements

- Separate worker dyno for 24/7 ingestion
- GNews API fallback for expanded coverage
- User accounts with saved feeds (Supabase Auth)
- Notification system (email/SMS for new connections)
- Real-time streaming via WebSocket
- Contributor API for adding locale profiles
- Automated post-facto validation: flag cards where local coverage later confirms or contradicts the AI prediction
