"""Turn data/raw/*.md case studies into retrieval-ready chunks in data/processed/.

Each case study is split on its H2 sections (further split on H3 if a section
is long). "Related information" sections are dropped — they're just link lists.
Output: one JSON object per line, each a self-contained chunk of text ready to
embed and to hand to the LLM as context.

Usage: python -m scripts.build_case_study_chunks
"""

import json
import re
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "case_studies.jsonl"

MAX_SECTION_WORDS = 450
MIN_CHUNK_WORDS = 25
SKIP_SECTIONS = {"related information"}


def clean_markdown(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)  # images
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # links -> link text
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_frontmatter_title(raw: str, fallback: str) -> str:
    match = re.search(r"^title:\s*(.+)$", raw, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def split_sections(body: str, level: str) -> list[tuple[str, str]]:
    """Split body text on headings of the given markdown level (e.g. '## ')."""
    pattern = re.compile(rf"^{re.escape(level)}(.+)$", re.MULTILINE)
    matches = list(pattern.finditer(body))
    if not matches:
        return [("", body)]

    sections = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections.append((m.group(1).strip(), body[start:end]))
    return sections


HEADING_LEVELS = ["### ", "#### "]


def split_by_paragraph(body: str) -> list[str]:
    """Fallback for flat sections with no sub-headings: group paragraphs into
    ~MAX_SECTION_WORDS pieces so nothing gets silently truncated at embed time."""
    paragraphs = [p for p in re.split(r"\n\s*\n", body) if p.strip()]
    pieces, current, current_words = [], [], 0

    for p in paragraphs:
        words = len(p.split())
        if current and current_words + words > MAX_SECTION_WORDS:
            pieces.append("\n\n".join(current))
            current, current_words = [], 0
        current.append(p)
        current_words += words

    if current:
        pieces.append("\n\n".join(current))
    return pieces


def split_to_size(title: str, body: str, level_idx: int = 0) -> list[tuple[str, str]]:
    """Recursively split body by heading level until each piece fits MAX_SECTION_WORDS.
    Once headings run out, fall back to paragraph grouping."""
    if len(body.split()) <= MAX_SECTION_WORDS:
        return [(title, body)]

    if level_idx >= len(HEADING_LEVELS):
        pieces = split_by_paragraph(body)
        if len(pieces) == 1:
            return [(title, body)]  # single oversized paragraph; nothing more to split on
        return [(f"{title} (part {i + 1})" if title else "", piece) for i, piece in enumerate(pieces)]

    sub_sections = split_sections(body, HEADING_LEVELS[level_idx])
    if len(sub_sections) == 1 and sub_sections[0][0] == "":
        # No headings at this level found; try the next level down
        return split_to_size(title, body, level_idx + 1)

    result = []
    for sub_title, sub_body in sub_sections:
        label = " > ".join(s for s in (title, sub_title) if s)
        result.extend(split_to_size(label, sub_body, level_idx + 1))
    return result


def build_chunks() -> list[dict]:
    chunks = []

    for path in sorted(RAW_DIR.glob("*.md")):
        slug = path.stem
        raw = path.read_text(encoding="utf-8")

        # Drop frontmatter and the hidden "#customer intent" SEO line
        body = re.sub(r"^---.*?---\n", "", raw, flags=re.DOTALL)
        body = re.sub(r"^#customer intent:.*$", "", body, flags=re.MULTILINE)

        h1_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = parse_frontmatter_title(raw, fallback=h1_match.group(1) if h1_match else slug)
        body = re.sub(r"^#\s+.+$", "", body, count=1, flags=re.MULTILINE)

        source_url = f"https://learn.microsoft.com/en-us/power-platform/guidance/case-studies/{slug}"

        for h2_title, h2_body in split_sections(body, "## "):
            if h2_title.strip().lower() in SKIP_SECTIONS:
                continue

            for section_label, sub_body in split_to_size(h2_title, h2_body):
                cleaned = clean_markdown(sub_body)
                if len(cleaned.split()) < MIN_CHUNK_WORDS:
                    continue

                header = f"Case study: {title}"
                if section_label:
                    header += f"\nSection: {section_label}"

                chunks.append(
                    {
                        "id": f"{slug}#{len(chunks)}",
                        "slug": slug,
                        "title": title,
                        "section": section_label,
                        "source_url": source_url,
                        "text": f"{header}\n\n{cleaned}",
                    }
                )

    return chunks


def main() -> None:
    chunks = build_chunks()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")

    words = [len(c["text"].split()) for c in chunks]
    print(f"Wrote {len(chunks)} chunks from {len(list(RAW_DIR.glob('*.md')))} case studies to {OUT_PATH}")
    print(f"Chunk size: min={min(words)} max={max(words)} avg={sum(words) / len(words):.0f} words")


if __name__ == "__main__":
    main()
