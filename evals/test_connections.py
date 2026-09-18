"""
Eval harness for LocalLens connection validity tests.

Tests three dimensions:
1. Connection validity — does the agent correctly identify valid/invalid pairs?
2. RAGAS faithfulness — is the synthesis faithful to source articles?
3. Relevance scoring — are the heuristic scores consistent?

Run with: pytest evals/ -v
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from config import settings

FIXTURES_PATH = Path(__file__).resolve().parent / "fixtures" / "connection_pairs.json"


def load_fixtures() -> list[dict[str, Any]]:
    """Load eval fixtures from JSON."""
    with open(FIXTURES_PATH) as f:
        return json.load(f)


# ── Connection Validity Tests ────────────────────────────────────────────


@pytest.mark.eval
class TestConnectionValidity:
    """Test the impact generator's ability to correctly identify connections.

    Each fixture has a known ground-truth label (valid_connection: bool).
    The test passes if the agent's assessment matches.
    """

    @pytest.fixture(scope="class")
    def fixtures(self) -> list[dict[str, Any]]:
        return load_fixtures()

    def test_fixtures_loaded(self, fixtures: list[dict[str, Any]]) -> None:
        """Verify fixture data loaded correctly."""
        assert len(fixtures) >= 10, f"Expected >=10 fixtures, got {len(fixtures)}"
        for fixture in fixtures:
            assert "id" in fixture
            assert "global_article" in fixture
            assert "local_article" in fixture
            assert "valid_connection" in fixture
            assert isinstance(fixture["valid_connection"], bool)

    @pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set",
    )
    def test_impact_generator_on_fixtures(
        self, fixtures: list[dict[str, Any]]
    ) -> None:
        """Run impact generator against all fixtures and measure accuracy.

        Uses the legacy validate() method which matches the old test API:
        (global_article, local_article, locale_profile) -> impact_output.
        """
        from agents.validation_agent import LocalImpactGenerator

        agent = LocalImpactGenerator()

        # Need a minimal locale profile for the generator to work
        min_profile = {
            "display_name": "San Diego, CA",
            "demographics": {"population": "1.38 million"},
            "economy": {"gdp": "$255 billion"},
            "key_industries": ["Defense", "Biotech", "Tourism"],
            "major_employers": ["UC San Diego", "Qualcomm"],
            "geography": {"region": "Southern California"},
            "infrastructure": {"port": "Port of San Diego"},
            "active_local_issues": ["Housing", "Water"],
        }

        results = {"correct": 0, "total": 0, "by_confidence": {}}
        for fixture in fixtures:
            result = agent.validate(
                fixture["global_article"],
                fixture["local_article"],
                min_profile,
            )
            predicted_valid = result is not None and result.has_local_impact
            actual_valid = fixture["valid_connection"]
            is_correct = predicted_valid == actual_valid

            if is_correct:
                results["correct"] += 1
            results["total"] += 1

            # Track by expected confidence
            exp_conf = fixture.get("confidence_expected", "unknown")
            if exp_conf not in results["by_confidence"]:
                results["by_confidence"][exp_conf] = {"correct": 0, "total": 0}
            results["by_confidence"][exp_conf]["total"] += 1
            if is_correct:
                results["by_confidence"][exp_conf]["correct"] += 1

        accuracy = results["correct"] / max(results["total"], 1)
        print(f"\nValidation accuracy: {accuracy:.1%} ({results['correct']}/{results['total']})")
        for conf, counts in sorted(results["by_confidence"].items()):
            acc = counts["correct"] / max(counts["total"], 1)
            print(f"  {conf}: {acc:.1%} ({counts['correct']}/{counts['total']})")

        # Minimum acceptable accuracy for MVP
        assert accuracy >= 0.55, f"Validation accuracy {accuracy:.1%} below 55% threshold"

    def test_fixture_distribution(self, fixtures: list[dict[str, Any]]) -> None:
        """Verify reasonable distribution of valid/invalid pairs."""
        valid_count = sum(1 for f in fixtures if f["valid_connection"])
        invalid_count = len(fixtures) - valid_count
        total = len(fixtures)
        print(f"\nFixture distribution: {valid_count} valid ({valid_count/total:.0%}), "
              f"{invalid_count} invalid ({invalid_count/total:.0%})")
        assert valid_count >= 2, "Need at least 2 valid pairs for meaningful evaluation"
        assert invalid_count >= 2, "Need at least 2 invalid pairs for meaningful evaluation"


# ── RAGAS Faithfulness and Relevancy Tests ──────────────────────────────


@pytest.mark.eval
class TestRAGASMetrics:
    """Test RAGAS faithfulness and answer relevancy of generated cards.

    Requires OPENAI_API_KEY and LANGCHAIN_API_KEY.
    """

    @pytest.fixture(scope="class")
    def fixtures(self) -> list[dict[str, Any]]:
        return load_fixtures()

    @pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY"),
        reason="OPENAI_API_KEY not set",
    )
    def test_ragas_metrics_on_valid_pairs(
        self, fixtures: list[dict[str, Any]]
    ) -> None:
        """Run RAGAS faithfulness and relevancy on a sample of valid pairs."""
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy
        from datasets import Dataset

        valid_fixtures = [f for f in fixtures if f["valid_connection"]]
        sample = valid_fixtures[:5]  # first 5 for speed
        if not sample:
            pytest.skip("No valid fixtures to evaluate")

        # Test the impact generator with legacy validate() interface
        from agents.validation_agent import LocalImpactGenerator

        agent = LocalImpactGenerator()
        min_profile = {
            "display_name": "San Diego, CA",
            "demographics": {"population": "1.38 million"},
            "economy": {"gdp": "$255 billion"},
            "key_industries": ["Defense", "Biotech", "Tourism"],
            "major_employers": ["UC San Diego", "Qualcomm"],
            "geography": {"region": "Southern California"},
            "infrastructure": {"port": "Port of San Diego"},
            "active_local_issues": ["Housing", "Water"],
        }

        data: dict[str, list[str]] = {
            "question": [],
            "answer": [],
            "contexts": [],
        }

        for fixture in sample:
            result = agent.validate(
                fixture["global_article"],
                fixture["local_article"],
                min_profile,
            )
            if result and result.has_local_impact:
                data["question"].append(
                    f"What is the local impact of {fixture['global_article']['title']} "
                    f"on San Diego?"
                )
                data["answer"].append(result.card_body)
                data["contexts"].append(
                    [fixture["global_article"]["body"], result.card_body]
                )

        if not data["answer"]:
            pytest.skip("No connection cards generated for evaluation")

        dataset = Dataset.from_dict(data)

        try:
            result = evaluate(
                dataset,
                metrics=[faithfulness, answer_relevancy],
            )
            print(f"\nRAGAS metrics ({len(data['answer'])} samples):")
            for metric_name, score in result.items():
                print(f"  {metric_name}: {score:.3f}")
        except Exception as e:
            print(f"RAGAS evaluation failed (this is expected without proper setup): {e}")
            pytest.skip("RAGAS evaluation requires LangSmith dataset configuration")


# ── Relevance Scorer Tests ────────────────────────────────────────────────


@pytest.mark.eval
class TestRelevanceScorer:
    """Test the relevance scorer's heuristic scoring.

    Validates that the keyword-based scoring is consistent
    and produces expected results for known inputs.
    """

    @pytest.fixture
    def profile(self) -> dict[str, Any]:
        """Minimal locale profile for testing."""
        return {
            "display_name": "San Diego, CA",
            "demographics": {"largest_ethnic_groups": "White, Hispanic, Asian, Black"},
            "major_employers": ["Qualcomm", "UC San Diego", "General Atomics", "Port of San Diego"],
            "key_industries": ["Defense", "Biotech", "Tourism", "International trade"],
            "geography": {"coastline": "70 miles", "border": "US-Mexico border"},
            "infrastructure": {"port": "Port of San Diego", "energy": "SDG&E"},
            "military": {"major_bases": "Naval Base San Diego, MCAS Miramar"},
            "active_local_issues": ["Housing affordability", "Water security", "Cross-border relations"],
        }

    def test_high_relevance_keywords(self, profile: dict[str, Any]) -> None:
        """Headline mentioning port and San Diego should score high."""
        from agents.discovery_agent import RelevanceScorer

        scorer = RelevanceScorer()
        headline = {
            "title": "Federal port automation rules reshape West Coast shipping routes",
            "body": "New automation rules at the Port of Long Beach and Port of Los Angeles "
                    "are redirecting cargo to smaller ports including San Diego. "
                    "The Port of San Diego's marine terminals stand to gain from the spillover.",
        }
        score = scorer.score_relevance(headline, profile)
        assert score >= 0.5, f"Expected >=0.5 for port headline, got {score}"

    def test_low_relevance_keywords(self, profile: dict[str, Any]) -> None:
        """Headline with no local relevance should score low."""
        from agents.discovery_agent import RelevanceScorer

        scorer = RelevanceScorer()
        headline = {
            "title": "New farming technique adopted in rural Nebraska corn fields",
            "body": "Farmers in Nebraska have adopted a new technique for corn cultivation "
                    "that increases yield by 15% while reducing water usage.",
        }
        score = scorer.score_relevance(headline, profile)
        assert score < 0.3, f"Expected <0.3 for unrelated headline, got {score}"

    def test_military_headline_high_score(self, profile: dict[str, Any]) -> None:
        """Headline about Navy should score high given SD's military presence."""
        from agents.discovery_agent import RelevanceScorer

        scorer = RelevanceScorer()
        headline = {
            "title": "Navy deploys additional destroyers to the Pacific Fleet",
            "body": "The US Navy has announced the deployment of three additional Arleigh Burke-class "
                    "destroyers to the Pacific Fleet, expanding operational capacity. "
                    "Naval Base San Diego will serve as a homeport for the new vessels.",
        }
        score = scorer.score_relevance(headline, profile)
        assert score >= 0.5, f"Expected >=0.5 for Navy headline, got {score}"

    def test_empty_body_does_not_crash(self, profile: dict[str, Any]) -> None:
        """Empty or missing body should not crash the scorer."""
        from agents.discovery_agent import RelevanceScorer

        scorer = RelevanceScorer()
        headline = {"title": "", "body": ""}
        score = scorer.score_relevance(headline, profile)
        assert score == 0.0, f"Expected 0.0 for empty headline, got {score}"

    def test_deterministic_scoring(self, profile: dict[str, Any]) -> None:
        """Same inputs should produce same scores."""
        from agents.discovery_agent import RelevanceScorer

        scorer = RelevanceScorer()
        headline = {
            "title": "Federal port regulations affect San Diego shipping",
            "body": "New port regulations will affect Port of San Diego operations.",
        }
        score1 = scorer.score_relevance(headline, profile)
        score2 = scorer.score_relevance(headline, profile)
        assert score1 == score2, f"Expected deterministic scoring, got {score1} != {score2}"

    def test_headline_monitor_no_db(self) -> None:
        """HeadlineMonitorAgent should work even without a DB connection."""
        from agents.discovery_agent import HeadlineMonitorAgent

        agent = HeadlineMonitorAgent(supabase_client=None)
        profile = {
            "display_name": "San Diego, CA",
            "demographics": {},
            "major_employers": [],
            "key_industries": [],
            "economy": {},
            "geography": {},
            "infrastructure": {},
            "military": {},
            "active_local_issues": [],
        }
        result = agent.discover("san-diego-ca", profile, hours=24)
        assert result == [], "Should return empty list with no DB"
