"""
Write data/bounties.json, which the homepage and bounties.html render, from
PyHealth's bounty.yaml and the PRs that claim bounties.

Usage (from the pyhealth.github.io repo root, PyHealth checked out beside it):
    python scripts/extract_bounties.py
    python scripts/extract_bounties.py --summary body.md
    python scripts/extract_bounties.py --prs-file prs.json   # no API calls

The rules match PyHealth's tools/update_bounty_board.py:
  - A PR claims a bounty when its title carries [BTY-<id>] or [Bounty-<id>].
    PRs closed without merging are ignored.
  - A bounty is complete once a claiming PR merges, or when bounty.yaml sets
    its `complete` field.
  - Credit is the `complete` text ("@login (#PR, ...), @other"), or else the
    authors of the merged PRs. Email addresses are never written.

PRs are read from the GitHub API (public data; GITHUB_TOKEN or GH_TOKEN raises
the rate limit). Without network access, pass --prs-file, or --no-prs to use
bounty.yaml alone.
"""

import argparse
import json
import os
import re
import urllib.request
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO = "sunlabuiuc/PyHealth"
BOARD_URL = f"https://github.com/{REPO}/issues/1489"
TITLE_TAG_RE = re.compile(r"\[\s*(?:bounty|bty)\s*-\s*(\d+)\s*\]", re.IGNORECASE)
EMAIL_RE = re.compile(r"\s*\(?[\w.%+-]+@[\w-]+(?:\.[\w-]+)+\)?")
CREDIT_RE = re.compile(r"@([A-Za-z0-9-]+)(?:\s*\(([^)]*)\))?")


def load_bounties(path):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return {b["id"]: b for b in data.get("bounty") or []}


def fetch_prs():
    """Open and merged PRs whose title names a bounty."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    prs = []
    for term in ("BTY", "Bounty"):
        page = 1
        while True:
            url = ("https://api.github.com/search/issues?per_page=100"
                   f"&page={page}&q=repo:{REPO}+is:pr+in:title+{term}")
            req = urllib.request.Request(url, headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "pyhealth-site-sync",
                **({"Authorization": f"Bearer {token}"} if token else {}),
            })
            with urllib.request.urlopen(req) as resp:
                items = json.load(resp)["items"]
            for it in items:
                merged = (it.get("pull_request") or {}).get("merged_at")
                state = "MERGED" if merged else it["state"].upper()
                prs.append({"number": it["number"], "title": it["title"],
                            "state": state, "author": it["user"]["login"]})
            if len(items) < 100:
                break
            page += 1
    return list({p["number"]: p for p in prs}.values())


def parse_credit(text):
    """`@a (#1, #2), @b` -> [{"login": "a", "prs": [1, 2]}, {"login": "b", ...}]."""
    text = EMAIL_RE.sub("", text)
    return [{"login": login,
             "prs": [int(n) for n in re.findall(r"#(\d+)", prs or "")]}
            for login, prs in CREDIT_RE.findall(text)]


def build(bounties, prs):
    claims = defaultdict(list)
    for pr in sorted(prs, key=lambda p: p["number"]):
        if pr["state"] not in ("OPEN", "MERGED"):
            continue
        for bid in {int(m) for m in TITLE_TAG_RE.findall(pr["title"])}:
            if bid in bounties:
                claims[bid].append(pr)

    open_, completed, to_record = [], [], []
    for bid, b in sorted(bounties.items()):
        merged = defaultdict(list)
        for pr in claims[bid]:
            if pr["state"] == "MERGED":
                merged[pr["author"]].append(pr["number"])
        item = {"id": bid, "title": b["title"].strip(), "category": b["category"],
                "priority": b.get("priority")}
        if b.get("complete"):
            completed.append({**item, "credit": parse_credit(b["complete"])})
        elif merged:
            completed.append({**item, "credit": [
                {"login": a, "prs": n} for a, n in merged.items()]})
            to_record.append(bid)
        else:
            authors = list(dict.fromkeys(p["author"] for p in claims[bid]))
            open_.append({**item, "description": b["description"].strip(),
                          "claimed_by": authors,
                          "prs": [p["number"] for p in claims[bid]]})
    open_.sort(key=lambda b: (b["priority"] or 9, b["id"]))
    completed.sort(key=lambda b: -b["id"])

    people = defaultdict(list)
    for b in completed:
        for c in b["credit"]:
            people[c["login"]].append(b["id"])
    contributors = sorted(({"login": k, "bounties": v} for k, v in people.items()),
                          key=lambda c: (-len(c["bounties"]), c["login"].lower()))
    return {
        "board_url": BOARD_URL,
        "counts": {"open": len(open_),
                   "claimed": sum(1 for b in open_ if b["claimed_by"]),
                   "completed": len(completed),
                   "contributors": len(contributors)},
        "open": open_,
        "completed": completed,
        "contributors": contributors,
    }, to_record


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pyhealth", default=str(ROOT.parent / "PyHealth"))
    ap.add_argument("--output", default=str(ROOT / "data" / "bounties.json"))
    ap.add_argument("--prs-file", help="JSON list of {number, title, state, author}.")
    ap.add_argument("--no-prs", action="store_true", help="Use bounty.yaml alone.")
    ap.add_argument("--summary", help="Append a Markdown report to this file.")
    args = ap.parse_args()

    bounties = load_bounties(Path(args.pyhealth) / "bounty.yaml")
    if args.no_prs:
        prs = []
    elif args.prs_file:
        prs = json.loads(Path(args.prs_file).read_text(encoding="utf-8"))
    else:
        prs = fetch_prs()
    data, to_record = build(bounties, prs)
    Path(args.output).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf-8")
    c = data["counts"]
    lines = [f"**Bounties:** {c['open']} open ({c['claimed']} claimed), "
             f"{c['completed']} completed by {c['contributors']} contributors."]
    if to_record:
        lines.append("Completed by a merged PR, credit not yet in PyHealth's "
                     "bounty.yaml: " + ", ".join(f"BTY-{b}" for b in to_record) + ".")
    print("\n".join(lines))
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as f:
            f.write("\n" + "\n\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
