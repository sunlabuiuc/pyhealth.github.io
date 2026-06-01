# PyHealth Website

## Blog Workflow

### System Overview

Each blog post lives in its own folder under `blogs/`:

```
blogs/
└── YYYY-MM-DD-slug-title/
    ├── text.md       ← source (write this)
    └── index.html    ← auto-generated (do not hand-edit)
```

The build script reads all `blogs/*/text.md` files and produces:
- `data/blogs.json` — metadata index consumed by `blog_list.html`
- `blogs/{slug}/index.html` — per-post page with Open Graph meta tags for social sharing

### Frontmatter Fields

Every `text.md` should start with a YAML frontmatter block:

```markdown
---
title: "Your Post Title"
description: "One sentence shown in the blog list card and social previews."
author: "Your Name"
updated: "YYYY-MM-DD"
---
```

All fields are optional — the parser falls back to the first `# heading` for title, auto-extracts a preview from the first paragraph, and uses the file's modification time for the date. But explicit frontmatter gives you control and better social sharing.

---

## Adding a Post

### Option A — Manual

```bash
# 1. Create the folder
mkdir blogs/2026-05-30-my-post-title

# 2. Write the post
# Create blogs/2026-05-30-my-post-title/text.md with frontmatter + content

# 3. Rebuild the index
python scripts/build_blog_index.py

# 4. Preview locally
python -m http.server 8080
# open http://localhost:8080/blog_list.html
```

### Option B — From Rough Notes (Claude Workflow)

If you have rough scratch notes in any `.md` file (no formatting required), the
`blog-from-notes` workflow will convert them into a publication-ready post, save
it to the right folder, and rebuild the index — all in one step.

**Run it via the Claude Code Workflow panel or CLI:**

```
Workflow: blog-from-notes
args: {
  "notesPath": "/path/to/your/rough-notes.md",
  "slug": "2026-05-30-my-post-title"   ← optional; inferred from frontmatter if omitted
}
```

The workflow will:
1. Read your rough notes
2. Rewrite them as a polished post with proper frontmatter, headings, and prose
3. Save to `blogs/{slug}/text.md`
4. Run `python scripts/build_blog_index.py` automatically

---

## Previewing Locally

Because the site uses `fetch()`, you must serve it over HTTP (not open files directly):

```bash
cd /path/to/pyhealth.github.io
python -m http.server 8080
```

| Page | URL |
|------|-----|
| Blog list | http://localhost:8080/blog_list.html |
| Specific post | http://localhost:8080/blogs/YYYY-MM-DD-slug/ |

---

## Build Script Reference

See [scripts/README.md](scripts/README.md) for full documentation of all scripts.

**Quick reference:**

```bash
# Rebuild blog index (run after any post add/edit)
python scripts/build_blog_index.py

# Rebuild task metadata (unrelated to blogs)
python scripts/extract_metadata.py
```
