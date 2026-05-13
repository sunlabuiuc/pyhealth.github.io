"""One-shot generator for a long lorem-ipsum blog post used for visual testing."""
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "blogs" / "2026-05-12" / "stress-test.md"
TARGET_WORDS = 25000
SEED = 42

SENTENCES = [
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
    "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.",
    "Curabitur pretium tincidunt lacus, nulla gravida orci a odio.",
    "Nullam varius, turpis et commodo pharetra, est eros bibendum elit, nec luctus magna felis sollicitudin mauris.",
    "Integer in mauris eu nibh euismod gravida, ut nulla velit aliquam erat, vitae faucibus ipsum tortor non magna.",
    "Donec auctor, ligula nec ultrices tincidunt, ipsum lectus dignissim nibh, sit amet pretium turpis ante eget arcu.",
    "Phasellus ac nisl in mi tincidunt facilisis sed et metus, in volutpat lectus.",
    "Quisque ultricies, est in suscipit fermentum, nibh quam suscipit purus, sit amet posuere libero augue at lectus.",
    "Aliquam erat volutpat. In hac habitasse platea dictumst, sed venenatis libero nec lorem placerat ultricies.",
    "Cras venenatis lectus eget metus eleifend, eu commodo tortor luctus, vitae pulvinar leo varius.",
    "Vivamus euismod mauris in dolor pharetra, sit amet pellentesque magna fermentum.",
    "Suspendisse potenti, vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae.",
    "Maecenas tincidunt ligula vel turpis aliquam, eu condimentum ipsum hendrerit, ut commodo lacus posuere.",
    "Fusce mollis purus a nisi malesuada, vel viverra ipsum tincidunt, ut convallis sapien ultricies.",
    "Etiam sodales urna a dui pretium, in feugiat magna semper, non sodales nibh hendrerit.",
    "Praesent rhoncus, mauris a ultricies bibendum, ipsum lorem porta lectus, a feugiat tellus ipsum sit amet ipsum.",
    "Mauris aliquet, nibh sit amet posuere blandit, sapien orci ornare risus, at sollicitudin urna lectus eget urna.",
    "Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae.",
    "Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas.",
]

EMPHASIS_PHRASES = [
    "**dolor sit amet**", "*consectetur adipiscing*", "**incididunt ut labore**",
    "*sed do eiusmod*", "**ad minim veniam**", "*ullamco laboris*",
    "**reprehenderit in voluptate**", "*velit esse cillum*", "**non proident**",
    "*culpa qui officia*",
]

LINKS = [
    "[lorem ipsum](#)", "[adipiscing elit](#)", "[ut labore](#)",
    "[ad minim veniam](#)", "[dolor sit](#)", "[consectetur](#)",
]

INLINE_CODES = [
    "`lorem.ipsum()`", "`dolor.sit(amet)`", "`adipiscing[\"elit\"]`",
    "`eiusmod_tempor`", "`labore.dolore`", "`magna_aliqua`",
]

CODE_BLOCKS = [
    ("python", """def lorem_ipsum(words: int = 50) -> str:
    \"\"\"Generate a lorem ipsum string with the requested word count.\"\"\"
    pool = LOREM_SENTENCES * (words // 10 + 1)
    text = ' '.join(pool)
    return ' '.join(text.split()[:words])


class IpsumGenerator:
    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)

    def paragraph(self, sentences: int = 5) -> str:
        return ' '.join(self.rng.choices(LOREM_SENTENCES, k=sentences))
"""),
    ("javascript", """function loremIpsum(words = 50) {
  const pool = LOREM_SENTENCES.flatMap(() => LOREM_SENTENCES);
  const text = pool.join(' ');
  return text.split(/\\s+/).slice(0, words).join(' ');
}

const generator = {
  seed: 42,
  paragraph(sentences = 5) {
    return Array.from({ length: sentences }, () =>
      LOREM_SENTENCES[Math.floor(Math.random() * LOREM_SENTENCES.length)]
    ).join(' ');
  },
};
"""),
    ("bash", """#!/usr/bin/env bash
# Generate lorem ipsum sample text
set -euo pipefail

words=${1:-50}
echo "Generating $words words of lorem ipsum..."

for i in $(seq 1 "$words"); do
  printf "lorem "
done
echo
"""),
]

SECTION_TITLES = [
    "Lorem Ipsum Dolor Sit Amet",
    "Consectetur Adipiscing Elit",
    "Eiusmod Tempor Incididunt",
    "Ut Labore Et Dolore",
    "Magna Aliqua Veniam",
    "Quis Nostrud Exercitation",
    "Ullamco Laboris Nisi",
    "Aliquip Ex Ea Commodo",
    "Duis Aute Irure",
    "Reprehenderit Voluptate",
    "Velit Esse Cillum",
    "Fugiat Nulla Pariatur",
    "Excepteur Sint Occaecat",
    "Cupidatat Non Proident",
    "Sunt In Culpa Qui",
    "Officia Deserunt Mollit",
]


def count_words(s: str) -> int:
    return len(s.split())


def main() -> None:
    rng = random.Random(SEED)
    parts: list[str] = []
    parts.append("---")
    parts.append('title: "The Long Read: A Visual Stress Test in Lorem Ipsum"')
    parts.append('author: "Dolor Sitamet"')
    parts.append("---")
    parts.append("")

    lead = " ".join(rng.choices(SENTENCES, k=6))
    parts.append(lead)
    parts.append("")
    word_count = count_words(lead)

    section_idx = 0
    while word_count < TARGET_WORDS:
        title = SECTION_TITLES[section_idx % len(SECTION_TITLES)]
        suffix = section_idx // len(SECTION_TITLES)
        if suffix:
            title = f"{title} ({suffix + 1})"
        parts.append(f"## {title}")
        parts.append("")
        section_idx += 1

        # 2-4 paragraphs
        for _ in range(rng.randint(2, 4)):
            n = rng.randint(5, 9)
            sentences = rng.choices(SENTENCES, k=n)
            if rng.random() < 0.45:
                sentences[rng.randrange(n)] = sentences[rng.randrange(n)].replace(
                    "dolor", rng.choice(EMPHASIS_PHRASES), 1
                )
            if rng.random() < 0.35:
                inline = rng.choice(INLINE_CODES)
                sentences[rng.randrange(n)] = f"Consider {inline} in this context: " + sentences[rng.randrange(n)]
            if rng.random() < 0.3:
                link = rng.choice(LINKS)
                sentences[rng.randrange(n)] = sentences[rng.randrange(n)] + f" See also {link} for further reading."
            paragraph = " ".join(sentences)
            parts.append(paragraph)
            parts.append("")
            word_count += count_words(paragraph)
            if word_count >= TARGET_WORDS:
                break

        if word_count >= TARGET_WORDS:
            break

        # Sometimes add an h3 + paragraph
        if rng.random() < 0.55:
            sub = rng.choice(SECTION_TITLES)
            parts.append(f"### {sub}")
            parts.append("")
            n = rng.randint(4, 7)
            paragraph = " ".join(rng.choices(SENTENCES, k=n))
            parts.append(paragraph)
            parts.append("")
            word_count += count_words(paragraph)

        roll = rng.random()
        if roll < 0.22:
            # bulleted list
            items = rng.randint(3, 5)
            parts.append("Some key considerations:")
            parts.append("")
            for _ in range(items):
                item = rng.choice(SENTENCES)
                parts.append(f"- {item}")
                word_count += count_words(item)
            parts.append("")
        elif roll < 0.40:
            # numbered list
            items = rng.randint(3, 5)
            parts.append("The process can be summarized as follows:")
            parts.append("")
            for i in range(items):
                item = rng.choice(SENTENCES)
                parts.append(f"{i + 1}. {item}")
                word_count += count_words(item)
            parts.append("")
        elif roll < 0.55:
            # blockquote
            q = " ".join(rng.choices(SENTENCES, k=rng.randint(2, 4)))
            parts.append(f"> {q}")
            parts.append("")
            word_count += count_words(q)
        elif roll < 0.70:
            # code block
            lang, code = rng.choice(CODE_BLOCKS)
            parts.append(f"```{lang}")
            parts.append(code.rstrip())
            parts.append("```")
            parts.append("")
            # code blocks don't count toward read time, but we want them present
        elif roll < 0.80:
            # horizontal rule
            parts.append("---")
            parts.append("")

    parts.append("")
    parts.append("## Final Thoughts")
    parts.append("")
    closer = " ".join(rng.choices(SENTENCES, k=6))
    parts.append(closer)
    parts.append("")
    word_count += count_words(closer)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Wrote {word_count} prose words to {OUT}")


if __name__ == "__main__":
    main()
