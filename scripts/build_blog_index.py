import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOGS_DIR = ROOT / "blogs"
OUTPUT_FILE = ROOT / "data" / "blogs.json"

MD_HEADER_RE = re.compile(r"^#\s+(.*)", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"^---\s*$(.*?)^---\s*$", re.MULTILINE | re.DOTALL)
TITLE_RE = re.compile(r"^title:\s*(.*)$", re.MULTILINE | re.IGNORECASE)


def infer_title(text: str, filename: str) -> str:
    frontmatter = FRONTMATTER_RE.search(text)
    if frontmatter:
        fm_text = frontmatter.group(1)
        title_match = TITLE_RE.search(fm_text)
        if title_match:
            return title_match.group(1).strip().strip('"\'')

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
        title = infer_title(text, path.stem)
        blogs.append({
            'id': path.stem,
            'title': title,
            'url': f'blog.html?post={path.stem}',
        })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(blogs, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"Wrote {len(blogs)} blog entries to {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
