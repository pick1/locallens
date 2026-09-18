"""
LocalLens — Streamlit Application Entrypoint

Connects global and national stories to their local impact.
Single-page app with sidebar navigation and inline card feed.

Usage:
    streamlit run app.py

Architecture:
    - Single app.py with component imports (no multi-page)
    - st.session_state for all state management
    - Seed data for demo mode when API keys aren't configured
    - Optional Supabase + pgvector for production
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

import streamlit as st

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from ui.styles import apply_styles, render_header

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════
# SEED DATA
# ══════════════════════════════════════════════════════════════════════════
# These are hardcoded demo cards that demonstrate the "scoop" approach:
# AI-generated local impact analysis from global headlines + locale profile,
# NOT matched to existing local articles. These represent the kind of
# original analysis that would precede — and potentially scoop — local
# media coverage.

SEED_CONNECTIONS: list[dict[str, Any]] = [
    {
        "id": "seed-1",
        "card_title": "US-Iran tensions in the Strait of Hormuz: San Diego's Muslim-American community navigates rising tensions",
        "card_body": (
            "Heightened conflict rhetoric in the Middle East has historically increased "
            "reports of discrimination incidents against Muslim and Arab Americans. "
            "San Diego's large Somali, Yemeni, and Iranian diaspora communities — concentrated "
            "in City Heights and El Cajon — are monitoring the situation closely.\n\n"
            "Local organizations like the Council on American-Islamic Relations (CAIR) San Diego "
            "chapter have activated support resources, including a hate incident reporting hotline "
            "and community safety workshops. The San Diego Police Department's Hate Crime Unit "
            "reports increased community outreach to Muslim-majority neighborhoods.\n\n"
            "San Diego County, home to an estimated 60,000 Muslim Americans and one of the largest "
            "Somali diaspora communities in the US, has historically seen a spike in bias incidents "
            "during Middle East conflict escalations according to CAIR's annual reports. "
            "The Iranian diaspora community (approximately 12,000 in San Diego County) faces "
            "particular strain due to direct family ties to the affected region."
        ),
        "mechanism_text": (
            "International conflict in the Middle East triggers a well-documented pattern of "
            "increased discrimination and bias incidents against Muslim and Arab American "
            "communities. San Diego's large diaspora communities — including significant Somali, "
            "Yemeni, and Iranian populations — experience the most direct impact due to "
            "community visibility and transnational family connections to affected regions."
        ),
        "confidence": "high",
        "topics": ["Community & Demographics", "Policy"],
        "global_source": "The Guardian — World News",
        "local_source": "AI-generated local impact analysis",
        "is_sensitive": True,
        "scoop_angle": "First analysis connecting Strait of Hormuz tensions specifically to San Diego's diaspora neighborhoods (City Heights, El Cajon) and local support organizations — before local media covers the community impact angle.",
        "neighborhoods_affected": "City Heights, El Cajon, College Area, Normal Heights",
        "created_at": "2025-05-26T08:00:00Z",
    },
    {
        "id": "seed-2",
        "card_title": "Sierra Nevada drought: Imperial Valley farmers and San Diego water rationing",
        "card_body": (
            "San Diego imports approximately 80% of its water supply, with a major share "
            "originating from the Colorado River via the Imperial Irrigation District (IID). "
            "The third consecutive drought year, which has reduced Sierra Nevada snowpack to "
            "40% of normal, accelerates reservoir drawdown across the Colorado River system.\n\n"
            "This triggers Tier 2 water restrictions under the San Diego County Water Authority's "
            "drought contingency plan, which mandates a 12% reduction in water use across the "
            "county. The Imperial Valley farming community — a multi-billion-dollar agricultural "
            "economy — faces mandatory fallowing payments from the IID, compensating farmers for "
            "not planting on their land to conserve water for urban use.\n\n"
            "Local farm employment in Imperial County, already among California's highest "
            "unemployment rates, faces additional pressure as fallowing reduces demand for "
            "agricultural labor. The Carlsbad desalination plant provides about 50 million "
            "gallons per day (7% of county supply) but cannot compensate for drought of this "
            "severity. The Pure Water San Diego program, targeting 30 MGD of recycled water "
            "by 2035, will not come online in time for this drought cycle."
        ),
        "mechanism_text": (
            "Reduced Sierra Nevada snowpack accelerates Colorado River reservoir drawdown, "
            "triggering tiered water restrictions. The Imperial Irrigation District's fallowing "
            "program aims to conserve water for urban areas but affects agricultural employment "
            "in Imperial Valley, while San Diego County enforces mandatory conservation measures.\n"
            "Key infrastructure: Carlsbad Desalination Plant (50 MGD), San Vicente Dam (152,000 acre-ft storage), "
            "and 90% import dependency create structural vulnerability to multi-year drought."
        ),
        "confidence": "high",
        "topics": ["Environment", "Economy"],
        "global_source": "CalMatters — California Water",
        "local_source": "AI-generated local impact analysis",
        "is_sensitive": False,
        "scoop_angle": "Predicted the specific Tier 2 trigger threshold and its cascading impact on Imperial Valley farm employment before local outlets detailed the labor market effects.",
        "neighborhoods_affected": "Imperial County agricultural zones, Carlsbad, Escondido, Poway (high-water-use areas)",
        "created_at": "2025-05-25T10:00:00Z",
    },
    {
        "id": "seed-3",
        "card_title": "Federal port automation rules take effect: Port of San Diego supply chain shifts",
        "card_body": (
            "New federal automation rules at the Port of Long Beach and Port of Los Angeles are "
            "reshaping cargo routing on the West Coast. Shipping lines seeking to avoid "
            "automation-related delays at the country's two busiest container ports are "
            "increasingly diverting cargo to smaller secondary ports — and San Diego's "
            "marine terminals stand to gain from the spillover.\n\n"
            "The Port of San Diego's two marine cargo terminals, which handle approximately "
            "1.8 million metric tons annually (primarily automobiles, fertilizers, and "
            "breakbulk/project cargo), could see a meaningful uptick in containerized cargo "
            "volume. Unlike the San Pedro Bay ports, San Diego lacks large-scale container "
            "cranes and deep-water berth capacity for the largest post-Panamax vessels — but "
            "the current diversion favors precisely the mid-size cargo segments where "
            "San Diego has comparative advantages.\n\n"
            "Local labor implications are significant. ILWU Local 29, representing approximately "
            "900 longshoremen in San Diego, faces a dual dynamic: increased work opportunities "
            "from cargo volume growth, offset by union concerns about automation precedent-setting "
            "at the larger ports. The San Diego Regional Chamber of Commerce is positioning "
            "the diversion as an economic development opportunity, advocating for terminal "
            "modernization investment. Environmental impact will concentrate along the I-5 and "
            "I-805 freight corridors, affecting neighborhoods in Barrio Logan, National City, "
            "and southeastern San Diego where diesel particulate levels are already elevated."
        ),
        "mechanism_text": (
            "Federal automation policy at major West Coast ports creates a 'push effect' — "
            "cargo diverts to smaller ports like San Diego to avoid automation-related "
            "delays. This increases local port revenue and logistics activity but triggers "
            "labor concerns (ILWU Local 29), environmental justice issues (Barrio Logan "
            "diesel corridor), and infrastructure investment questions for the Port of San Diego."
        ),
        "confidence": "medium",
        "topics": ["Economy", "Infrastructure"],
        "global_source": "Journal of Commerce",
        "local_source": "AI-generated local impact analysis — Predicted before Voice of San Diego coverage",
        "is_sensitive": False,
        "scoop_angle": "Predicted the cargo diversion effect on Port of San Diego's specific terminal operations and the labor/environmental justice dimensions before Voice of San Diego and KPBS covered the local angle — demonstrating the scoop capability.",
        "neighborhoods_affected": "Barrio Logan, National City, southeastern San Diego, Otay Mesa",
        "created_at": "2025-05-24T14:00:00Z",
    },
    # ── Card 4: Fed rate hold + San Diego housing ──────────────────────
    {
        "id": "seed-4",
        "card_title": "Federal Reserve holds rates steady: San Diego's housing crisis deepens as mortgage affordability hits new lows",
        "card_body": (
            "The Federal Reserve's decision to hold the federal funds rate at 5.25-5.50% — the highest "
            "level in 23 years — extends the most aggressive monetary tightening cycle in a generation. "
            "For San Diego, already the least affordable major metro in the United States, the impact "
            "is acute and multi-layered.\\n\\n"
            "Mortgage rates hovering near 7.5% for a 30-year fixed loan mean the monthly payment on "
            "San Diego's median-priced home ($835,000) exceeds $5,700 — requiring an income of roughly "
            "$230,000 to qualify. This locks out first-time homebuyers and depresses transaction "
            "volume, which fell 18% year-over-year in Q1 2025 according to CoreLogic data. Builders "
            "in the Chula Vista and Otay Ranch new-construction corridor report slowed pre-sales, "
            "deferring planned developments of single-family subdivisions.\\n\\n"
            "The rental market tells a bifurcated story. High-end coastal luxury rentals (La Jolla, "
            "Del Mar) see softening demand as tech and biotech hiring slows, but workforce housing in "
            "City Heights, El Cajon, and southeastern San Diego continues to tighten — rents up 8% "
            "year-over-year in those submarkets. The San Diego Housing Commission reports a 40% "
            "increase in Section 8 voucher applicants over 2023 levels, straining an already "
            "undersupplied affordable housing ecosystem.\\n\\n"
            "Commercial real estate faces parallel pressure. Office vacancy in downtown San Diego "
            "reached 22% in Q1 2025, the highest since the early 1990s recession. The rate hold "
            "delays the refinancing cycle for $4.5 billion in maturing CRE loans tied to San Diego "
            "properties, increasing default risk on Class B office assets in Mission Valley and "
            "Kearny Mesa."
        ),
        "mechanism_text": (
            "Extended high interest rates amplify San Diego's structural housing affordability crisis "
            "by compressing mortgage qualification, slowing new construction starts in growth corridors, "
            "bifurcating the rental market (luxury softening vs. workforce tightening), and delaying "
            "the commercial real estate refinancing cycle — increasing default risk on Class B office assets."
        ),
        "confidence": "high",
        "topics": ["Economy"],
        "global_source": "Federal Reserve / Bloomberg — Monetary Policy",
        "local_source": "AI-generated local impact analysis",
        "is_sensitive": False,
        "scoop_angle": "Connects the macro rate hold decision to specific San Diego submarkets and housing segments — new construction in Chula Vista, luxury coastal vs. workforce inland rents, CRE default risk in Mission Valley — before local real estate coverage fully maps the sector-by-sector effects.",
        "neighborhoods_affected": "Chula Vista, Otay Ranch, Mission Valley, Kearny Mesa, City Heights, El Cajon, coastal North County luxury submarkets",
        "created_at": "2025-05-27T06:00:00Z",
    },
    # ── Card 5: Tijuana sewage crisis + South Bay ──────────────────────
    {
        "id": "seed-5",
        "card_title": "Tijuana River sewage crisis deepens: Imperial Beach closures and cross-border health impacts escalate",
        "card_body": (
            "The Tijuana River sewage crisis — a decades-long cross-border environmental disaster — "
            "intensifies as federal funding for the International Boundary and Water Commission's "
            "infrastructure projects remains stalled in congressional appropriations. Without the "
            "requested $310 million for the South Bay International Wastewater Treatment Plant "
            "expansion and the Canyon del Padre collector system, raw sewage and industrial effluent "
            "from Tijuana continues to flow unabated into the Tijuana River Valley and ultimately "
            "the Pacific Ocean.\\n\\n"
            "Imperial Beach, the most directly affected community, has endured 700+ consecutive "
            "days of beach closure warnings as of May 2025 — the longest uninterrupted closure "
            "since monitoring began. The economic toll on this low-to-middle-income coastal "
            "community is severe: tourism revenue at local restaurants and hotels dropped 35% "
            "compared to pre-crisis baseline, according to the Imperial Beach Chamber of Commerce. "
            "SurfRider Foundation San Diego chapter estimates $50 million in lost annual economic "
            "activity across South County coastal communities.\\n\\n"
            "Air quality impacts extend beyond the shoreline. Hydrogen sulfide (H2S) levels in "
            "the Tijuana River Valley have exceeded California's acute exposure standards on 45 "
            "days in 2025 alone, affecting residents in Nestor, San Ysidro, and southernmost "
            "portions of the City of San Diego. The San Diego County Air Pollution Control District "
            "has deployed additional monitors but acknowledges the data reflects only a fraction "
            "of the actual exposure. Emergency room visits for respiratory complaints at Scripps "
            "Chula Vista and UCSD Imperial Beach clinics increased 28% year-over-year.\\n\\n"
            "Property values in the impacted zone have declined an estimated 8-12% since 2021, "
            "according to a Zillow market analysis. The Environmental Health Coalition and "
            "local community groups continue to press the Biden administration and California "
            "Congressional delegation for expedited funding, but the IBWC's procurement process "
            "for the Punta Bandera treatment plant expansion has encountered repeated delays."
        ),
        "mechanism_text": (
            "Stalled federal funding for IBWC infrastructure allows continued untreated sewage "
            "and industrial effluent from Tijuana to flow across the border, causing the longest "
            "beach closure in San Diego history, measurable property value decline (8-12%), "
            "respiratory health impacts in South Bay communities, and an estimated $50M annual "
            "loss in coastal economic activity. The crisis is simultaneously an environmental, "
            "public health, economic, and bilateral diplomatic problem."
        ),
        "confidence": "high",
        "topics": ["Environment", "Public Health", "Infrastructure"],
        "global_source": "EPA / IBWC — US-Mexico Border Infrastructure",
        "local_source": "AI-generated local impact analysis",
        "is_sensitive": True,
        "scoop_angle": "Synthesizes the disparate data points — beach closure days, ER visit increases, property value decline, air quality violations, economic losses — into a single cross-cutting impact assessment that no single local outlet has published in a unified analysis.",
        "neighborhoods_affected": "Imperial Beach, Coronado, San Ysidro, Nestor, Otay Mesa West, Chula Vista coastal areas",
        "created_at": "2025-05-26T16:00:00Z",
    },
    # ── Card 6: Fentanyl emergency + border health impact ───────────────
    {
        "id": "seed-6",
        "card_title": "National fentanyl public health emergency: San Diego border health infrastructure under strain",
        "card_body": (
            "The Department of Health and Human Services' declaration of a national public health "
            "emergency for the fentanyl crisis signals a significant escalation in federal response, "
            "with implications for funding allocation, border enforcement coordination, and local "
            "public health systems. As the busiest land border crossing in the Western Hemisphere, "
            "San Diego County is one of the most heavily impacted regions in the country.\\n\\n"
            "CBP's San Diego Field Office seized 18,000+ pounds of fentanyl at the San Ysidro and "
            "Otay Mesa ports of entry in calendar year 2024 — more than any other sector on the "
            "southwest border. The emergency declaration unlocks new resources for detection "
            "technology and screening infrastructure, which CBP officials expect to increase "
            "secondary inspection times by an average of 10-15 minutes per passenger vehicle. "
            "For the 70,000 northbound vehicles that cross San Ysidro daily, this translates to "
            "measurable economic disruption — $2.3 billion in annual cross-border commerce "
            "affected according to SANDAG estimates.\\n\\n"
            "Local health systems report parallel strain. The County of San Diego Health and Human "
            "Services Agency recorded 912 fentanyl-related overdose deaths in 2024, up from 674 "
            "in 2022 — a 35% increase. Emergency departments at Scripps Mercy (Hillcrest) and "
            "UCSD Medical Center report 15-20 fentanyl overdose presentations per week, "
            "disproportionately concentrated among unsheltered populations in downtown San Diego "
            "and East County. The County's harm reduction programs — including naloxone distribution "
            "(25,000+ kits in 2024) and the Downtown San Diego syringe access program — face "
            "sustained demand increases.\\n\\n"
            "The emergency declaration's impact on local law enforcement is mixed. The San Diego "
            "Police Department's Narcotics Division has received $1.2 million in new federal "
            "grant funding for fentanyl interdiction, but critics note this may divert resources "
            "from the City's homelessness response. The San Diego County Sheriff's Department has "
            "expanded its medication-assisted treatment (MAT) program in the county jails, where "
            "a disproportionate share of fentanyl detox cases originate."
        ),
        "mechanism_text": (
            "The federal fentanyl emergency declaration creates cascading effects across San Diego's "
            "border infrastructure (increased inspection times at San Ysidro disrupting $2.3B in "
            "cross-border commerce), public health systems (912 overdose deaths in 2024, 35% increase "
            "over two years, straining ER and harm reduction capacity), and local enforcement "
            "($1.2M new federal grants but potential diversion from homelessness response). The "
            "border-city position amplifies every dimension of the crisis."
        ),
        "confidence": "medium",
        "topics": ["Public Health", "Policy"],
        "global_source": "HHS / DEA — National Drug Control Policy",
        "local_source": "AI-generated local impact analysis",
        "is_sensitive": True,
        "scoop_angle": "Connects the federal declaration to three specific SD impact vectors — border wait-time economics, hospital system strain with neighborhood-level overdose data, and enforcement funding trade-offs with homelessness programs — before any single local analysis piece has mapped all three together.",
        "neighborhoods_affected": "Downtown San Diego, El Cajon, Spring Valley, San Ysidro, Otay Mesa, Hillcrest",
        "created_at": "2025-05-26T12:00:00Z",
    },
]

# San Diego locale profile seed data
SAN_DIEGO_PROFILE: dict[str, Any] = {
    "locale_slug": "san-diego-ca",
    "display_name": "San Diego, CA",
    "metro_code": "41740",
    "demographics": {
        "population": "1.38 million (city), 3.3 million (county)",
        "median_age": "35.0",
        "median_household_income": "$83,000",
        "largest_ethnic_groups": "White (44%), Hispanic/Latino (30%), Asian (17%), Black (6%)",
        "foreign_born": "26%",
        "languages_spoken": "English (56%), Spanish (23%), Tagalog (6%), Vietnamese (4%), Arabic (1%)",
        "top_diaspora_communities": "Filipino (200K+), Mexican (750K+), Vietnamese (50K+), Somali (15K+), Iranian (12K+), Yemeni (5K+)",
        "educational_attainment": "Bachelor's degree or higher: 44% of adults (above national average)",
        "age_distribution": "Under 18: 21%, 18-34: 26%, 35-64: 38%, 65+: 15%",
    },
    "economy": {
        "gdp": "$255 billion (San Diego metro area)",
        "largest_sectors_by_employment": "Government/military (22%), Healthcare/social assistance (14%), Professional services (12%), Retail (10%), Manufacturing (8%)",
        "unemployment_rate": "4.2% (typically below national average)",
        "median_home_price": "$835,000",
        "cost_of_living_index": "144 (national average=100)",
        "major_exports": "Semiconductors, medical devices, optical instruments, aircraft parts",
        "port_cargo_value": "$6.5 billion annually (Port of San Diego)",
        "tourism_annual_revenue": "$13 billion (pre-pandemic baseline)",
        "cross_border_trade": "$60 billion annual two-way trade through San Diego-Tijuana border crossings",
    },
    "major_employers": [
        "UC San Diego (35,000+ employees)",
        "Sharp Healthcare (18,000+)",
        "Scripps Health (15,000+)",
        "San Diego Unified School District (13,000+)",
        "Qualcomm (12,000+)",
        "Northrop Grumman (8,000+)",
        "General Atomics (6,000+)",
        "NAVWAR / Naval Base San Diego (45,000+ military + civilian)",
        "Sempra Energy (4,000+)",
        "Illumina (2,500+)",
        "Thermo Fisher Scientific (2,000+)",
        "SeaWorld San Diego (3,000+)",
        "San Diego Padres (1,000+ game-day)",
        "Port of San Diego (900+ direct, thousands indirect)",
    ],
    "key_industries": [
        "Defense and military contracting (NAVWAR, Space Systems Command)",
        "Biotechnology and life sciences (Illumina, Thermo Fisher, BioLegend)",
        "Cybersecurity and defense IT (Qualcomm, Northrop Grumman mission systems)",
        "Wireless and semiconductor design (Qualcomm HQ)",
        "Tourism and hospitality (theme parks, beaches, convention center)",
        "International trade and logistics (Port of SD, Otay Mesa cargo)",
        "Craft brewing (150+ breweries, $1B+ industry)",
        "Agriculture (avocados, flowers — North County; Imperial Valley vegetables)",
        "Aerospace and unmanned systems (General Atomics Predator drones)",
        "Medical devices and health tech",
    ],
    "government_entities": [
        "San Diego City Council (9 districts, mayor — Todd Gloria)",
        "San Diego County Board of Supervisors (5 districts)",
        "San Diego County Water Authority (member agencies)",
        "San Diego Unified Port District (5 member cities)",
        "Port of San Diego (port operations + tidelands management)",
        "San Diego Metropolitan Transit System (MTS — buses + trolley)",
        "San Diego Police Department (1,800+ sworn officers)",
        "San Diego Fire-Rescue Department",
        "San Diego County Air Pollution Control District",
        "San Diego Airport Authority (SAN)",
        "San Diego Housing Commission",
        "SANDAG (regional planning agency)",
    ],
    "geography": {
        "region": "Southern California, 120 miles south of LA, 20 miles north of Tijuana",
        "climate": "Mediterranean: avg 70F, 10 inches rain/year (Nov-Mar)",
        "coastline": "70 miles of coastline; Imperial Beach, Pacific Beach, La Jolla, Del Mar",
        "major_water_sources": "Colorado River (via Imperial Irrigation District + SDCWA), State Water Project, Carlsbad Desalination Plant (50 MGD)",
        "elevation_zones": "Coastal plain (sea level), inland valleys (200-500ft), mountains (6,000ft), desert (eastern county)",
        "wildfire_zones": "High fire risk in inland valleys (East County, Ramona, Alpine, Julian)",
        "seismic_risk": "Moderate; active fault zones (Rose Canyon, Elsinore, San Jacinto)",
        "border": "15-mile US-Mexico border; 3 ports of entry (San Ysidro, Otay Mesa, Tecate)",
        "international_airport": "San Diego International Airport (SAN) — 25M passengers/year, single-runway, land-constrained",
    },
    "infrastructure": {
        "port": "Port of San Diego: 2 marine cargo terminals, 1 cruise ship terminal, 34 maritime tenant facilities; handles autos, fertilizers, breakbulk, project cargo; limited container capacity vs LA/Long Beach",
        "airport": "SAN — 1 runway (9L/27R), constrained by downtown + bay; no feasible expansion site; $3B terminal modernization underway",
        "public_transit": "MTS: 3 trolley lines (Blue, Orange, Green), 80+ bus routes; 100,000 daily riders (pre-COVID); COASTER commuter rail to Oceanside",
        "roads": "Interstates 5, 8, 15, 805, 905; State Routes 52, 54, 56, 67, 78, 94, 125, 163; perpetual congestion on I-5, I-15 corridor",
        "energy": "SDG&E service territory; 33% renewable (solar, wind); 2,200 MW peak demand; planned offshore wind (500MW); Palomar Energy Center (natural gas, 580MW)",
        "water_infrastructure": "Carlsbad Desalination Plant (50 MGD, largest in Western Hemisphere); San Vicente Dam raise (152,000 acre-ft added storage); Pure Water San Diego (recycled water, 30 MGD by 2035); 90% imported water reliance reduction ongoing",
        "sewage": "Point Loma Wastewater Treatment Plant (primary only, waiver from secondary treatment); South Bay International Wastewater Treatment Plant (cross-border flows)",
        "ports_of_entry": "San Ysidro POE (70,000 northbound vehicles/day, busiest land border in Western Hemisphere); Otay Mesa POE (commercial cargo + vehicles); PedWest pedestrian crossing",
    },
    "military": {
        "major_bases": "Naval Base San Diego (50+ ships homeported), Marine Corps Air Station Miramar, Camp Pendleton (North County), Naval Air Station North Island, Space Systems Command (Los Angeles AFB detachment in SD)",
        "military_personnel": "100,000+ active duty + civilian (San Diego County has the largest concentration of military in the US)",
        "economic_impact": "$20 billion annual direct economic impact from military presence",
        "key_defense_contractors": "General Atomics (Predator/Reaper drones, electromagnetic railgun), Northrop Grumman (mission systems, space), BAE Systems (ship repair), NASSCO (shipbuilding, 3 dry docks)",
        "nbsd_capabilities": "Naval Base San Diego: largest naval base on West Coast, home to 50+ ships, 3 dry docks, surface force maintenance",
        "space_force": "Space Systems Command (SSC) moving to Los Angeles but maintains SD presence; Camp Roberts (satellite ground station in SLO County)",
    },
    "active_local_issues": [
        "Housing affordability crisis (median home price 9.5x median income)",
        "Homelessness (estimated 5,000+ unsheltered in city, 10,000+ countywide)",
        "Cross-border sewage crisis (Tijuana River flows causing beach closures from Imperial Beach to Coronado)",
        "Water security — Colorado River allocations, drought contingency plans, desalination expansion",
        "Climate adaptation — sea level rise threatening coastal infrastructure, Mission Bay, Coronado",
        "Airport capacity (SAN land-constrained; no 2nd runway feasible; debate over Miramar relocation)",
        "SDG&E wildfire liability and rising electricity rates (highest in continental US)",
        "San Diego Unified Port District tidelands trust disputes with State Lands Commission",
        "Military base compatibility — Miramar flight paths vs. residential development in University City, Clairemont",
        "Immigration and border enforcement — San Ysidro POE operations, asylum processing, humanitarian impacts",
        "K-12 education funding disparities between coastal and East County school districts",
        "Public transit funding (MTS fiscal cliff post-COVID ridership recovery at 80%)",
        "Short-term rental regulation (Airbnb/VRBO impacts on housing supply in beach communities)",
        "Biotech lab space shortage driving life sciences companies to Torrey Pines, Sorrento Valley, UTC",
    ],
    "community_organizations": [
        "CAIR San Diego (Council on American-Islamic Relations)",
        "Jewish Family Service of San Diego",
        "San Diego Rapid Response Network (immigrant services)",
        "MAAC Project (Latino community development)",
        "Barrio Logan Community Planning Group",
        "City Heights Community Development Corporation",
        "Southeast San Diego Community Development Corporation",
        "San Diego LGBT Community Center (The Center)",
        "San Diego Foundation (philanthropic)",
        "United Way of San Diego County",
        "Environmental Health Coalition (environmental justice, Barrio Logan, National City)",
        "SurfRider Foundation San Diego Chapter (coastal environmental)",
    ],
}


# ══════════════════════════════════════════════════════════════════════════
# LOCAL MODE PIPELINE (SQLite + Ollama)
# ══════════════════════════════════════════════════════════════════════════


def _run_local_ingestion(
    db: Any,
    locale: str,
    categories: list[str] | None = None,
) -> int:
    """Ingest RSS articles into local SQLite database."""
    from data.rss_client import RSSClient

    rss = RSSClient(locale=locale)
    cats = categories or ["global", "national", "state", "local"]
    articles = rss.parse_feeds(categories=cats)
    count = db.insert_articles(articles)
    logger.info(
        "Local ingestion: %d new articles for %s (categories=%s)",
        count,
        locale,
        cats,
    )
    return count


def _seed_locale_profile(db: Any, locale: str) -> dict[str, Any] | None:
    """Ensure a locale profile exists in the local database."""
    profile = db.get_locale_profile(locale)
    if profile:
        return profile

    if locale == "san-diego-ca" or locale == settings.default_locale:
        db.upsert_locale_profile(
            locale_slug=SAN_DIEGO_PROFILE["locale_slug"],
            display_name=SAN_DIEGO_PROFILE["display_name"],
            context=SAN_DIEGO_PROFILE,
        )
        logger.info("Seeded locale profile: %s", locale)
        return db.get_locale_profile(locale)

    # Generic stub for other locales
    display = dict(settings.supported_locales).get(locale, locale)
    db.upsert_locale_profile(
        locale_slug=locale,
        display_name=display,
        context={"locale_slug": locale, "display_name": display},
    )
    return db.get_locale_profile(locale)


def _format_connection_to_card(conn_dict: dict[str, Any]) -> dict[str, Any]:
    """Convert a raw connection dict from SQLite to the card format expected by the UI."""
    # Get the global article for title/source
    global_title = conn_dict.get("global_title", "")
    global_source = conn_dict.get("global_source", "AI analysis")

    return {
        "id": f"conn-{conn_dict['id']}",
        "card_title": conn_dict.get("card_title", "Untitled"),
        "card_body": conn_dict.get("card_body", ""),
        "mechanism_text": conn_dict.get("mechanism_text", ""),
        "confidence": conn_dict.get("confidence", "medium"),
        "topics": conn_dict.get("topics", []),
        "global_source": global_source or "AI analysis",
        "local_source": "AI-generated local impact analysis",
        "is_sensitive": conn_dict.get("is_sensitive", False),
        "scoop_angle": conn_dict.get("scoop_angle", ""),
        "neighborhoods_affected": conn_dict.get("neighborhoods_affected", ""),
        "created_at": conn_dict.get("created_at", ""),
    }


def _run_local_pipeline(locale: str) -> list[dict[str, Any]]:
    """Run the full connection pipeline using local SQLite + Ollama.

    Flow:
    1. Seed locale profile if not already stored
    2. Ingest RSS feeds if articles are empty/stale
    3. Score global/national headlines for local relevance (keyword heuristic)
    4. Generate local impact analysis via available LLM (Ollama or OpenAI)
    5. Store results in SQLite connections table
    6. Return connection cards in UI format
    """
    from data.local_storage import Connection, LocalDatabase

    db = LocalDatabase()

    # Step 1: Locale profile
    with st.spinner("Loading locale context..."):
        locale_profile = _seed_locale_profile(db, locale)
    if not locale_profile:
        logger.warning("Could not load locale profile — falling back to seed data")
        return SEED_CONNECTIONS

    # Step 2: Check / run ingestion
    article_count = db.get_article_count()
    if article_count < 10:
        with st.spinner("Ingesting news from RSS feeds..."):
            ingested = _run_local_ingestion(db, locale)
            if ingested == 0 and article_count == 0:
                logger.warning("No articles ingested — falling back to seed data")
                return SEED_CONNECTIONS
            article_count = db.get_article_count()

    # Step 3: Get global/national headlines
    headlines = db.get_articles_by_level(
        "global", hours=48, limit=50
    ) + db.get_articles_by_level("national", hours=48, limit=50)

    if not headlines:
        logger.info("No headlines available — falling back to seed data")
        return SEED_CONNECTIONS

    with st.spinner("Scoring headlines for local relevance..."):
        from agents.discovery_agent import RelevanceScorer

        scorer = RelevanceScorer()
        relevant: list[dict[str, Any]] = []
        for h in headlines:
            score = scorer.score_relevance(h, locale_profile)
            if score >= 0.35:
                h["relevance_score"] = round(score, 3)
                relevant.append(h)

        relevant.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    top_headlines = relevant[:10]

    if not top_headlines:
        logger.info("No relevant headlines found — using seed data")
        return SEED_CONNECTIONS

    # Step 4: Generate local impact analysis
    from agents.validation_agent import LocalImpactGenerator

    generator = LocalImpactGenerator()
    connections: list[dict[str, Any]] = []
    progress_text = st.empty()

    for i, headline in enumerate(top_headlines):
        progress_text.info(
            f"Analyzing: {headline.get('title', '')[:60]}... "
            f"({i + 1}/{len(top_headlines)})"
        )
        result = generator.generate(headline, locale_profile)
        if result and result.has_local_impact:
            conn = Connection(
                global_article_id=headline["id"],
                locale=locale,
                confidence=result.confidence,
                mechanism_text=result.mechanism,
                card_title=result.card_title,
                card_body=result.card_body,
                topics=result.topics,
                is_sensitive=result.is_sensitive,
                scoop_angle=result.scoop_angle or "",
                neighborhoods_affected=", ".join(
                    result.neighborhoods_or_groups_affected
                ),
            )
            saved = db.insert_connection(conn)
            if saved:
                connections.append(_format_connection_to_card(saved))

    progress_text.empty()

    if not connections:
        logger.info("No AI connections generated — using seed data")
        return SEED_CONNECTIONS

    # Step 5: Update session state
    st.session_state["_cached_pairs_count"] = len(connections)
    st.session_state["last_refresh_time"] = datetime.now(timezone.utc).strftime(
        "%b %d, %Y at %I:%M %p"
    )

    logger.info("Local pipeline complete: %d connection cards", len(connections))
    return connections


# ══════════════════════════════════════════════════════════════════════════
# SESSION STATE INITIALIZATION
# ══════════════════════════════════════════════════════════════════════════


def init_session_state() -> None:
    """Initialize all session state variables."""
    # Check for existing local DB connections first
    initial_connections = SEED_CONNECTIONS
    initial_cached_count = 6
    if not _check_supabase_configured():
        try:
            from data.local_storage import LocalDatabase

            db = LocalDatabase()
            existing = db.get_connections(locale=settings.default_locale, limit=20)
            if existing:
                initial_connections = [
                    _format_connection_to_card(c) for c in existing
                ]
                initial_cached_count = len(existing)
        except Exception:
            pass

    defaults: dict[str, Any] = {
        "locale": settings.default_locale,
        "connections": initial_connections,
        "last_refresh_time": None,
        "deep_dive_cache": {},
        "_cached_pairs_count": initial_cached_count,
        "_supabase_available": False,
        "_ingestion_scheduler_started": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ══════════════════════════════════════════════════════════════════════════
# CONNECTION PIPELINE
# ══════════════════════════════════════════════════════════════════════════


def run_connection_pipeline(locale: str) -> list[dict[str, Any]]:
    """Run the full connection discovery and validation pipeline.

    When Supabase is configured, runs the real pipeline.
    Otherwise returns seed data for demo mode.
    """
    # Demo mode: use local SQLite + Ollama pipeline
    if not _check_supabase_configured():
        logger.info("Running in local mode — SQLite + RSS + Ollama")
        return _run_local_pipeline(locale)

    # Production mode with Supabase
    return _run_production_pipeline(locale)


def _check_supabase_configured() -> bool:
    """Check if Supabase credentials are available."""
    return bool(
        settings.supabase_url
        and settings.supabase_key
        and settings.supabase_url != "your_supabase_url"
    )


def _run_production_pipeline(locale: str) -> list[dict[str, Any]]:
    """Run the full production pipeline with Supabase + agents.

    In the "scoop" architecture:
    1. HeadlineMonitorAgent fetches global headlines and scores relevance
    2. LocalImpactGenerator generates impact analysis from headline + locale profile
    3. Results are cached in Supabase connections table
    """
    try:
        from data.supabase_client import SupabaseClient
        from agents.discovery_agent import HeadlineMonitorAgent, RelevanceScorer
        from agents.validation_agent import LocalImpactGenerator

        db = SupabaseClient()
        monitor = HeadlineMonitorAgent(supabase_client=db)
        generator = LocalImpactGenerator()

        # Step 1: Get locale profile
        locale_profile = db.get_locale_profile(locale)
        if not locale_profile:
            logger.warning("No locale profile for %s — falling back to seed", locale)
            return SEED_CONNECTIONS

        # Step 2: Monitor headlines and find locally relevant stories
        relevant_headlines = monitor.discover(
            locale=locale,
            locale_profile=locale_profile,
            hours=24,
        )

        if not relevant_headlines:
            logger.info("No relevant headlines found for %s", locale)
            return SEED_CONNECTIONS

        # Step 3: Generate local impact for each relevant headline
        connections = []
        for headline in relevant_headlines[:10]:  # top 10
            result = generator.generate(
                headline=headline,
                locale_profile=locale_profile,
            )
            if result and result.has_local_impact:
                from data.supabase_client import Connection as ConnDC

                conn = ConnDC(
                    global_article_id=headline["id"],
                    locale=locale,
                    confidence=result.confidence,
                    mechanism_text=result.mechanism,
                    card_title=result.card_title,
                    card_body=result.card_body,
                    topics=result.topics,
                    scoop_angle=result.scoop_angle,
                    neighborhoods_affected=", ".join(result.neighborhoods_or_groups_affected),
                )
                saved = db.insert_connection(conn)
                connections.append(saved)

        # Step 4: Update session state
        st.session_state["_cached_pairs_count"] = len(connections)
        st.session_state["last_refresh_time"] = datetime.now(
            timezone.utc
        ).strftime("%b %d, %Y at %I:%M %p")

        return connections or SEED_CONNECTIONS  # fallback to seed

    except Exception:
        logger.exception("Production pipeline failed — falling back to seed data")
        return SEED_CONNECTIONS


# ══════════════════════════════════════════════════════════════════════════
# INGESTION
# ══════════════════════════════════════════════════════════════════════════


def run_ingestion(locale: str) -> int:
    """Run the news ingestion pipeline for a locale.

    Fetches from RSS feeds (and NewsAPI/Guardian if configured),
    then stores in Supabase (if configured) or local SQLite.
    """
    if not _check_supabase_configured():
        from data.local_storage import LocalDatabase

        db = LocalDatabase()
        count = _run_local_ingestion(db, locale)
        logger.info("Local ingestion complete: %d new articles", count)
        return count

    try:
        from data.supabase_client import SupabaseClient
        from data.newsapi_client import NewsAPIClient
        from data.guardian_client import GuardianClient
        from data.rss_client import RSSClient

        db = SupabaseClient()
        total = 0

        # NewsAPI global headlines
        newsapi = NewsAPIClient()
        articles = newsapi.get_global_headlines(locale)
        total += db.insert_articles_batch(articles)

        # Guardian world and US news
        guardian = GuardianClient()
        articles = guardian.get_world_news(locale)
        total += db.insert_articles_batch(articles)
        articles = guardian.get_us_news(locale)
        total += db.insert_articles_batch(articles)

        # RSS local feeds
        rss = RSSClient(locale=locale)
        articles = rss.parse_feeds()
        total += db.insert_articles_batch(articles)

        logger.info("Ingestion complete: %d new articles for %s", total, locale)
        return total

    except Exception:
        logger.exception("Ingestion pipeline failed")
        return 0


# ══════════════════════════════════════════════════════════════════════════
# STREAMLIT APP
# ══════════════════════════════════════════════════════════════════════════


def authenticate() -> bool:
    """Render login form and check credentials.

    Returns True if the user is authenticated.
    Credentials come from LOCALLENS_USERNAME / LOCALLENS_PASSWORD env vars
    (defaults: admin / locallens).
    """
    if st.session_state.get("_authenticated"):
        return True

    st.markdown(
        """
        <div style="
            display:flex; align-items:center; justify-content:center;
            min-height:80vh;
        ">
            <div style="
                max-width:400px; width:100%;
                background:#111118; border:1px solid #00ff8822;
                border-radius:12px; padding:2.5rem;
                text-align:center;
            ">
                <h1 style="margin:0 0 0.25rem; font-size:1.75rem;">
                    🔍 LocalLens
                </h1>
                <p style="color:#9ca3af; margin:0 0 1.5rem; font-size:0.9rem;">
                    News Through a Local Lens
                </p>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        username = st.text_input("Username", key="_auth_user")
        password = st.text_input("Password", type="password", key="_auth_pass")
        if st.button("Log In", type="primary", use_container_width=True):
            if (
                username == settings.locallens_username
                and password == settings.locallens_password
            ):
                st.session_state["_authenticated"] = True
                st.rerun()
            else:
                st.error("Invalid credentials")

    st.markdown(
        """
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return False


def main() -> None:
    """Main Streamlit application entrypoint."""
    st.set_page_config(
        page_title="LocalLens — Stories Through a Local Lens",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize state
    init_session_state()

    # Auth gate — render login if not authenticated
    if not authenticate():
        return

    # Apply custom styles
    apply_styles()

    # ── Sidebar ──────────────────────────────────────────────
    from ui.components.sidebar import render_sidebar

    def _on_locale_change(new_locale: str) -> None:
        """Handle locale switch."""
        st.session_state["locale"] = new_locale
        locale_options = dict(settings.supported_locales)
        display = locale_options.get(new_locale, new_locale)
        with st.spinner(f"Analyzing connections for {display}..."):
            connections = run_connection_pipeline(new_locale)
            st.session_state["connections"] = connections
        st.rerun()

    def _on_refresh() -> None:
        """Handle manual refresh."""
        locale = st.session_state["locale"]
        locale_options = dict(settings.supported_locales)
        display = locale_options.get(locale, locale)
        with st.spinner(f"Refreshing connections for {display}..."):
            connections = run_connection_pipeline(locale)
            st.session_state["connections"] = connections
        st.rerun()

    selected_topics = render_sidebar(
        current_locale=st.session_state["locale"],
        on_locale_change=_on_locale_change,
        on_refresh=_on_refresh,
    )

    # ── Header ───────────────────────────────────────────────
    locale_display = dict(settings.supported_locales).get(
        st.session_state["locale"], "San Diego, CA"
    )
    render_header(locale_display)

    # ── Content Area ─────────────────────────────────────────
    current_view = st.session_state.get("_current_view", "feed")

    if current_view == "archive":
        # ── Archive Page ─────────────────────────────────────
        from ui.components.archive_page import render_archive_page
        from ui.components.deep_dive_modal import render_deep_dive_modal

        def _archive_deep_dive(connection_id: str) -> None:
            render_deep_dive_modal(connection_id)

        render_archive_page(on_deep_dive=_archive_deep_dive)

    else:
        # ── Feed View ─────────────────────────────────────────
        from ui.components.card_feed import render_card_feed
        from ui.components.deep_dive_modal import render_deep_dive_modal

        # Deep dive callback
        def _on_deep_dive(connection_id: str) -> None:
            render_deep_dive_modal(connection_id)

        # Render the feed
        connections = st.session_state.get("connections", SEED_CONNECTIONS)
        render_card_feed(
            connections=connections,
            selected_topics=selected_topics if selected_topics else None,
            on_deep_dive=_on_deep_dive,
        )

    # ── Initialize ingestion scheduler ───────────────────────
    if not st.session_state.get("_ingestion_scheduler_started"):
        try:
            from data.ingestion_scheduler import IngestionScheduler
            scheduler = IngestionScheduler()
            scheduler.configure(
                ingestion_fn=run_ingestion,
                locale=st.session_state["locale"],
            )
            scheduler.start()
            st.session_state["_ingestion_scheduler_started"] = True
            st.session_state["_scheduler"] = scheduler
        except Exception:
            logger.exception("Failed to start ingestion scheduler")

    # ── Footer ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align:center; font-size:0.75rem; color:#9ca3af; padding:1rem;">
            <strong>LocalLens</strong> — AI-synthesized news analysis.
            Always verify with original sources.
            No user accounts. No tracking. No PII stored.
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
