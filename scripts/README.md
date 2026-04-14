# Website Scripts

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
