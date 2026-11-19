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
    dataset_classes - pyhealth.datasets classes the docstring cites with
                    :class:`~pyhealth.datasets.X` (drives dataset links)
"""

import inspect
import json
import re
import argparse
from pathlib import Path

_DEFAULT_OUTPUT = Path(__file__).parent.parent / "data" / "tasks.json"
_DATASET_REF = re.compile(r":class:`~?pyhealth\.datasets\.(\w+)`")

# Keys are the names processors register under (pyhealth.processors); a
# processor given as a class is looked up by the name its class registered.
OUTPUT_TYPE_MAP = {
    "binary":                "binary",
    "timeseries_binary":     "binary",
    "multiclass":            "multiclass",
    "timeseries_multiclass": "multiclass",
    "multilabel":            "multilabel",
    "timeseries_multilabel": "multilabel",
    "regression":            "regression",
    "timeseries_regression": "regression",
    "image_mask_dir":        "segmentation",
}

SCHEMA_TO_MODALITY = {
    # EHR clinical codes (ICD, drugs, procedures) and event timelines
    "sequence":                    "ehr",
    "sequence_v2":                 "ehr",
    "jagged":                      "ehr",
    "nested_sequence":             "ehr",
    "nested_sequence_floats":      "ehr",
    "deep_nested_sequence":        "ehr",
    "deep_nested_sequence_floats": "ehr",
    "stagenet":                    "ehr",
    "multi_hot":                   "ehr",
    "nested_multihot":             "ehr",
    "cehr":                        "ehr",
    "ethos":                       "ehr",
    "ethos_context":               "ehr",
    # Timeseries / continuous measurements
    "timeseries":                  "timeseries",
    "temporal_timeseries":         "timeseries",
    "stagenet_tensor":             "timeseries",
    # Medical images and volumes
    "image":                       "image",
    "time_image":                  "image",
    "time_region_image":           "image",
    "dicom":                       "image",
    "dicom_series":                "image",
    "nifti":                       "image",
    "image_mask_dir":              "image",
    # Clinical text / NLP
    "text":                        "text",
    "tuple_time_text":             "text",
    # Biomedical waveforms (ECG, EEG)
    "signal":                      "signal",
    # Audio (heart/lung sounds)
    "audio":                       "audio",
    # Graph structures
    "graph":                       "graph",
}

# Processors that say nothing about the modality: plain arrays and values
# (an input using one takes its modality from the task's dataset), labels, and
# fields to skip.
NO_MODALITY = {"tensor", "raw", "ignore"} | set(OUTPUT_TYPE_MAP) - {"image_mask_dir"}

# A dataset's modality (data/datasets.json) as a task modality.
DATASET_TO_MODALITY = {
    "ehr": "ehr", "signal": "signal", "image": "image",
    "genomics": "genomics", "text": "text",
}


def _first_paragraph(docstring):
    if not docstring:
        return ""
    return docstring.strip().split("\n\n")[0].replace("\n", " ").strip()


def _registered_names():
    """{processor class: name it registered under} from pyhealth.processors."""
    from pyhealth.processors import PROCESSOR_REGISTRY
    return {cls: name for name, cls in PROCESSOR_REGISTRY.items()}


def _serialize_schema(schema, registered):
    """
    Convert a schema dict to a JSON-safe form: each value becomes the name its
    processor registered under, or the class name for an unregistered class.
    """
    if not isinstance(schema, dict):
        return None
    def _name(v):
        # Processor specs may be ("image", {...kwargs}) tuples; keep the type.
        if isinstance(v, tuple) and v:
            v = v[0]
        if not inspect.isclass(v):
            return str(v)
        # A subclass of a registered processor (e.g. one that tolerates
        # missing images) counts as that processor.
        return next((registered[c] for c in v.__mro__ if c in registered), v.__name__)

    return {k: _name(v) for k, v in schema.items()}


def _infer_modality(input_schema, dataset_modalities=()):
    """
    Sorted modality labels for the input_schema values. An input whose
    processor names no modality (e.g. a tensor) holds data of the kind its
    dataset has, so it adds the modalities of the task's datasets.
    """
    names = [n for n in (input_schema or {}).values() if n != "ignore"]
    result = {SCHEMA_TO_MODALITY[n] for n in names if n in SCHEMA_TO_MODALITY}
    if not names or any(n not in SCHEMA_TO_MODALITY for n in names):
        result |= {DATASET_TO_MODALITY[m] for m in dataset_modalities if m in DATASET_TO_MODALITY}
    return sorted(result)


def _infer_output_type(output_schema):
    for name in (output_schema or {}).values():
        if name in OUTPUT_TYPE_MAP:
            return OUTPUT_TYPE_MAP[name]
    return None


def _schemas(cls):
    """
    (input_schema, output_schema) of a task class. Tasks that set them in
    __init__ are read from a default instance, when one can be made.
    """
    input_schema = getattr(cls, "input_schema", None)
    output_schema = getattr(cls, "output_schema", None)
    if isinstance(input_schema, dict) and isinstance(output_schema, dict):
        return input_schema, output_schema
    try:
        task = cls()
    except Exception:  # needs arguments; keep what the class has
        return input_schema, output_schema
    return getattr(task, "input_schema", None), getattr(task, "output_schema", None)


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
    import pyhealth.datasets as datasets_module

    # Docstrings also cite helpers such as PatientSplit; keep only datasets.
    dataset_bases = tuple(getattr(datasets_module, name) for name in
                          ("BaseDataset", "BaseEHRDataset", "BaseSignalDataset")
                          if hasattr(datasets_module, name))

    def is_dataset(name):
        cls = getattr(datasets_module, name, None)
        return inspect.isclass(cls) and issubclass(cls, dataset_bases)

    registered = _registered_names()
    found = {}
    for name, cls in inspect.getmembers(tasks_module, inspect.isclass):
        if cls is BaseTask or not issubclass(cls, BaseTask):
            continue
        input_schema, output_schema = _schemas(cls)
        found[name] = {
            "class_name":    name,
            "task_name":     getattr(cls, "task_name", name),
            "_docstring":    _first_paragraph(cls.__doc__),
            "input_schema":  _serialize_schema(input_schema, registered),
            "output_schema": _serialize_schema(output_schema, registered),
            "source_file":   _relative_source(cls),
            "dataset_classes": sorted({name for name in _DATASET_REF.findall(cls.__doc__ or "")
                                       if is_dataset(name)}),
        }
    return found


def _classify(entry, dataset_modality):
    """
    Refresh output_type and modality from the entry's schemas. The values the
    rules gave last time are kept in "inferred"; a field that still equals them
    (or is empty) was never set by hand and takes the new value, while a hand
    edit is kept.
    """
    inferred = {
        "output_type": _infer_output_type(entry.get("output_schema")),
        "modality": _infer_modality(
            entry.get("input_schema"),
            [dataset_modality.get(cls) for cls in entry.get("dataset_classes", [])],
        ),
    }
    previous = entry.get("inferred", {})
    for field, value in inferred.items():
        if not entry.get(field) or entry[field] == previous.get(field):
            entry[field] = value
    entry["inferred"] = inferred


def merge_tasks(existing, discovered, dataset_modality=None):
    """
    Merge discovered class data into the existing entry list.

    For each existing entry:
      - Refresh code-derived fields from discovered (if the class is in the package).
      - Preserve all hand-authored fields.
      - Fill an empty description from the docstring, and refresh output_type
        and modality unless they were set by hand (see _classify).

    For classes in discovered but not yet in existing:
      - Append a new stub entry with auto-derived defaults.

    dataset_modality maps dataset classes to their data/datasets.json modality,
    for tasks whose inputs don't name one.

    Returns the updated list (existing order preserved, new entries appended).
    """
    dataset_modality = dataset_modality or {}
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
        # Schemas a task sets only when given arguments can't be read; keep the
        # previously recorded schema rather than overwriting it with null.
        if auto["input_schema"] is not None:
            new_entry["input_schema"] = auto["input_schema"]
        if auto["output_schema"] is not None:
            new_entry["output_schema"] = auto["output_schema"]
        new_entry["source_file"]   = auto["source_file"]
        new_entry["dataset_classes"] = auto["dataset_classes"]

        # Fill from code only when the hand-authored field is absent/empty
        if not new_entry.get("description"):
            new_entry["description"] = auto["_docstring"]
        _classify(new_entry, dataset_modality)

        updated.append(new_entry)

    # Append stubs for classes not yet in the file
    for name, auto in sorted(discovered.items()):
        if name in existing_class_names:
            continue
        entry = {
            "class_name":    name,
            "display_name":  _humanize(name),
            "display_class": None,
            "task_name":     auto["task_name"],
            "description":   auto["_docstring"],
            "datasets":      [],
            "input_schema":  auto["input_schema"],
            "output_schema": auto["output_schema"],
            "output_type":   None,
            "modality":      [],
            "source_file":   auto["source_file"],
            "dataset_classes": auto["dataset_classes"],
            "colab_url":     None,
            "docs_url":      None,
            "example_url":   None,
        }
        _classify(entry, dataset_modality)
        updated.append(entry)

    return updated


def unmapped_processors():
    """Registered processor names neither table covers, to add to one of them."""
    from pyhealth.processors import PROCESSOR_REGISTRY
    return sorted(set(PROCESSOR_REGISTRY) - set(SCHEMA_TO_MODALITY) - NO_MODALITY)


def main():
    parser = argparse.ArgumentParser(
        description="Merge PyHealth task metadata into data/tasks.json."
    )
    parser.add_argument(
        "--output",
        default=str(_DEFAULT_OUTPUT),
        help="Path to tasks.json (default: data/tasks.json relative to this repo)",
    )
    parser.add_argument("--summary", help="Also append the new tasks, as Markdown, to this file")
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

    datasets_path = output_path.parent / "datasets.json"
    datasets = json.loads(datasets_path.read_text()) if datasets_path.exists() else {}
    dataset_modality = {cls: info.get("modality") for cls, info in datasets.items()}
    tasks = merge_tasks(existing, discovered, dataset_modality)
    unmapped = unmapped_processors()

    new = [t for t in tasks if t["class_name"] not in {e["class_name"] for e in existing}]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(tasks, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(tasks)} tasks to {output_path}  ({len(new)} new)")
    if unmapped:
        print("Processors with no modality yet (add them to SCHEMA_TO_MODALITY "
              "or NO_MODALITY):", ", ".join(unmapped))
    if args.summary and (new or unmapped):
        with open(args.summary, "a", encoding="utf-8") as f:
            if new:
                f.write(f"**New task cards ({len(new)})**, filled in from docstrings:\n")
                f.writelines(f"- `{t['class_name']}`: {t['output_type'] or 'no output type'}, "
                             f"{', '.join(t['modality']) or 'no modality'}; works with "
                             f"{', '.join(t['dataset_classes']) or 'no dataset cited'}\n"
                             for t in new)
                f.write("\n")
            if unmapped:
                f.write("**Processors with no modality yet**: "
                        + ", ".join(f"`{name}`" for name in unmapped)
                        + ". Add each to `SCHEMA_TO_MODALITY` or `NO_MODALITY` in "
                        "`scripts/extract_metadata.py`.\n\n")


if __name__ == "__main__":
    main()
