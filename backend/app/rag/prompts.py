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

    GENERATION_PROMPT = """Based on the following context, write a professional document section about: {topic}

CONTEXT:
{context}

INSTRUCTIONS:
- Write in a clear, professional tone
- Structure the content logically with paragraphs
- After each major claim or fact, cite the source using [Source N] notation
- If you cannot find support for something in the context, do not write it
- If the context is insufficient, explain what information is missing

Write the content now:"""

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


def format_context(sources: list[dict]) -> str:
    """Format retrieved sources into context string.

    Args:
        sources: List of source dictionaries with 'content' and 'metadata'

    Returns:
        Formatted context string with source labels
    """
    if not sources:
        return "No relevant sources found."

    context_parts = []
    for i, source in enumerate(sources, 1):
        content = source.get("content", "")
        doc_title = source.get("metadata", {}).get("title", "Unknown")

        context_parts.append(f"[Source {i}] (from: {doc_title})\n{content}")

    return "\n\n---\n\n".join(context_parts)


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
    context = format_context(sources)

    user_prompt = PromptTemplates.GENERATION_PROMPT.format(
        topic=topic,
        context=context,
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
    context = format_context(sources)

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
