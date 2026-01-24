"""Prompt templates for RAG generation.

All prompts enforce strict grounding in retrieved context.
Key principle: If the model can't ground a claim in sources, it must say so.
"""

from dataclasses import dataclass


@dataclass
class PromptTemplates:
    """Collection of prompt templates for different generation tasks."""

    # === ANALYSIS MODE PROMPTS (Epistemic Guardrails) ===

    ANALYSIS_SYSTEM_PROMPT = """You are a document analysis assistant that helps users understand their documents.

EPISTEMIC RULES (you MUST follow these):
1. Your confidence must not exceed what coverage justifies
2. Separate claims (with citations) from interpretations (marked as synthesis)
3. Surface contradictions without forcing resolution
4. Acknowledge what you cannot assess

Your goal is intellectual honesty first, usefulness second, polish last."""

    ANALYSIS_PROMPT = """Analyze the following documents based on what you can see.

COVERAGE CONTEXT:
{coverage_info}

Given this coverage level, provide analysis appropriate to what you can actually see.

CONTEXT ({num_sources} sources available):
{context}

OUTPUT STRUCTURE (maintain claim-evidence separation):

## Directly Supported Observations
[Claims backed by evidence - cite with [Source N]. These are grounded in the retrieved content.]

## Synthesized Patterns
[Interpretations across sources - preface with "Based on available sources..." or "The content suggests..."]

## Tensions or Contradictions
[Where sources conflict or suggest different conclusions. Do NOT artificially resolve - present both views.]

## Questions Raised
[What the content raises but doesn't answer. What would you want to investigate further?]

## Blind Spots
[What you could NOT assess due to coverage limitations. Be specific about what's missing.]

Begin your analysis:"""

    # === EXPLORATORY SUMMARY PROMPT (Broad summaries) ===

    EXPLORATORY_SUMMARY_PROMPT = """Provide an exploratory overview of this document based on a representative sample.

IMPORTANT - THIS IS AN EXPLORATORY OVERVIEW:
{coverage_info}

You are seeing a sample across different parts of the document. Your goal is to:
1. Identify the main topics and themes present
2. Give the user a map of what the document contains
3. Suggest specific areas they might want to explore deeper

CONTEXT ({num_sources} sources from different document regions):
{context}

OUTPUT STRUCTURE:

## Document Overview
[2-3 sentences describing what this document appears to be about, based on the sample. Use tentative language: "appears to cover", "seems to focus on", "includes discussion of".]

## Key Topics Identified
[Bullet list of main topics/themes found in the sample. Cite sources: [Source N]]

## Notable Points
[3-5 specific observations that stood out, with citations]

## Suggested Focus Areas
[Based on what you've seen, suggest 3-5 specific questions or topics the user could explore for deeper understanding. Frame these as actionable next steps like "To understand X better, try asking about..." or "For more detail on Y, focus on..."]

## Coverage Note
[Brief note on what parts of the document this sample represents and what might be missing]

Begin your exploratory overview:"""

    # === FOCUSED SUMMARY PROMPT (Topic-scoped deep synthesis) ===

    FOCUSED_SUMMARY_PROMPT = """Provide a focused analysis of "{focus_topic}" based on the document content.

COVERAGE CONTEXT:
{coverage_info}

The user wants to understand "{focus_topic}" specifically. Focus your analysis narrowly on this topic.

CONTEXT ({num_sources} sources):
{context}

OUTPUT STRUCTURE:

## Summary: {focus_topic}
[Provide a focused synthesis of what the document says about this specific topic. Cite every claim with [Source N].]

## Key Details
[Specific facts, figures, or statements about {focus_topic} found in the sources]

## Related Connections
[How this topic connects to other themes mentioned in the sources]

## Gaps in Coverage
[What aspects of {focus_topic} are NOT covered in the available sources? What would you need to see to give a more complete picture?]

## Follow-up Questions
[2-3 specific questions that would deepen understanding of {focus_topic}]

Begin your focused analysis:"""

    # === STANDARD WRITING MODE PROMPTS ===

    SYSTEM_PROMPT = """You are a writing assistant that helps users write through uncertainty and draft professional documents.

CRITICAL RULES:
1. Use ONLY the provided context as your knowledge base
2. NEVER make up information not present in the context
3. You MAY include reasoned interpretations or hypotheses IF they are clearly labeled as such
4. Clearly distinguish between:
   - Directly supported claims
   - Reasoned synthesis based on sources
   - Open questions or unknowns
5. Cite which source supports each claim using [Source N] notation
6. If sources conflict, acknowledge the conflict and describe the conflict explicitly

Your goal is transparency - users must be able to verify every claim you make."""

    GENERATION_PROMPT = """Write the following based on the provided context: {topic}

CONTEXT ({num_sources} sources available - you may ONLY cite [Source 1] through [Source {num_sources}]):
{context}

CRITICAL OUTPUT RULES:
- Output ONLY the requested content - no preamble, introduction, or meta-commentary
- Do NOT start with phrases like "Here is...", "Below is...", "I've written...", etc.
- Write in a clear, professional tone
- Structure your response with clear sections using markdown headings (## Section Title)
- MANDATORY: Include [Source N] citations inline after claims or facts. Example: "I have 5 years of Python experience [Source 2] and led a team of 10 developers [Source 4]."
- ONLY cite sources that exist: [Source 1] through [Source {num_sources}]. Do NOT cite any source number higher than {num_sources}.
- Every paragraph MUST have at least one citation - if you cannot cite something, do not include it
- If the context is insufficient for the entire request, write what you can and note gaps at the end

Begin with ## followed by your first section title:"""

    SECTION_PROMPT = """Continue writing about: {topic}

Previous content:
{previous_content}

Additional context:
{context}

Write the next section, maintaining consistency with the previous content and citing sources."""

    REGENERATION_PROMPT = """Rewrite this section using the provided context: {original_section}

{refinement_instructions}

CONTEXT:
{context}

Rewritten section:"""

    SUGGESTED_QUESTIONS_PROMPT = """Based on the following document content, generate {num_questions} thoughtful questions that a user might want to explore or write about.

DOCUMENT CONTENT:
{context}

Generate questions that:
1. Can be answered or explored using the provided content
2. Cover different aspects and topics from the documents
3. Range from specific factual questions to broader analytical ones
4. Would help someone understand or work with this material better

Output ONLY the questions, one per line, numbered 1-{num_questions}. Do not include any other text or explanations:"""

    # === COVERAGE-AWARE QA/WRITING PROMPTS ===

    COVERAGE_AWARE_GENERATION_PROMPT = """Write the following based on the provided context: {topic}

IMPORTANT CONTEXT LIMITATION:
{coverage_info}

CONTEXT ({num_sources} sources available - cite [Source 1] through [Source {num_sources}]):
{context}

CRITICAL OUTPUT RULES:
- Output ONLY the requested content - no preamble or meta-commentary
- Write in a clear, professional tone
- MANDATORY: Include [Source N] citations inline after claims
- ONLY cite sources that exist: [Source 1] through [Source {num_sources}]
- Every paragraph MUST have at least one citation
- If context is insufficient, write what you can and note gaps at the end

Begin writing:"""


def format_context(sources: list[dict]) -> tuple[str, int]:
    """Format retrieved sources into context string.

    Args:
        sources: List of source dictionaries with 'content' and 'metadata'

    Returns:
        Tuple of (formatted context string, number of sources)
    """
    if not sources:
        return "No relevant sources found.", 0

    context_parts = []
    for i, source in enumerate(sources, 1):
        content = source.get("content", "")
        doc_title = source.get("metadata", {}).get("title", "Unknown")

        context_parts.append(f"[Source {i}] (from: {doc_title})\n{content}")

    return "\n\n---\n\n".join(context_parts), len(sources)


def build_generation_prompt(
    topic: str,
    sources: list[dict],
) -> tuple[str, str]:
    """Build the complete prompt for generation.

    Args:
        topic: The topic to write about
        sources: Retrieved source chunks

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    context, num_sources = format_context(sources)

    user_prompt = PromptTemplates.GENERATION_PROMPT.format(
        topic=topic,
        context=context,
        num_sources=num_sources if num_sources > 0 else 0,
    )

    return PromptTemplates.SYSTEM_PROMPT, user_prompt


def build_regeneration_prompt(
    original_section: str,
    sources: list[dict],
    refinement_instructions: str | None = None,
) -> tuple[str, str]:
    """Build prompt for section regeneration.

    Args:
        original_section: The original section content to rewrite
        sources: Retrieved source chunks
        refinement_instructions: Optional instructions for how to refine

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    context, _ = format_context(sources)

    instructions = refinement_instructions or "Improve clarity and ensure all claims are well-supported."

    user_prompt = PromptTemplates.REGENERATION_PROMPT.format(
        original_section=original_section[:500] + "..." if len(original_section) > 500 else original_section,
        refinement_instructions=instructions,
        context=context,
    )

    return PromptTemplates.SYSTEM_PROMPT, user_prompt


def extract_citations(text: str) -> list[int]:
    """Extract citation numbers from generated text.

    Args:
        text: Generated text with [Source N] citations

    Returns:
        List of source numbers that were cited
    """
    import re

    pattern = r"\[Source (\d+)\]"
    matches = re.findall(pattern, text)
    return sorted(set(int(m) for m in matches))


def sanitize_citations(text: str, max_source: int) -> str:
    """Remove citations that reference non-existent sources.

    Args:
        text: Generated text with [Source N] citations
        max_source: Maximum valid source number

    Returns:
        Text with invalid citations removed
    """
    import re

    def replace_invalid(match: re.Match) -> str:
        source_num = int(match.group(1))
        if source_num < 1 or source_num > max_source:
            return ""  # Remove invalid citation
        return match.group(0)  # Keep valid citation

    pattern = r"\[Source (\d+)\]"
    return re.sub(pattern, replace_invalid, text)


def build_suggested_questions_prompt(
    sources: list[dict],
    num_questions: int = 5,
) -> tuple[str, str]:
    """Build prompt for generating suggested questions.

    Args:
        sources: Retrieved source chunks
        num_questions: Number of questions to generate

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    context, _ = format_context(sources)

    system_prompt = """You are a helpful assistant that generates thoughtful questions based on document content.
Your questions should help users explore and understand the material better."""

    user_prompt = PromptTemplates.SUGGESTED_QUESTIONS_PROMPT.format(
        context=context,
        num_questions=num_questions,
    )

    return system_prompt, user_prompt


def parse_questions(text: str) -> list[str]:
    """Parse numbered questions from LLM output.

    Args:
        text: Raw LLM output with numbered questions

    Returns:
        List of question strings
    """
    import re

    # Match lines starting with a number followed by . or )
    pattern = r"^\s*\d+[\.\)]\s*(.+)$"
    questions = []

    for line in text.strip().split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            question = match.group(1).strip()
            if question:
                questions.append(question)

    return questions


def build_analysis_prompt(
    sources: list[dict],
    coverage_summary: str,
) -> tuple[str, str]:
    """Build prompt for analysis mode with epistemic guardrails.

    Args:
        sources: Retrieved source chunks
        coverage_summary: Human-readable coverage description for prompt injection

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    context, num_sources = format_context(sources)

    user_prompt = PromptTemplates.ANALYSIS_PROMPT.format(
        coverage_info=coverage_summary,
        context=context,
        num_sources=num_sources if num_sources > 0 else 0,
    )

    return PromptTemplates.ANALYSIS_SYSTEM_PROMPT, user_prompt


def build_coverage_aware_generation_prompt(
    topic: str,
    sources: list[dict],
    coverage_summary: str,
) -> tuple[str, str]:
    """Build coverage-aware prompt for writing/QA modes.

    Args:
        topic: The topic to write about
        sources: Retrieved source chunks
        coverage_summary: Human-readable coverage description

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    context, num_sources = format_context(sources)

    user_prompt = PromptTemplates.COVERAGE_AWARE_GENERATION_PROMPT.format(
        topic=topic,
        coverage_info=coverage_summary,
        context=context,
        num_sources=num_sources if num_sources > 0 else 0,
    )

    return PromptTemplates.SYSTEM_PROMPT, user_prompt


def build_exploratory_summary_prompt(
    sources: list[dict],
    coverage_summary: str,
) -> tuple[str, str]:
    """Build prompt for broad/exploratory summaries.

    Used when user asks for general summarization without a specific topic.
    Outputs overview + suggested focus areas for deeper exploration.

    Args:
        sources: Retrieved source chunks (from diverse sampling)
        coverage_summary: Human-readable coverage description

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    context, num_sources = format_context(sources)

    user_prompt = PromptTemplates.EXPLORATORY_SUMMARY_PROMPT.format(
        coverage_info=coverage_summary,
        context=context,
        num_sources=num_sources if num_sources > 0 else 0,
    )

    return PromptTemplates.ANALYSIS_SYSTEM_PROMPT, user_prompt


def build_focused_summary_prompt(
    focus_topic: str,
    sources: list[dict],
    coverage_summary: str,
) -> tuple[str, str]:
    """Build prompt for focused/topic-scoped summaries.

    Used when user asks to summarize a specific topic within the document.
    Outputs deep synthesis on the specified topic.

    Args:
        focus_topic: The specific topic to focus on
        sources: Retrieved source chunks
        coverage_summary: Human-readable coverage description

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    context, num_sources = format_context(sources)

    user_prompt = PromptTemplates.FOCUSED_SUMMARY_PROMPT.format(
        focus_topic=focus_topic,
        coverage_info=coverage_summary,
        context=context,
        num_sources=num_sources if num_sources > 0 else 0,
    )

    return PromptTemplates.ANALYSIS_SYSTEM_PROMPT, user_prompt
