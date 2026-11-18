"""
Add a data/datasets.json entry (and so a datasets.html card) for every PyHealth
dataset class the site doesn't list yet.

Usage (from the pyhealth.github.io repo root):
    python scripts/extract_datasets.py
    python scripts/extract_datasets.py --summary body.md

Requires pyhealth to be installed in the active Python environment.

Behaviour
---------
On each run the script:
  1. Reads data/datasets.json. Every existing entry is hand-checked and is
     never changed.
  2. Discovers every dataset class exported by pyhealth.datasets.
  3. Appends a stub entry for each class not yet in the file, filled from its
     docstring (see below), after the last entry with the same modality.
  4. Reports, without changing anything, entries whose class is no longer
     exported and entries whose docstring now cites a different source URL.
  5. Writes the file and prints a summary (also to --summary, as Markdown).

Stub fields come from the docstring's "Getting the data:" block, which
PyHealth dataset docstrings carry:

    Getting the data:
        - Source: https://physionet.org/content/eicu-crd/2.0/
        - Access: credentialed. Create a PhysioNet account, ...
        - Download: ...
        - ``root``: the folder holding ``patient.csv.gz`` ...
        - No access yet? ... https://physionet.org/content/eicu-crd-demo/2.0.1/

    source_url  - first URL in Source
    access      - first word of Access (open / restricted / credentialed)
    access_note - first sentence of the rest of Access
    demo_url    - URL in "No access yet?"
    description - first paragraph of the docstring
    snippet     - a minimal constructor call with root=...
    modality    - guessed from the description (ehr / signal / image /
                  genomics / text), else "other"

Review stub text before merging; it is a starting point, not copy.
"""

import argparse
import inspect
import json
import re
from pathlib import Path

_DEFAULT_OUTPUT = Path(__file__).parent.parent / "data" / "datasets.json"
_URL = re.compile(r"https?://[^\s)>`'\"]+[^\s)>`'\".,;]")

# Bases and helpers pyhealth.datasets exports that are not datasets to download.
_NOT_DATASETS = {
    "BaseDataset", "BaseEHRDataset", "BaseSignalDataset", "PatchDataset",
    "SampleDataset", "SampleEHRDataset", "SampleSignalDataset",
}

# Words in Access that mean "sign up or agree, but no credentialing".
_ACCESS = {
    "open": "open", "public": "open",
    "restricted": "restricted", "free": "restricted", "registration": "restricted",
    "credentialed": "credentialed",
}

# First match wins, so the more specific modalities come first.
_MODALITY_WORDS = [
    ("signal", r"\b(EEG|ECG|EKG|PSG|polysomnograph\w*|sleep|biosignal|waveform|heart sound)"),
    ("image", r"\b(image|imaging|X-?ray|radiograph\w*|CT|MRI|segmentation)\b"),
    ("genomics", r"\b(genom\w*|mutation\w*|variant\w*|gene)\b"),
    ("text", r"\b(clinical notes?|text|transcription\w*|reports?)\b"),
    ("ehr", r"\b(EHR|electronic health|ICU|admission\w*|patients?|survival|cohort)\b"),
]


def _first_paragraph(docstring):
    if not docstring:
        return ""
    return docstring.strip().split("\n\n")[0].replace("\n", " ").strip()


def _getting_the_data(docstring):
    """{item: text} for the bullets under "Getting the data:", or {}."""
    lines = (docstring or "").splitlines()
    start = next((i for i, line in enumerate(lines)
                  if line.strip() == "Getting the data:"), None)
    if start is None:
        return {}
    indent = len(lines[start]) - len(lines[start].lstrip())
    items, key = {}, None
    for line in lines[start + 1:]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        text = line.strip()
        bullet = re.match(r"- (Source|Access|Download|``\w+``|No access yet\?):?\s*(.*)", text)
        if bullet:
            key = bullet.group(1).rstrip("?").strip("`")
            items[key] = bullet.group(2)
        elif key and text:
            items[key] += " " + text
    return items


def _access(text):
    """(access, access_note) from the Access bullet."""
    word, _, rest = text.partition(" ")
    access = _ACCESS.get(word.strip(".,;:").lower())
    if access is None:  # e.g. "Access: free registration" or prose
        return None, text
    note = re.sub(r"\s*\(https?://[^)]*\)", "", rest)  # drop parenthesized links
    note = re.split(r"(?<=\.)\s", note.strip())[0].rstrip(".")
    return access, note[:1].upper() + note[1:]


def _modality(text):
    for modality, pattern in _MODALITY_WORDS:
        if re.search(pattern, text, re.I):
            return modality
    return "other"


def _snippet(class_name):
    folder = re.sub(r"Dataset$", "", class_name).lower() or class_name.lower()
    return (f"from pyhealth.datasets import {class_name}\n"
            f"dataset = {class_name}(\n"
            f"    root=\"data/{folder}/\",\n"
            f")")


def _discover_classes():
    """Return {class_name: docstring} for every dataset class pyhealth.datasets exports."""
    import pyhealth.datasets as datasets_module

    bases = tuple(getattr(datasets_module, name) for name in
                  ("BaseDataset", "BaseEHRDataset", "BaseSignalDataset")
                  if hasattr(datasets_module, name))
    return {
        name: inspect.getdoc(cls) or ""
        for name, cls in inspect.getmembers(datasets_module, inspect.isclass)
        if issubclass(cls, bases) and name not in _NOT_DATASETS
    }


def stub_entry(class_name, docstring):
    """A datasets.json entry for a class the site doesn't list yet."""
    block = _getting_the_data(docstring)
    description = _first_paragraph(docstring)
    entry = {
        "label": re.sub(r"Dataset$", "", class_name) or class_name,
        "modality": _modality(description),
        "description": description,
        "snippet": _snippet(class_name),
    }
    source = _URL.search(block.get("Source", ""))
    if source:
        entry["source_url"] = source.group(0)
        access, note = _access(block.get("Access", ""))
        entry["access"] = access or "restricted"
        entry["access_note"] = note or "See the source for how to get access"
    demo = _URL.search(block.get("No access yet", ""))
    if demo:
        entry["demo_label"] = "open demo"
        entry["demo_url"] = demo.group(0)
    return entry


def merge_datasets(existing, discovered):
    """
    Return (merged, report). Existing entries are kept as they are; each new
    class goes in after the last entry with the same modality (or at the end).
    report lists what was added and what a person should look at.
    """
    merged = dict(existing)
    report = {"added": [], "not_exported": [], "source_changed": []}

    for name, docstring in sorted(discovered.items()):
        if name in existing:
            source = _URL.search(_getting_the_data(docstring).get("Source", ""))
            listed = existing[name].get("source_url")
            if source and listed and source.group(0).rstrip("/") != listed.rstrip("/"):
                report["source_changed"].append((name, listed, source.group(0)))
            continue
        entry = stub_entry(name, docstring)
        keys = list(merged)
        same = [i for i, key in enumerate(keys)
                if merged[key].get("modality") == entry["modality"]]
        at = same[-1] + 1 if same else len(keys)
        merged = dict(list(merged.items())[:at] + [(name, entry)] + list(merged.items())[at:])
        report["added"].append((name, entry))

    report["not_exported"] = sorted(name for name in existing if name not in discovered)
    return merged, report


def format_report(report):
    """The report as Markdown, for the console and the PR body."""
    lines = []
    if report["added"]:
        lines.append(f"**New dataset cards ({len(report['added'])})**, filled in from docstrings:")
        for name, entry in report["added"]:
            access = entry.get("access", "no \"Getting the data\" block")
            lines.append(f"- `{name}`: {entry['modality']}, {access}")
    if report["source_changed"]:
        lines.append("\n**Docstring cites a different source** (the site was not changed):")
        lines += [f"- `{name}`: site has {old}, docstring has {new}"
                  for name, old, new in report["source_changed"]]
    if report["not_exported"]:
        lines.append("\n**On the site but no longer exported by pyhealth.datasets** (not removed):")
        lines += [f"- `{name}`" for name in report["not_exported"]]
    return "\n".join(lines) or "No dataset changes."


def main():
    parser = argparse.ArgumentParser(
        description="Add stub entries for new PyHealth datasets to data/datasets.json."
    )
    parser.add_argument(
        "--output",
        default=str(_DEFAULT_OUTPUT),
        help="Path to datasets.json (default: data/datasets.json relative to this repo)",
    )
    parser.add_argument("--summary", help="Also append the report, as Markdown, to this file")
    args = parser.parse_args()
    output_path = Path(args.output)

    existing = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else {}

    try:
        discovered = _discover_classes()
    except ImportError as e:
        raise SystemExit(
            f"Could not import pyhealth: {e}\n"
            "Make sure pyhealth is installed in your active Python environment."
        )

    merged, report = merge_datasets(existing, discovered)
    output_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    text = format_report(report)
    print(text)
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as f:
            f.write(text + "\n\n")
    print(f"Wrote {len(merged)} datasets to {output_path}  ({len(report['added'])} new)")


if __name__ == "__main__":
    main()
