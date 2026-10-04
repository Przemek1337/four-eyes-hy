from __future__ import annotations

CHARS_PER_TOKEN = 4  # estimate without a tokenizer dependency (spec §4.4)


def split_text(text: str, max_tokens: int, overlap_tokens: int = 200) -> list[str]:
    """Split text into overlapping chunks that fit a model's input limit."""
    size = max_tokens * CHARS_PER_TOKEN
    if len(text) <= size:
        return [text]
    if overlap_tokens >= max_tokens:
        raise ValueError("overlap must be smaller than the chunk")
    overlap = overlap_tokens * CHARS_PER_TOKEN
    step = size - overlap
    return [text[i:i + size] for i in range(0, len(text) - overlap, step)]
