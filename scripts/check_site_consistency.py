#!/usr/bin/env python3
"""Verify the entity pages on pyhealth.github.io still match the PyHealth package.

models.html, datasets.html and data/tasks.json name PyHealth classes and link to
readthedocs pages and GitHub examples. All three drift silently when the package
moves. This checks, against a PyHealth checkout:

  1. every ``pyhealth.<mod>.<Symbol>`` the site names is actually exported
  2. every readthedocs api/{models,datasets,tasks}/<slug>.html link has a
     matching docs/api/<cat>/<slug>.rst
  3. every github.com/sunlabuiuc/PyHealth/blob/<ref>/<path> link resolves
  4. every ``source_file`` in tasks.json exists
  5. (advisory) entities PyHealth exports that the site never mentions

Deliberately stdlib-only and AST-based: it must run in CI without installing
PyHealth or its heavy dependencies.

    python3 scripts/check_site_consistency.py --pyhealth ../PyHealth

With --runtime it additionally imports pyhealth and getattr()s every name, which
catches what the AST pass cannot: a name that is declared but whose lazy
``__getattr__`` or underlying module is broken. Needs PyHealth's dependencies
installed, so it is opt-in rather than the default.

    python3 scripts/check_site_consistency.py --pyhealth ../PyHealth --runtime
"""
import argparse
import ast
import json
import os
import re
import sys

MODULES = ("models", "datasets", "tasks")

# Exported but intentionally not advertised on the site: internal building
# blocks, abstract bases, and deprecated shims.
NOT_ADVERTISED = re.compile(
    r"(Layer$|^Base|^Sample(Dataset|Builder|EHRDataset|SignalDataset)$"
    r"|^DenseBlock$|^DenseLayer$|^TransitionLayer$|^ResBlock2D$|^MambaBlock$"
    r"|^GraphConvolution$|^GraphAttention$|^SinusoidalTimeEmbedding$"
    r"|^TFM_|^EHRGeneration$|^BiAttentionGNNConv$)"
)

# Classes with no rst page of any kind; their docs links legitimately fall back
# to the category index.
NO_RST_PAGE = {"PatientLinkageMIMIC3Task", "LengthOfStayStageNetMIMIC4",
               "SurvivalPreprocessSupport2"}


def exported_symbols(pyhealth, module):
    """Names re-exported from pyhealth/<module>/__init__.py, per its AST."""
    path = os.path.join(pyhealth, "pyhealth", module, "__init__.py")
    tree = ast.parse(open(path).read())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if getattr(target, "id", None) == "__all__":
                    try:
                        names.update(ast.literal_eval(node.value))
                    except ValueError:
                        pass
    # Lazily-exposed names handled by a module-level __getattr__.
    src = open(path).read()
    if "__getattr__" in src:
        names.update(re.findall(r'["\']([A-Z]\w+)["\']', src))
    return names


def site_symbols(site):
    """Symbols the site claims exist, per module."""
    claimed = {m: set() for m in MODULES}
    for page, module in (("models.html", "models"), ("datasets.html", "datasets")):
        text = open(os.path.join(site, page)).read()
        # readthedocs slugs are page names, not symbols -- they are validated
        # separately against the rst files, so drop them before scanning.
        text = re.sub(r"https?://\S*readthedocs\.io\S*", "", text)
        claimed[module].update(
            re.findall(rf"pyhealth\.{module}\.([A-Za-z_]\w*)", text)
        )
        # The visible class name and the import in each card's snippet.
        claimed[module].update(re.findall(r'-classname">([^<]+)<', text))
        claimed[module].update(
            re.findall(r'import</span> <span class="tok-cl">([^<]+)<', text)
        )
    for task in json.load(open(os.path.join(site, "data", "tasks.json"))):
        claimed["tasks"].add(task["class_name"])
        if task.get("display_class"):
            claimed["tasks"].add(task["display_class"])
    return claimed


def site_text(site):
    """Every file on the site that can carry a link."""
    for root, dirs, files in os.walk(site):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules"}]
        for name in files:
            if name.endswith((".html", ".json")):
                path = os.path.join(root, name)
                yield os.path.relpath(path, site), open(path, errors="replace").read()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyhealth", default="../PyHealth",
                        help="path to a PyHealth checkout")
    parser.add_argument("--runtime", action="store_true",
                        help="also import pyhealth and resolve every name "
                             "(requires PyHealth's dependencies installed)")
    args = parser.parse_args()

    site = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pyhealth = os.path.abspath(os.path.join(site, args.pyhealth))
    if not os.path.isdir(os.path.join(pyhealth, "pyhealth")):
        sys.exit(f"no PyHealth checkout at {pyhealth}")

    errors, notes = [], []
    exported = {m: exported_symbols(pyhealth, m) for m in MODULES}

    # 1. Claimed symbols must exist.
    claimed = site_symbols(site)
    for module in MODULES:
        for symbol in sorted(claimed[module] - exported[module]):
            errors.append(f"pyhealth.{module}.{symbol} is named by the site "
                          f"but not exported by pyhealth/{module}/__init__.py")

    # 2 & 3. Links must resolve.
    doc_link = re.compile(
        r"readthedocs\.io/en/latest/api/(models|datasets|tasks)/([\w.]+)\.html")
    blob_link = re.compile(
        r"github\.com/sunlabuiuc/PyHealth/blob/[^/\s\"'<>)]+/([^\s\"'<>)]+)")
    for page, text in site_text(site):
        for category, slug in set(doc_link.findall(text)):
            rst = os.path.join(pyhealth, "docs", "api", category, f"{slug}.rst")
            if not os.path.isfile(rst):
                errors.append(f"{page}: docs link to api/{category}/{slug}.html "
                              f"but docs/api/{category}/{slug}.rst does not exist")
        for rel in set(blob_link.findall(text)):
            if not os.path.exists(os.path.join(pyhealth, rel.rstrip(".,"))):
                errors.append(f"{page}: example link to {rel} which does not "
                              f"exist in the checkout")

    # 4. tasks.json bookkeeping.
    tasks = json.load(open(os.path.join(site, "data", "tasks.json")))
    for task in tasks:
        name = task["class_name"]
        src = task.get("source_file")
        if not src:
            errors.append(f"tasks.json: {name} has no source_file")
        elif not os.path.isfile(os.path.join(pyhealth, src)):
            errors.append(f"tasks.json: {name} source_file {src} does not exist")
        if task.get("display_class") and task["display_class"] != name:
            errors.append(f"tasks.json: {name} display_class is "
                          f"{task['display_class']}; they must match")
        if task.get("docs_url", "").endswith("api/tasks.html") and name not in NO_RST_PAGE:
            notes.append(f"tasks.json: {name} still points at the generic docs "
                         f"index; a per-class or module rst page may now exist")

    # 5. Optionally resolve every name for real.
    if args.runtime:
        sys.path.insert(0, pyhealth)
        import importlib
        for module in MODULES:
            try:
                imported = importlib.import_module(f"pyhealth.{module}")
            except ImportError as exc:
                errors.append(f"--runtime: cannot import pyhealth.{module}: {exc}")
                continue
            if not os.path.abspath(imported.__file__).startswith(pyhealth):
                errors.append(f"--runtime: imported pyhealth.{module} from "
                              f"{imported.__file__}, not {pyhealth}; an editable "
                              f"install is shadowing the checkout")
                continue
            for symbol in sorted(claimed[module]):
                if not hasattr(imported, symbol):
                    errors.append(f"--runtime: pyhealth.{module}.{symbol} does "
                                  f"not resolve at import time")

    # 6. Advisory coverage report.
    for module in MODULES:
        missing = {s for s in exported[module]
                   if s[0].isupper() and not NOT_ADVERTISED.search(s)} - claimed[module]
        for symbol in sorted(missing):
            notes.append(f"pyhealth.{module}.{symbol} is exported but not on the site")

    for note in notes:
        print(f"note:  {note}")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        print(f"\n{len(errors)} error(s), {len(notes)} note(s)")
        return 1
    print(f"\nOK: site is consistent with {pyhealth} ({len(notes)} note(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
