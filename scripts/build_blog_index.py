import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOGS_DIR = ROOT / "blogs"
OUTPUT_FILE = ROOT / "data" / "blogs.json"

MD_HEADER_RE = re.compile(r"^#\s+(.*)", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"^---\s*$(.*?)^---\s*$", re.MULTILINE | re.DOTALL)
FIELD_RE = re.compile(r"^(title|author):\s*(.*)$", re.MULTILINE | re.IGNORECASE)


def parse_frontmatter(text: str) -> dict[str, str]:
    frontmatter = FRONTMATTER_RE.search(text)
    if not frontmatter:
        return {}

    fields: dict[str, str] = {}
    for match in FIELD_RE.finditer(frontmatter.group(1)):
        fields[match.group(1).lower()] = match.group(2).strip().strip('"\'')
    return fields


def infer_title(text: str, filename: str) -> str:
    fields = parse_frontmatter(text)
    if title := fields.get('title'):
        return title

    header_match = MD_HEADER_RE.search(text)
    if header_match:
        return header_match.group(1).strip()

    return filename.replace('-', ' ').replace('_', ' ').title()


def main() -> None:
    if not BLOGS_DIR.exists():
        raise SystemExit(f"Blogs directory not found: {BLOGS_DIR}")

    blog_files = sorted(BLOGS_DIR.glob('*.md'))
    blogs = []

    for path in blog_files:
        text = path.read_text(encoding='utf-8')
        fields = parse_frontmatter(text)
        title = fields.get('title') or infer_title(text, path.stem)
        blogs.append({
            'id': path.stem,
            'title': title,
            'author': fields.get('author', ''),
            'url': f'blog.html?post={path.stem}',
        })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(blogs, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"Wrote {len(blogs)} blog entries to {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
