# Website Scripts

## sync_site_chrome.py

Single source for the site-wide header (nav) and footer. Every page carries a
static copy between `<!-- site-header:start/end -->` and
`<!-- site-footer:start/end -->` markers; edit the links or templates in the
script, then:

```bash
python scripts/sync_site_chrome.py          # rewrite all pages
python scripts/build_blog_index.py          # blog posts are generated from blog.html
python scripts/sync_site_chrome.py --check  # verify nothing drifted (exit 1 if so)
```

New top-level or `research/` pages are picked up automatically once they have
the markers (or a `<header class="site-header">` / `<footer class="site-footer">`
the script can replace); add other new pages to `PAGES` in the script.

---

## extract_metadata.py

Imports task classes from the installed `pyhealth` package and writes
`data/tasks.json`. Run this whenever a task class is added or renamed.

**Prerequisites:** `pyhealth` installed in your active Python environment.

```bash
# From the pyhealth.github.io repo root:
python scripts/extract_metadata.py

# Custom output path:
python scripts/extract_metadata.py --output data/tasks.json
```

Output goes to `data/tasks.json` by default.

---

### Workflow for adding a new task

1. Add the task class to `PyHealth/pyhealth/tasks/`.
2. Run the script to regenerate `data/tasks.json`.
3. Add one entry to `data/tasks_extra.json` (see format below).
4. Commit both JSON files — the site renders from them automatically.

---

### data/tasks.json (auto-generated, do not hand-edit)

Each entry is one Python class found in `pyhealth/tasks/`:

```json
{
  "class_name":    "MortalityPredictionMIMIC3",
  "task_name":     "MortalityPredictionMIMIC3",
  "description":   "Task for predicting mortality using MIMIC-III...",
  "input_schema":  {"conditions": "sequence", "procedures": "sequence"},
  "output_schema": {"mortality": "binary"},
  "output_type":   "binary",
  "source_file":   "pyhealth/tasks/mortality_prediction.py"
}
```

`output_type` is inferred from `output_schema` values. Classes that set their
schema dynamically in `__init__` will have `null` here — override via
`tasks_extra.json`.

---

### data/tasks_extra.json (hand-authored)

Controls which tasks appear on the site and in what order. Fields:

| Field           | Required | Description |
|----------------|----------|-------------|
| `class_name`    | Yes      | Python class name — used to join with `tasks.json` |
| `display_name`  | Yes      | Human-readable title shown on the card |
| `display_class` | No       | Short name shown in the code snippet (defaults to `class_name`) |
| `datasets`      | Yes      | Array of dataset pill labels, e.g. `["MIMIC-III"]` |
| `description`   | Yes      | One-sentence description for the card |
| `colab_url`     | No       | Colab notebook URL |
| `docs_url`      | No       | ReadTheDocs URL (defaults to the tasks index page) |
| `output_type`   | No       | Override auto-detected type (needed when schema is set in `__init__`) |

Minimal entry:

```json
{
  "class_name":   "MyNewTask",
  "display_name": "My New Task",
  "datasets":     ["MIMIC-IV"],
  "description":  "One sentence for the website card.",
  "colab_url":    "https://colab.research.google.com/drive/..."
}
```

---

### Testing locally

The site fetches JSON via `fetch()`, so it must be served over HTTP:

```bash
cd /path/to/pyhealth.github.io
python -m http.server 8080
# open http://localhost:8080/tasks.html
```

---

## build_blog_index.py (blog index + metadata)

This script scans the `blogs/` folder and writes the blog index used by the
site.

- **Input:** `blogs/YYYY-MM-DD/*.md` (uses the first `.md` file in each dated folder)
- **Output:** `data/blogs.json`
- **What it computes:** title/author (from frontmatter or `# ...`), preview text,
  `word_count`, and `read_time_min` (based on words-per-minute).

Run it whenever you:

- add a new blog post folder,
- rename the `.md` file inside a post folder,
- or change post content and want `preview` / `word_count` / `read_time_min` updated.

```bash
# From the pyhealth.github.io repo root:
python scripts/build_blog_index.py
```

### How blog pages render

- `blog_list.html` loads `data/blogs.json` to render the list.
- `blog.html?post=YYYY-MM-DD` loads `data/blogs.json` to find the markdown
  filename, then fetches `blogs/YYYY-MM-DD/<file>.md` and converts the Markdown
  to HTML in the browser.

---

## Previewing the blog locally

Because the site uses `fetch()`, preview via an HTTP server:

```bash
cd /path/to/pyhealth.github.io
python -m http.server 8080
# open http://localhost:8080/blog_list.html
```

To open a specific post:

- `http://localhost:8080/blog.html?post=YYYY-MM-DD`
