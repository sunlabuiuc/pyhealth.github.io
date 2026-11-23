# Website Scripts

## Keeping tasks and datasets in step with PyHealth

`.github/workflows/sync-pyhealth.yml` runs every night at 09:00 UTC; to run it
now, go to Actions > Sync from PyHealth > Run workflow. It installs PyHealth
master, runs `extract_metadata.py` and `extract_datasets.py`, and checks the
result with `check_site_consistency.py`. If `data/tasks.json` or
`data/datasets.json` changed, it opens a PR, or updates the one already open,
on the branch `bot/sync-pyhealth`. The PR body lists the new cards and
anything that needs a person to look at it.

New classes arrive as stub cards written from their docstrings. To review:
1. Read the new cards locally (see "Testing locally" below) and merge.
2. Polish the stub text on main in a normal PR. The next run rebuilds the bot
   branch from main, so edits pushed to the bot branch are lost, but edits
   on main are kept.

The workflow needs "Allow GitHub Actions to create and approve pull requests"
turned on under Settings > Actions > General.

**Auto-merge.** Set the repository variable `SYNC_AUTO_MERGE` to `true`
(Settings > Secrets and variables > Actions > Variables). After that, a run
whose site check passes commits straight to main, and GitHub Pages deploys it.
A run with no changes does nothing. A run whose check fails still opens a PR,
so a person sees the problem. Delete the variable to go back to PRs.

To run the same thing by hand, from the repo root with PyHealth installed:

```bash
python scripts/extract_metadata.py
python scripts/extract_datasets.py
python scripts/check_site_consistency.py --pyhealth ../PyHealth
```

Both generators take `--summary FILE` to append a Markdown report.

---

## extract_bounties.py

Writes `data/bounties.json`, which the homepage bounty section and
`bounties.html` render, from PyHealth's `bounty.yaml` and the PRs whose titles
carry `[BTY-<id>]` or `[Bounty-<id>]`. The rules match PyHealth's
`tools/update_bounty_board.py`: a bounty is complete once a claiming PR merges
or `complete` is set in `bounty.yaml`, and its credit is the `complete` text or
else the merged PRs' authors. Email addresses are never written.

```bash
python scripts/extract_bounties.py                     # GitHub API (public data)
python scripts/extract_bounties.py --prs-file prs.json # offline
python scripts/extract_bounties.py --no-prs            # bounty.yaml only
```

The file is regenerated, never hand-edited. To change a bounty or its credit,
edit `bounty.yaml` in PyHealth.

---

## extract_metadata.py

Imports task classes from the installed `pyhealth` package and updates
`data/tasks.json`.

**Prerequisites:** `pyhealth` installed in your active Python environment.

```bash
# From the pyhealth.github.io repo root:
python scripts/extract_metadata.py

# Custom output path:
python scripts/extract_metadata.py --output data/tasks.json
```

---

### data/tasks.json

One entry per task class in `pyhealth.tasks`; tasks.html renders a card for
each. Rerunning the script refreshes the fields that come from code and adds a
stub entry for each new class. Hand-edited fields are kept.

```json
{
  "class_name":    "MortalityPredictionMIMIC3",
  "display_name":  "Mortality Prediction (MIMIC-III)",
  "task_name":     "MortalityPredictionMIMIC3",
  "description":   "Task for predicting mortality using MIMIC-III...",
  "input_schema":  {"conditions": "sequence", "procedures": "sequence"},
  "output_schema": {"mortality": "binary"},
  "output_type":   "binary",
  "modality":      ["ehr"],
  "inferred":      {"output_type": "binary", "modality": ["ehr"]},
  "source_file":   "pyhealth/tasks/mortality_prediction.py",
  "dataset_classes": ["MIMIC3Dataset"]
}
```

**Refreshed from code on every run:** `task_name`, `input_schema`,
`output_schema`, `source_file`, `dataset_classes`.

**Hand-edited, never overwritten:**
- `display_name`
- `display_class`
- `description` (filled from the docstring when empty)
- `datasets`
- `colab_url`
- `docs_url`
- `example_url`

**Classified from code unless set by hand:** `output_type` and `modality`.
The script reads them off the schemas, after naming each processor by the name
it registered under in `pyhealth.processors` (so `MultiHotProcessor` counts as
`multi_hot`):

- `output_type` is the first `output_schema` value in `OUTPUT_TYPE_MAP`:
  `binary`, `multiclass`, `multilabel`, `regression` (and their `timeseries_`
  forms), or `image_mask_dir` for `segmentation`. Otherwise it stays `null`,
  which the page shows as "Other".
- `modality` is every `SCHEMA_TO_MODALITY` value among the `input_schema`
  values. Inputs such as `tensor` and `raw` (listed in `NO_MODALITY`) hold
  whatever the dataset holds, so they add the `datasets.json` modality of each
  dataset in `dataset_classes`.

Schemas a task sets in `__init__` are read from a default instance; a task that
needs arguments keeps the schema last recorded.

`inferred` holds the values the rules gave on the last run. A field equal to
them (or empty) is refreshed, so better rules reach it; a field you changed by
hand differs from them and is kept. To classify a task by hand, edit
`output_type` or `modality` and leave `inferred` alone. No schema says a task
recommends, generates or models survival, so set `recommend`, `generative` or
`survival` by hand.

When PyHealth registers a processor neither table covers, the run lists it in
its summary; add it to `SCHEMA_TO_MODALITY` or `NO_MODALITY`.

`dataset_classes` lists the `pyhealth.datasets` classes that the task's
docstring cites as ``:class:`~pyhealth.datasets.X` ``. PyHealth task docstrings
say "Works with :class:`~pyhealth.datasets.X`." tasks.html turns these into
dataset pills that link to `datasets.html#X`, and datasets.html lists each
dataset's tasks from them. A task whose docstring cites no dataset gets no
pills.

---

## extract_datasets.py

Imports dataset classes from the installed `pyhealth` package and adds a stub
entry to `data/datasets.json` for each class the site doesn't list yet.

```bash
python scripts/extract_datasets.py
```

Existing entries are hand-checked and never changed. A stub is filled in from
the dataset docstring's "Getting the data:" block (Source, Access,
No access yet?) and its first paragraph. A stub's modality is guessed from the
description, and set to `other` when nothing matches. The new entry goes after
the last entry with the same modality.

The script only reports, and does not change:
- entries whose class is no longer exported;
- entries whose docstring now cites a different source URL than the site.

---

### data/datasets.json

One entry per `pyhealth.datasets` class, keyed by class name, in page order.
datasets.html renders a card for each entry that has no `anchor`, and
tasks.html uses `label` for its dataset pills. The access facts match the
"Getting the data" section of each dataset's docstring in PyHealth.

| Field         | Description |
|---------------|-------------|
| `label`       | Short pill label, e.g. `"MIMIC-III"` |
| `modality`    | `ehr`, `signal`, `image`, `genomics`, `text` or `other`; sets the tag and the filter |
| `description` | One or two sentences for the card |
| `snippet`     | Plain-text Python example; highlighted when the page renders |
| `access`      | `open`, `restricted`, `credentialed`, or `format` |
| `access_note` | One line on what access takes (the page adds the period) |
| `source_url`  | Where to download it; with no `source_url`, the card has no access line |
| `demo_label`, `demo_url` | Optional open demo or subset |
| `docs_url`    | Optional; defaults to `api/datasets/pyhealth.datasets.<Class>.html` |
| `example_url` | Optional "Example →" link |
| `anchor`      | Card to link to instead, for a class with no card of its own |

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
