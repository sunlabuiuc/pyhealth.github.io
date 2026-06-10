"""
Merge PyHealth task metadata into a single data/tasks.json file.

Usage (from the pyhealth.github.io repo root):
    python scripts/extract_metadata.py
    python scripts/extract_metadata.py --output data/tasks.json

Requires pyhealth to be installed in the active Python environment.

Behaviour
---------
On each run the script:
  1. Reads the existing data/tasks.json (if present) as the source of truth for
     hand-authored fields (display_name, datasets, description, colab_url, etc.).
  2. Discovers every BaseTask subclass in pyhealth.tasks and extracts/infers the
     fields that come from code: input_schema, output_schema, output_type,
     modality, source_file, task_name.
  3. Updates every matching entry in the existing file with the freshly extracted
     code-derived fields, leaving hand-authored fields untouched.
  4. Appends auto-generated stub entries for any class not yet in the file.
  5. Writes the result back to tasks.json.

Hand-authored fields (preserved across runs):
    display_name  - Human-readable title shown on the card
    display_class - Short name used in the code snippet (defaults to class_name)
    description   - One-sentence card description (falls back to docstring)
    datasets      - Array of dataset pill labels, e.g. ["MIMIC-III"]
    colab_url     - Colab notebook URL
    docs_url      - ReadTheDocs URL
    output_type   - Override auto-inferred type (needed for dynamic schemas)
    modality      - Override auto-inferred modality list

Code-derived fields (always refreshed from the installed package):
    class_name    - Python class name
    task_name     - Value of the task_name class attribute
    input_schema  - {field: type} from the input_schema class attribute
    output_schema - {field: type} from the output_schema class attribute
    source_file   - Relative path within the pyhealth package
"""

import inspect
import json
import re
import argparse
from pathlib import Path

_DEFAULT_OUTPUT = Path(__file__).parent.parent / "data" / "tasks.json"

OUTPUT_TYPE_MAP = {
    "binary":     "binary",
    "multiclass": "multiclass",
    "multilabel": "multilabel",
    "regression": "regression",
}

SCHEMA_TO_MODALITY = {
    # EHR clinical codes (ICD, drugs, procedures)
    "sequence":             "ehr",
    "nested_sequence":      "ehr",
    "nested_floats":        "ehr",
    "deep_nested_sequence": "ehr",
    "deep_nested_floats":   "ehr",
    "stagenet":             "ehr",
    "multi_hot":            "ehr",
    # Timeseries / continuous measurements
    "timeseries":           "timeseries",
    "temporal_timeseries":  "timeseries",
    "stagenet_tensor":      "timeseries",
    # Raw tensor — defaults to timeseries (override via modality field when needed)
    "tensor":               "timeseries",
    # Medical images
    "image":                "image",
    "time_image":           "image",
    # Clinical text / NLP
    "text":                 "text",
    "tuple_time_text":      "text",
    # Biomedical waveforms (ECG, EEG)
    "signal":               "signal",
    # Audio (heart/lung sounds)
    "audio":                "audio",
    # Graph structures
    "graph":                "graph",
}


def _first_paragraph(docstring):
    if not docstring:
        return ""
    return docstring.strip().split("\n\n")[0].replace("\n", " ").strip()


def _serialize_schema(schema):
    """Convert a schema dict to a JSON-safe form (class references become their name)."""
    if not isinstance(schema, dict):
        return None
    return {
        k: (v.__name__ if inspect.isclass(v) else str(v))
        for k, v in schema.items()
    }


def _infer_modality(input_schema):
    """Return deduplicated, sorted list of modality labels from input_schema values."""
    if not isinstance(input_schema, dict):
        return []
    seen = set()
    result = []
    for v in input_schema.values():
        raw = v.__name__ if inspect.isclass(v) else str(v)
        key = raw.lower().replace("processor", "").split("(")[0].strip()
        mod = SCHEMA_TO_MODALITY.get(key)
        if mod and mod not in seen:
            seen.add(mod)
            result.append(mod)
    return sorted(result)


def _infer_output_type(output_schema):
    if not isinstance(output_schema, dict):
        return None
    for val in output_schema.values():
        name = val.__name__ if inspect.isclass(val) else str(val)
        mapped = OUTPUT_TYPE_MAP.get(name.lower())
        if mapped:
            return mapped
    return None


def _relative_source(cls):
    try:
        abs_path = Path(inspect.getfile(cls))
        parts = abs_path.parts
        idx = next((i for i, p in enumerate(parts) if p == "pyhealth"), None)
        return str(Path(*parts[idx:])) if idx is not None else abs_path.name
    except (TypeError, StopIteration):
        return None


def _humanize(class_name):
    """Convert a CamelCase class name into a readable display name."""
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", class_name)   # camelCase split
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", s)          # acronym split
    return s.strip()


def _discover_classes():
    """Return {class_name: auto_fields} for all BaseTask subclasses in pyhealth.tasks."""
    from pyhealth.tasks import BaseTask
    import pyhealth.tasks as tasks_module

    found = {}
    for name, cls in inspect.getmembers(tasks_module, inspect.isclass):
        if cls is BaseTask or not issubclass(cls, BaseTask):
            continue
        input_schema  = getattr(cls, "input_schema",  None)
        output_schema = getattr(cls, "output_schema", None)
        found[name] = {
            "class_name":    name,
            "task_name":     getattr(cls, "task_name", name),
            "_docstring":    _first_paragraph(cls.__doc__),
            "input_schema":  _serialize_schema(input_schema),
            "output_schema": _serialize_schema(output_schema),
            "_inferred_output_type": _infer_output_type(output_schema),
            "_inferred_modality":    _infer_modality(input_schema),
            "source_file":   _relative_source(cls),
        }
    return found


def merge_tasks(existing, discovered):
    """
    Merge discovered class data into the existing entry list.

    For each existing entry:
      - Refresh code-derived fields from discovered (if the class is in the package).
      - Preserve all hand-authored fields.
      - If a hand-authored field is empty/null, fill it from the auto-detected value.

    For classes in discovered but not yet in existing:
      - Append a new stub entry with auto-derived defaults.

    Returns the updated list (existing order preserved, new entries appended).
    """
    existing_class_names = {e["class_name"] for e in existing}
    updated = []

    for entry in existing:
        cn = entry["class_name"]
        auto = discovered.get(cn)
        if auto is None:
            # Class not found in the installed package — preserve as-is.
            updated.append(entry)
            continue

        new_entry = dict(entry)

        # Always refresh from code
        new_entry["task_name"]     = auto["task_name"]
        new_entry["input_schema"]  = auto["input_schema"]
        new_entry["output_schema"] = auto["output_schema"]
        new_entry["source_file"]   = auto["source_file"]

        # Fill from code only when the hand-authored field is absent/empty
        if not new_entry.get("description"):
            new_entry["description"] = auto["_docstring"]
        if not new_entry.get("output_type"):
            new_entry["output_type"] = auto["_inferred_output_type"]
        if not new_entry.get("modality"):
            new_entry["modality"] = auto["_inferred_modality"]

        updated.append(new_entry)

    # Append stubs for classes not yet in the file
    for name, auto in sorted(discovered.items()):
        if name in existing_class_names:
            continue
        updated.append({
            "class_name":    name,
            "display_name":  _humanize(name),
            "display_class": None,
            "task_name":     auto["task_name"],
            "description":   auto["_docstring"],
            "datasets":      [],
            "input_schema":  auto["input_schema"],
            "output_schema": auto["output_schema"],
            "output_type":   auto["_inferred_output_type"],
            "modality":      auto["_inferred_modality"],
            "source_file":   auto["source_file"],
            "colab_url":     None,
            "docs_url":      None,
            "example_url":   None,
        })

    return updated


def main():
    parser = argparse.ArgumentParser(
        description="Merge PyHealth task metadata into data/tasks.json."
    )
    parser.add_argument(
        "--output",
        default=str(_DEFAULT_OUTPUT),
        help="Path to tasks.json (default: data/tasks.json relative to this repo)",
    )
    args = parser.parse_args()
    output_path = Path(args.output)

    # Load existing file (source of truth for hand-authored fields)
    existing = []
    if output_path.exists():
        existing = json.loads(output_path.read_text())

    try:
        discovered = _discover_classes()
    except ImportError as e:
        raise SystemExit(
            f"Could not import pyhealth: {e}\n"
            "Make sure pyhealth is installed in your active Python environment."
        )

    tasks = merge_tasks(existing, discovered)

    n_new = sum(1 for t in tasks if t["class_name"] not in {e["class_name"] for e in existing})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(tasks, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(tasks)} tasks to {output_path}  ({n_new} new)")


if __name__ == "__main__":
    main()
