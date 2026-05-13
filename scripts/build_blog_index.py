import json
import math
import re
from datetime import datetime
from pathlib import Path

FOLDER_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")
WORDS_PER_MINUTE = 238

ROOT = Path(__file__).resolve().parent.parent
BLOGS_DIR = ROOT / "blogs"
OUTPUT_FILE = ROOT / "data" / "blogs.json"

MD_HEADER_RE = re.compile(r"^#\s+(.*)", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"^---\s*$(.*?)^---\s*$", re.MULTILINE | re.DOTALL)
FIELD_RE = re.compile(r"^(title|author|description):\s*(.*)$", re.MULTILINE | re.IGNORECASE)
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


def count_words(text: str) -> int:
    text = FRONTMATTER_RE.sub('', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`[^`]+`', '', text)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[#>*_~`\-]+', ' ', text)
    words = re.findall(r"\b\w[\w'-]*\b", text)
    return len(words)


def folder_last_modified(folder: Path) -> float:
    latest = folder.stat().st_mtime
    for child in folder.rglob('*'):
        try:
            latest = max(latest, child.stat().st_mtime)
        except OSError:
            continue
    return latest


def parse_folder_date(folder_name: str) -> tuple[str, str]:
    match = FOLDER_DATE_RE.match(folder_name)
    if not match:
        return '', ''
    iso = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    try:
        display = datetime.strptime(iso, "%Y-%m-%d").strftime("%b %d, %Y").replace(" 0", " ")
    except ValueError:
        display = iso
    return iso, display


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
        description = (fields.get('description') or '').strip()
        preview = description if description else extract_preview(text)
        
        date_iso, date_display = parse_folder_date(blog_dir.name)
        last_updated_iso = datetime.fromtimestamp(folder_last_modified(blog_dir)).isoformat(timespec='seconds')
        word_count = count_words(text)
        read_time_min = max(1, math.ceil(word_count / WORDS_PER_MINUTE)) if word_count else 0

        blogs.append({
            'id': blog_dir.name,
            'title': title,
            'author': fields.get('author', ''),
            'preview': preview,
            'date': date_iso,
            'date_display': date_display,
            'last_updated': last_updated_iso,
            'word_count': word_count,
            'read_time_min': read_time_min,
            'file': path.name,
            'url': f'blog.html?post={blog_dir.name}',
        })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(blogs, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f"Wrote {len(blogs)} blog entries to {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
