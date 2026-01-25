"""Intent detection service for classifying user queries.

Pattern-based detection to determine retrieval strategy:
- ANALYSIS: User wants to understand/summarize documents
- QA: User asking specific questions
- WRITING: User wants to create new content (default)
"""

import re
from dataclasses import dataclass

from ..core import get_logger
from ..models import IntentClassification, QueryIntent, RetrievalType, SummaryScope

logger = get_logger(__name__)


# Patterns to detect focused (topic-scoped) summaries
# These indicate the user wants a deep dive on a specific topic
# Each pattern should capture the TOPIC, not the verb
FOCUSED_SUMMARY_PATTERNS = [
    # "Summarize X in this document" - capture X (non-greedy, before "in/from")
    r"\b(?:summarize|summary|summarise)\s+(?:the\s+)?(.+?)\s+(?:in|from)\s+(?:this|the)\s+document",
    # "Summarize the X section/chapter/part" - capture X section
    r"\b(?:summarize|summary|summarise)\s+((?:the\s+)?.+?(?:section|chapter|part))",
    # "What does it say about X" - capture X (everything after "about")
    r"\bwhat\s+does\s+(?:it|the\s+document)\s+say\s+about\s+(.+?)(?:\?|$)",
    # "Go deeper on X" / "More detail on X" - capture X
    r"\b(?:go\s+deeper|more\s+detail|elaborate|expand)\s+(?:on|about)\s+(.+?)(?:\?|$)",
    # "Focus on X" - capture X
    r"\bfocus\s+(?:on|about)\s+(.+?)(?:\?|$)",
    # "Analyze the X in/from" (specific topic) - capture X
    r"\b(?:analyze|analyse)\s+(?:the\s+)?(.+?)\s+(?:in|from)\s+",
]


@dataclass
class IntentPattern:
    """Pattern for intent matching."""
    patterns: list[str]
    intent: QueryIntent
    retrieval_type: RetrievalType
    confidence_boost: float = 0.0  # Bonus confidence for strong matches


# Intent detection patterns ordered by specificity
ANALYSIS_PATTERNS = IntentPattern(
    patterns=[
        # High-priority: "write a summary" should be ANALYSIS, not WRITING
        r"\b(write|draft|create)\s+(a\s+)?(summary|overview|analysis)\b",
        r"\b(summarize|summary|summarise)\b",
        r"\b(overview|overviews)\b",
        r"\b(main\s+points?|key\s+points?)\b",
        r"\b(key\s+takeaways?|main\s+takeaways?|takeaways?)\b",
        r"\b(what\s+are\s+the\s+main)\b",
        r"\b(what\s+are\s+the\s+key)\b",
        r"\b(what\s+is\s+the\s+overview)\b",
        r"\b(analyze|analyse|analysis)\b",
        # "analyse/analyze this document" - strong analysis signal
        r"\b(analyze|analyse)\s+(this|the)\s+(document|text|file)\b",
        r"\b(themes?|patterns?)\s+(in|from|across)\b",
        r"\b(extract|identify)\s+(key|main|important|ideas?)\b",
        # Focused summary triggers (escalation phrases)
        r"\b(go\s+deeper|more\s+detail|elaborate|expand)\s+on\b",
        r"\b(focus\s+on)\b",
        r"\bwhat\s+does\s+(it|the\s+document)\s+say\s+about\b",
        # Document-level analysis
        r"\b(about\s+this\s+document|of\s+this\s+document)\b",
        # "what is at stake" type analysis questions
        r"\bwhat\s+is\s+at\s+stake\b",
        r"\bwhat\s+are\s+the\s+(implications?|consequences?|issues?)\b",
    ],
    intent=QueryIntent.ANALYSIS,
    retrieval_type=RetrievalType.DIVERSE,
    confidence_boost=0.20,  # Higher boost for analysis to win over WRITING when both match
)

QA_PATTERNS = IntentPattern(
    patterns=[
        r"^(what|when|where|who|why|how|which|is|are|do|does|did|can|could|would|should)\s+",
        r"\?\s*$",
        r"\b(tell\s+me\s+about)\b",
        r"\b(explain|describe)\s+(what|how|why)\b",
        r"\b(find|look\s+for|search\s+for)\b",
    ],
    intent=QueryIntent.QA,
    retrieval_type=RetrievalType.SIMILARITY,
    confidence_boost=0.05,
)

WRITING_PATTERNS = IntentPattern(
    patterns=[
        r"\b(write|draft|create|compose|generate)\b",
        r"\b(cover\s+letter|resume|cv)\b",
        r"\b(letter|email|memo|report)\b",
        r"\b(help\s+me\s+write)\b",
        r"\b(prepare|craft)\b",
    ],
    intent=QueryIntent.WRITING,
    retrieval_type=RetrievalType.SIMILARITY,
    confidence_boost=0.15,
)


class IntentService:
    """Service for detecting user query intent."""

    def __init__(self):
        """Initialize intent service with compiled patterns.

        Order matters: ANALYSIS checked first so 'write a summary'
        is detected as analysis, not writing.
        """
        self._patterns = [
            (ANALYSIS_PATTERNS, self._compile_patterns(ANALYSIS_PATTERNS)),
            (QA_PATTERNS, self._compile_patterns(QA_PATTERNS)),
            (WRITING_PATTERNS, self._compile_patterns(WRITING_PATTERNS)),
        ]
        # Compile focused summary patterns
        self._focused_patterns = [
            re.compile(p, re.IGNORECASE) for p in FOCUSED_SUMMARY_PATTERNS
        ]

    def _compile_patterns(self, pattern_group: IntentPattern) -> list[re.Pattern]:
        """Compile regex patterns for faster matching."""
        return [re.compile(p, re.IGNORECASE) for p in pattern_group.patterns]

    def _detect_summary_scope(self, query: str) -> tuple[SummaryScope, str | None]:
        """Detect whether a summary request is broad or focused.

        Args:
            query: The user's query text

        Returns:
            Tuple of (SummaryScope, focus_topic or None)
        """
        query_lower = query.lower().strip()

        # Check for focused summary patterns
        for pattern in self._focused_patterns:
            match = pattern.search(query_lower)
            if match:
                # Extract the focus topic from the capture group
                groups = match.groups()
                # Find the first non-empty group that looks like a topic
                focus_topic = None
                for group in groups:
                    if group and len(group) > 2 and group not in ("the", "this", "a"):
                        focus_topic = group.strip()
                        break

                if focus_topic:
                    logger.info(
                        "Focused summary detected",
                        focus_topic=focus_topic,
                        query_preview=query[:50],
                    )
                    return SummaryScope.FOCUSED, focus_topic

        # Check if it's a broad summary (general summarization without specific topic)
        broad_patterns = [
            r"\b(summarize|summary|summarise)\s+(this|the)\s+(document|file|text|content)s?\b",
            r"\b(give|provide)\s+(me\s+)?(a|an)?\s*(summary|overview)\b",
            r"\b(what\s+are\s+the\s+main|key)\s+(points?|takeaways?|themes?)\b",
            r"\boverview\s+of\s+(this|the)\s+(document|file)\b",
        ]

        for pattern_str in broad_patterns:
            if re.search(pattern_str, query_lower):
                logger.info(
                    "Broad summary detected",
                    query_preview=query[:50],
                )
                return SummaryScope.BROAD, None

        # Default: if analysis intent but no clear scope, treat as broad
        return SummaryScope.BROAD, None

    def detect_intent(self, query: str) -> IntentClassification:
        """Detect the intent of a user query.

        Args:
            query: The user's query text

        Returns:
            IntentClassification with detected intent, confidence, and suggested retrieval
        """
        query = query.strip()
        query_lower = query.lower()

        matches: list[tuple[IntentPattern, int, float]] = []

        for pattern_group, compiled in self._patterns:
            match_count = 0
            for pattern in compiled:
                if pattern.search(query_lower):
                    match_count += 1

            if match_count > 0:
                matches.append((pattern_group, match_count, pattern_group.confidence_boost))

        if not matches:
            # Default to WRITING for ambiguous queries (preserves existing behavior)
            logger.info(
                "No intent patterns matched, defaulting to WRITING",
                query_preview=query[:50],
            )
            return IntentClassification(
                intent=QueryIntent.WRITING,
                confidence=0.5,
                reasoning="No specific patterns matched; defaulting to writing mode",
                suggested_retrieval=RetrievalType.SIMILARITY,
                summary_scope=SummaryScope.NOT_APPLICABLE,
                focus_topic=None,
            )

        # Sort by match count (more matches = higher confidence)
        matches.sort(key=lambda x: (x[1], x[2]), reverse=True)
        best_match = matches[0]
        pattern_group, match_count, boost = best_match

        # Calculate confidence based on match count and pattern specificity
        base_confidence = min(0.6 + (match_count * 0.1) + boost, 0.95)

        # Build reasoning
        reasoning = self._build_reasoning(query, pattern_group, match_count)

        # Determine summary scope for ANALYSIS intent
        summary_scope = SummaryScope.NOT_APPLICABLE
        focus_topic = None

        if pattern_group.intent == QueryIntent.ANALYSIS:
            summary_scope, focus_topic = self._detect_summary_scope(query)
            # Add scope info to reasoning
            if summary_scope == SummaryScope.FOCUSED and focus_topic:
                reasoning += f" (focused on: {focus_topic})"
            elif summary_scope == SummaryScope.BROAD:
                reasoning += " (broad exploratory summary)"

        logger.info(
            "Intent detected",
            intent=pattern_group.intent.value,
            confidence=round(base_confidence, 2),
            match_count=match_count,
            summary_scope=summary_scope.value,
            focus_topic=focus_topic,
            query_preview=query[:50],
        )

        return IntentClassification(
            intent=pattern_group.intent,
            confidence=base_confidence,
            reasoning=reasoning,
            suggested_retrieval=pattern_group.retrieval_type,
            summary_scope=summary_scope,
            focus_topic=focus_topic,
        )

    def _build_reasoning(
        self,
        query: str,
        pattern_group: IntentPattern,
        match_count: int,
    ) -> str:
        """Build human-readable reasoning for the classification."""
        intent_descriptions = {
            QueryIntent.ANALYSIS: "analysis/summarization",
            QueryIntent.QA: "question-answering",
            QueryIntent.WRITING: "content creation",
        }

        desc = intent_descriptions.get(pattern_group.intent, str(pattern_group.intent))

        if match_count > 2:
            return f"Strong {desc} indicators detected ({match_count} pattern matches)"
        elif match_count > 1:
            return f"Multiple {desc} indicators detected"
        else:
            return f"Query matches {desc} pattern"


# Singleton instance
_intent_service: IntentService | None = None


def get_intent_service() -> IntentService:
    """Get the singleton intent service instance."""
    global _intent_service
    if _intent_service is None:
        _intent_service = IntentService()
    return _intent_service
