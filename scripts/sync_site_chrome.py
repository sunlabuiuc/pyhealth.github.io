"""
Write the shared site header (nav) and footer into every page.

Usage (from the pyhealth.github.io repo root):
    python scripts/sync_site_chrome.py          # rewrite pages in place
    python scripts/sync_site_chrome.py --check  # exit 1 if any page is out of sync

The header and footer are plain HTML in each page (no build step, works
without JavaScript). This script is the single source for that markup: edit
NAV_LINKS / FOOTER_LINKS or the templates below, then re-run it.

Each page's chrome sits between marker comments:
    <!-- site-header:start --> ... <!-- site-header:end -->
    <!-- site-footer:start --> ... <!-- site-footer:end -->

blogs/<slug>/index.html pages are generated from blog.html, so after running
this, also run scripts/build_blog_index.py.
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DOCS_URL = "https://pyhealth.readthedocs.io/en/latest/"
GITHUB_URL = "https://github.com/sunlabuiuc/PyHealth"

# (key, label, href) — internal hrefs are relative to the site root.
NAV_LINKS = [
    ("datasets", "Datasets", "datasets.html"),
    ("tasks", "Tasks", "tasks.html"),
    ("models", "Models", "models.html"),
    ("blog", "Blog", "blog_list.html"),
    ("research", "Research", "research.html"),
    ("contribute", "Contribute", "how_to_contribute.html"),
    ("github", "GitHub", GITHUB_URL),
]
NAV_CTA = ("docs", "Docs", DOCS_URL)

FOOTER_LINKS = [
    ("Docs", DOCS_URL),
    ("GitHub", GITHUB_URL),
    ("PyPI", "https://pypi.org/project/pyhealth/"),
    ("Discord", "https://discord.gg/mpb835EHaX"),
    ("Roadmap", "roadmap.html"),
    ("Blog", "blog_list.html"),
    ("Contribute", "how_to_contribute.html"),
]

# page path -> (link prefix, active nav key)
# blog.html is also served at /blogs/<slug>/, so it needs root-absolute links.
PAGES = {
    "index.html": ("", None),
    "datasets.html": ("", "datasets"),
    "tasks.html": ("", "tasks"),
    "models.html": ("", "models"),
    "roadmap.html": ("", None),
    "blog_list.html": ("", "blog"),
    "blog.html": ("/", "blog"),
    "research.html": ("", "research"),
    "how_to_contribute.html": ("", "contribute"),
}
for _p in sorted((ROOT / "research").glob("*.html")):
    PAGES[f"research/{_p.name}"] = ("../", "research")

HEADER_RE = re.compile(
    r"<!-- site-header:start -->.*?<!-- site-header:end -->"
    r"|<header class=\"site-header\">.*?</header>",
    re.S,
)
FOOTER_RE = re.compile(
    r"<!-- site-footer:start -->.*?<!-- site-footer:end -->"
    r"|<footer class=\"site-footer\">.*?</footer>",
    re.S,
)


def _href(href, prefix):
    return href if href.startswith("http") else prefix + href


def _link(label, href, prefix, cls=None):
    attrs = f' href="{_href(href, prefix)}"'
    if cls:
        attrs += f' class="{cls}"'
    if href.startswith("http"):
        attrs += ' target="_blank" rel="noopener"'
    return f"<a{attrs}>{label}</a>"


def render_header(prefix, active):
    items = []
    for key, label, href in NAV_LINKS:
        cls = "active" if key == active else None
        link = _link(label, href, prefix, cls)
        if cls:
            link = link.replace("<a ", '<a aria-current="page" ', 1)
        items.append(f"        {link}")
    key, label, href = NAV_CTA
    items.append(f"        {_link(label, href, prefix, 'nav-cta')}")
    return (
        "<!-- site-header:start -->\n"
        '  <header class="site-header">\n'
        '    <div class="site-wrap header-inner">\n'
        f'      <a href="{prefix}index.html" class="site-brand">PyHealth</a>\n'
        '      <nav class="nav" aria-label="Main navigation">\n'
        + "\n".join(items) + "\n"
        "      </nav>\n"
        "    </div>\n"
        "  </header>\n"
        "  <!-- site-header:end -->"
    )


def render_footer(prefix):
    links = "\n".join(
        f"        {_link(label, href, prefix)}" for label, href in FOOTER_LINKS
    )
    return (
        "<!-- site-footer:start -->\n"
        '  <footer class="site-footer">\n'
        '    <div class="site-wrap footer-inner">\n'
        '      <span>PyHealth · built by <a href="https://github.com/sunlabuiuc" '
        'target="_blank" rel="noopener">SunLab at UIUC</a> and community contributors</span>\n'
        '      <nav class="footer-links" aria-label="Footer">\n'
        f"{links}\n"
        "      </nav>\n"
        "    </div>\n"
        "  </footer>\n"
        "  <!-- site-footer:end -->"
    )


def sync_page(text, prefix, active):
    header, footer = render_header(prefix, active), render_footer(prefix)

    if HEADER_RE.search(text):
        text = HEADER_RE.sub(lambda _: header, text, count=1)
    else:  # page had no header yet: put it first in <body>
        text = re.sub(r"<body>\n", lambda m: m.group(0) + "\n  " + header + "\n", text, count=1)

    if FOOTER_RE.search(text):
        text = FOOTER_RE.sub(lambda _: footer, text, count=1)
    else:  # page had no footer yet: put it right after the main content
        m = re.search(r"</main>\n", text) or re.search(r"\n  </div>\n", text)
        if not m:
            raise ValueError("no </main> or top-level </div> to place the footer after")
        text = text[: m.end()] + "\n  " + footer + "\n" + text[m.end():]
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true",
                        help="report pages that differ instead of rewriting them")
    args = parser.parse_args()

    stale = []
    for rel, (prefix, active) in PAGES.items():
        path = ROOT / rel
        old = path.read_text(encoding="utf-8")
        new = sync_page(old, prefix, active)
        if new != old:
            stale.append(rel)
            if not args.check:
                path.write_text(new, encoding="utf-8")

    if args.check:
        for rel in stale:
            print(f"out of sync: {rel}")
        print(f"{len(PAGES) - len(stale)}/{len(PAGES)} pages in sync")
        sys.exit(1 if stale else 0)
    print(f"Updated {len(stale)} of {len(PAGES)} pages")
    if "blog.html" in stale:
        print("blog.html changed: run python scripts/build_blog_index.py")


if __name__ == "__main__":
    main()
