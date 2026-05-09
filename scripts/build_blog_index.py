import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOGS_DIR = ROOT / "blogs"
OUTPUT_FILE = ROOT / "data" / "blogs.json"

MD_HEADER_RE = re.compile(r"^#\s+(.*)", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"^---\s*$(.*?)^---\s*$", re.MULTILINE | re.DOTALL)
FIELD_RE = re.compile(r"^(title|author):\s*(.*)$", re.MULTILINE | re.IGNORECASE)
MARKDOWN_CLEAN_RE = re.compile(r'(\*\*|\*|~~|`|\[.*?\]\(.*?\)|!\[.*?\]\(.*?\)|<.*?>|#{1,6}\s*)', re.MULTILINE)


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


def extract_preview(text: str) -> str:
    # Remove frontmatter
    frontmatter_match = FRONTMATTER_RE.search(text)
    if frontmatter_match:
        content = text[frontmatter_match.end():]
    else:
        content = text
    
    # Split into lines and filter out headings
    lines = content.split('\n')
    non_heading_lines = [line for line in lines if not line.strip().startswith('#')]
    
    # Join back and clean markdown formatting
    content_text = '\n'.join(non_heading_lines)
    clean_text = MARKDOWN_CLEAN_RE.sub('', content_text)
    
    # Split into words and take first 25
    words = clean_text.split()
    preview_words = words[:25]
    preview = ' '.join(preview_words)
    
    # Add ellipsis if truncated
    if len(words) > 25:
        preview += '...'
    
    return preview.strip()


def main() -> None:
    if not BLOGS_DIR.exists():
        raise SystemExit(f"Blogs directory not found: {BLOGS_DIR}")

    # Get all subdirectories in blogs folder
    blog_dirs = sorted([d for d in BLOGS_DIR.iterdir() if d.is_dir()])
    blogs = []

    for blog_dir in blog_dirs:
        # Find markdown files in each blog directory
        md_files = sorted(blog_dir.glob('*.md'))
        
        if not md_files:
            print(f"Warning: No markdown files found in {blog_dir.name}")
            continue
        
        # Use the first markdown file found
        path = md_files[0]
        text = path.read_text(encoding='utf-8')
        fields = parse_frontmatter(text)
        title = fields.get('title') or infer_title(text, path.stem)
        preview = extract_preview(text)
        
        blogs.append({
            'id': blog_dir.name,
            'title': title,
            'author': fields.get('author', ''),
            'preview': preview,
            'file': path.name,
            'url': f'blog.html?post={blog_dir.name}',
        })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(blogs, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"Wrote {len(blogs)} blog entries to {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
