"""Prompt templates for RAG generation.

All prompts enforce strict grounding in retrieved context.
Key principle: If the model can't ground a claim in sources, it must say so.
"""

from dataclasses import dataclass


@dataclass
class PromptTemplates:
    """Collection of prompt templates for different generation tasks."""

    SYSTEM_PROMPT = """You are a writing assistant that helps users draft professional documents.

CRITICAL RULES:
1. Use ONLY the provided context to write your response
2. NEVER make up information not present in the context
3. If the context is insufficient, explicitly say "I don't have enough information to write about [topic]"
4. Cite which source supports each claim using [Source N] notation
5. If sources conflict, acknowledge the conflict

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
