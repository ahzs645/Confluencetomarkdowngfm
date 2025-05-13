#!/usr/bin/env python3
"""
clean_confluence.py – trims Confluence-specific clutter,
rewrites attachment links, then Pandoc-converts HTML→GFM
leaving complex tables untouched.
"""
import subprocess, pathlib, re, sys, datetime
from bs4 import BeautifulSoup

src     = pathlib.Path(sys.argv[1]).resolve()          # page.html
out_dir = pathlib.Path(sys.argv[2]).resolve()          # docs/
out_dir.mkdir(parents=True, exist_ok=True)

html = BeautifulSoup(src.read_text(encoding="utf-8"), "lxml")

# ── scrub Confluence chrome we don’t want ─────────────────────────
for junk in ["#breadcrumb-section", "#attachments", "#footer",
             "[id^=expander-]", ".pageSection"]:       # add more as needed
    for tag in html.select(junk):
        tag.decompose()

# ── yank the title & metadata for front-matter --------------------
title = html.select_one("#title-text").get_text(" ", strip=True)
meta  = html.select_one(".page-metadata").get_text(" ", strip=True)

# ── collect images / docs into nice sub-folders -------------------
asset_img  = out_dir / "images"; asset_file = out_dir / "files"
asset_img.mkdir(exist_ok=True);   asset_file.mkdir(exist_ok=True)

for tag in html.find_all(["img", "a"]):
    attr = "src" if tag.name == "img" else "href"
    link = tag.get(attr, "")
    if "attachments/" not in link: continue
    fname   = pathlib.Path(link).name
    destdir = asset_img if tag.name == "img" else asset_file
    dest    = destdir / fname
    try:
        (src.parent / link).replace(dest)   # move if the attachment is local
    except FileNotFoundError:
        pass                                # ignore remote links in the sample
    tag[attr] = f"{destdir.name}/{fname}"   # rewrite link

# ── dump the cleaned body to temp HTML ----------------------------
body_file = out_dir / "_body.html"
body_file.write_text(str(html.select_one("#content")), encoding="utf-8")

# ── 1-step convert: HTML → GitHub-Flavoured Markdown --------------
md = subprocess.check_output(
        ["pandoc", "-f", "html", "-t", "gfm", "--wrap=none", body_file],
        text=True, stderr=subprocess.STDOUT)

# ── prepend a tiny YAML header & save ------------------------------
readme = out_dir / "README.md"
front  = (
    f"---\n"
    f"title: \"{title}\"\n"
    f"converted: {datetime.date.today()}\n"
    f"original_meta: \"{meta}\"\n"
    f"---\n\n"
)
readme.write_text(front + md, encoding="utf-8")

print("✔  Converted →", readme.relative_to(pathlib.Path.cwd()))