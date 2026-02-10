"""Tests for intent detection service.

Verifies that queries are correctly classified as:
- ANALYSIS: summarize, overview, key takeaways
- QA: questions (what, when, where, who, why, how)
- WRITING: write, draft, create, compose (default)
"""

import pytest

from app.models import QueryIntent, RetrievalType, SummaryScope
from app.services.intent import IntentService, get_intent_service


class TestIntentDetection:
    """Test intent detection patterns."""

    @pytest.fixture
    def intent_service(self) -> IntentService:
        """Create a fresh intent service for each test."""
        return IntentService()

    # ========================================================================
    # Analysis Intent Tests
    # ========================================================================

    @pytest.mark.parametrize(
        "query",
        [
            "Summarize this document",
            "Give me a summary of the content",
            "Provide an overview",
            "What are the main points?",
            "List the key points",
            "Analyze the document",
            "Provide an analysis of the themes",
            "Identify the main themes in this document",
            "What is the overview of this?",
            "What are the key takeaways from this?",
            "Extract key ideas from this",
        ],
    )
    def test_analysis_intent_detected(self, intent_service: IntentService, query: str):
        """Queries requesting summarization/analysis should be classified as ANALYSIS."""
        result = intent_service.detect_intent(query)

        assert result.intent == QueryIntent.ANALYSIS
        assert result.suggested_retrieval == RetrievalType.DIVERSE
        assert result.confidence > 0.5

    # ========================================================================
    # QA Intent Tests
    # ========================================================================

    @pytest.mark.parametrize(
        "query",
        [
            "What is my degree?",
            "When did I graduate?",
            "Where did I work?",
            "Who was my supervisor?",
            "Why did I leave my previous job?",
            "How long did I work there?",
            "What skills do I have?",
            "Is there any mention of Python?",
            "Tell me about my experience",
        ],
    )
    def test_qa_intent_detected(self, intent_service: IntentService, query: str):
        """Question-like queries should be classified as QA."""
        result = intent_service.detect_intent(query)

        assert result.intent == QueryIntent.QA
        assert result.suggested_retrieval == RetrievalType.SIMILARITY
        assert result.confidence > 0.5

    # ========================================================================
    # Writing Intent Tests
    # ========================================================================

    @pytest.mark.parametrize(
        "query",
        [
            "Write a cover letter",
            "Draft a professional email",
            "Create a resume summary",
            "Compose an introduction",
            "Generate a response",
            "Help me write a letter",
            "Prepare a memo",
            "Write me a cover letter for software engineer position",
        ],
    )
    def test_writing_intent_detected(self, intent_service: IntentService, query: str):
        """Writing requests should be classified as WRITING."""
        result = intent_service.detect_intent(query)

        assert result.intent == QueryIntent.WRITING
        assert result.suggested_retrieval == RetrievalType.SIMILARITY
        assert result.confidence > 0.5

    # ========================================================================
    # Default Behavior Tests
    # ========================================================================

    @pytest.mark.parametrize(
        "query",
        [
            "Hello",
            "test",
            "random text here",
            "something else entirely",
        ],
    )
    def test_ambiguous_queries_default_to_writing(self, intent_service: IntentService, query: str):
        """Ambiguous queries without clear intent should default to WRITING."""
        result = intent_service.detect_intent(query)

        assert result.intent == QueryIntent.WRITING
        assert result.suggested_retrieval == RetrievalType.SIMILARITY
        # Lower confidence for ambiguous queries
        assert result.confidence <= 0.6

    # ========================================================================
    # Edge Cases
    # ========================================================================

    def test_mixed_signals_summary_prioritizes_analysis(self, intent_service: IntentService):
        """When query has both writing and summary signals, analysis takes priority."""
        query = "Write a summary of my experience"
        result = intent_service.detect_intent(query)

        # "summary" keyword triggers ANALYSIS priority over WRITING
        assert result.intent == QueryIntent.ANALYSIS

    def test_case_insensitive_detection(self, intent_service: IntentService):
        """Intent detection should be case-insensitive."""
        result_lower = intent_service.detect_intent("summarize this document")
        result_upper = intent_service.detect_intent("SUMMARIZE THIS DOCUMENT")
        result_mixed = intent_service.detect_intent("SumMarIzE this Document")

        assert result_lower.intent == result_upper.intent == result_mixed.intent
        assert all(
            r.intent == QueryIntent.ANALYSIS for r in [result_lower, result_upper, result_mixed]
        )

    def test_confidence_increases_with_more_matches(self, intent_service: IntentService):
        """Multiple pattern matches should increase confidence."""
        single_match = intent_service.detect_intent("summarize")
        multiple_matches = intent_service.detect_intent(
            "summarize the main points and key takeaways"
        )

        assert multiple_matches.confidence > single_match.confidence

    def test_reasoning_included(self, intent_service: IntentService):
        """All classifications should include reasoning."""
        result = intent_service.detect_intent("summarize this document")

        assert result.reasoning is not None
        assert len(result.reasoning) > 0

    def test_empty_query_handled(self, intent_service: IntentService):
        """Empty or whitespace queries should default to WRITING."""
        result = intent_service.detect_intent("   ")

        assert result.intent == QueryIntent.WRITING
        assert result.confidence == 0.5


class TestIntentClassificationSerialization:
    """Test IntentClassification serialization."""

    @pytest.fixture
    def intent_service(self) -> IntentService:
        return IntentService()

    def test_to_dict(self, intent_service: IntentService):
        """IntentClassification should serialize to dict correctly."""
        result = intent_service.detect_intent("summarize the document")
        data = result.to_dict()

        assert data["intent"] == "analysis"
        assert data["suggested_retrieval"] == "diverse"
        assert "confidence" in data
        assert "reasoning" in data
        assert "summary_scope" in data

    def test_from_dict(self, intent_service: IntentService):
        """IntentClassification should deserialize from dict correctly."""
        from app.models import IntentClassification

        data = {
            "intent": "analysis",
            "confidence": 0.85,
            "reasoning": "Test reasoning",
            "suggested_retrieval": "diverse",
            "summary_scope": "focused",
            "focus_topic": "ethics",
        }

        result = IntentClassification.from_dict(data)

        assert result.intent == QueryIntent.ANALYSIS
        assert result.confidence == 0.85
        assert result.reasoning == "Test reasoning"
        assert result.suggested_retrieval == RetrievalType.DIVERSE
        assert result.summary_scope == SummaryScope.FOCUSED
        assert result.focus_topic == "ethics"


class TestIntentServiceSingleton:
    """Test singleton behavior of intent service."""

    def test_get_intent_service_returns_same_instance(self):
        """get_intent_service should return the same instance."""
        service1 = get_intent_service()
        service2 = get_intent_service()

        assert service1 is service2


class TestSummaryScopeDetection:
    """Test summary scope detection (broad vs focused)."""

    @pytest.fixture
    def intent_service(self) -> IntentService:
        return IntentService()

    # ========================================================================
    # Broad Summary Tests
    # ========================================================================

    @pytest.mark.parametrize(
        "query",
        [
            "Summarize this document",
            "Give me a summary",
            "Provide an overview",
            "What are the main points?",
            "What are the key takeaways?",
            "Overview of this document",
            "Summarize the document",
        ],
    )
    def test_broad_summary_detected(self, intent_service: IntentService, query: str):
        """Broad summary requests should have BROAD scope."""
        result = intent_service.detect_intent(query)

        assert result.intent == QueryIntent.ANALYSIS
        assert result.summary_scope == SummaryScope.BROAD
        assert result.focus_topic is None

    # ========================================================================
    # Focused Summary Tests
    # ========================================================================

    @pytest.mark.parametrize(
        "query,expected_topic",
        [
            ("Summarize the ethics section in this document", "ethics"),
            ("Summarize data bias in this document", "bias"),
            ("Go deeper on intersectionality", "intersectionality"),
            ("More detail on the methodology", "methodology"),
            ("Focus on the results section", "results"),
            ("Analyze the findings in this document", "findings"),
        ],
    )
    def test_focused_summary_detected(
        self, intent_service: IntentService, query: str, expected_topic: str
    ):
        """Focused summary requests should have FOCUSED scope with topic extracted."""
        result = intent_service.detect_intent(query)

        assert result.intent == QueryIntent.ANALYSIS
        assert result.summary_scope == SummaryScope.FOCUSED
        assert result.focus_topic is not None
        # Topic should contain the key word
        assert expected_topic.lower() in result.focus_topic.lower()

    # ========================================================================
    # Non-Analysis Intents
    # ========================================================================

    def test_writing_intent_has_not_applicable_scope(self, intent_service: IntentService):
        """Writing intent should have NOT_APPLICABLE summary scope."""
        result = intent_service.detect_intent("Write a cover letter")

        assert result.intent == QueryIntent.WRITING
        assert result.summary_scope == SummaryScope.NOT_APPLICABLE
        assert result.focus_topic is None

    def test_qa_intent_has_not_applicable_scope(self, intent_service: IntentService):
        """QA intent should have NOT_APPLICABLE summary scope."""
        result = intent_service.detect_intent("What is my degree?")

        assert result.intent == QueryIntent.QA
        assert result.summary_scope == SummaryScope.NOT_APPLICABLE
        assert result.focus_topic is None

    # ========================================================================
    # Serialization with Summary Scope
    # ========================================================================

    def test_to_dict_includes_summary_scope(self, intent_service: IntentService):
        """Serialization should include summary_scope."""
        result = intent_service.detect_intent("Summarize the ethics in this document")
        data = result.to_dict()

        assert "summary_scope" in data
        assert data["summary_scope"] in ["broad", "focused", "not_applicable"]

    def test_to_dict_includes_focus_topic_when_present(self, intent_service: IntentService):
        """Serialization should include focus_topic when present."""
        result = intent_service.detect_intent("Summarize the ethics in this document")
        data = result.to_dict()

        if result.summary_scope == SummaryScope.FOCUSED:
            assert "focus_topic" in data
            assert data["focus_topic"] is not None
