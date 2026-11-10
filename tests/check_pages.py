"""Checks run by `make test` (from the repo root; Python 3.9 standard library only).

1. Every page parses: it starts with <!doctype html>, and every element is closed
   explicitly, in order (void elements such as <meta> and <br> have no closing tag).
2. GitHub Pages serves nothing but pages: every file it would publish (tracked, or new
   and not ignored) is .html, .css or .js, or is listed under exclude in _config.yml.
"""

import fnmatch
import os
import re
import subprocess
import sys
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "source", "track", "wbr"}
SERVED_TYPES = (".html", ".css", ".js")


class Page(HTMLParser):
    def __init__(self, path, problems):
        super().__init__()
        self.path, self.problems = path, problems
        self.open = []          # (tag, line) of the elements not closed yet
        self.doctype = False

    def problem(self, line, why):
        self.problems.append("%s:%d: %s" % (self.path, line, why))

    def handle_decl(self, decl):
        self.doctype = self.doctype or decl.lower() == "doctype html"

    def handle_starttag(self, tag, attrs):
        if not self.doctype and not self.open:
            self.problem(self.getpos()[0], "<%s> before <!doctype html>" % tag)
            self.doctype = True             # report it once
        if tag not in VOID:
            self.open.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        if tag not in VOID:
            self.problem(self.getpos()[0], "<%s/> is not a void element: close it with </%s>" % (tag, tag))

    def handle_endtag(self, tag):
        line = self.getpos()[0]
        if tag in VOID:
            self.problem(line, "</%s>: <%s> has no closing tag" % (tag, tag))
        elif not self.open:
            self.problem(line, "</%s> closes nothing" % tag)
        elif self.open[-1][0] != tag:
            want, opened = self.open[-1]
            self.problem(line, "</%s> where </%s> (opened on line %d) was due" % (tag, want, opened))
            if any(t == tag for t, _ in self.open):     # resynchronise on the matching element
                while self.open.pop()[0] != tag:
                    pass
        else:
            self.open.pop()

    def finish(self):
        self.close()
        if not self.doctype:
            self.problem(1, "no <!doctype html>")
        for tag, line in self.open:
            self.problem(line, "<%s> is never closed" % tag)


def repo_files():
    out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                         stdout=subprocess.PIPE, check=True).stdout.decode("utf-8")
    return sorted(set(f for f in out.split("\0") if f))


def excluded_patterns():
    try:
        with open("_config.yml", encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        return []
    m = re.search(r"^exclude:\s*\[(.*)\]\s*$", text, re.M)
    return [x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()] if m else []


def served(path, exclude):
    """Would Jekyll publish this file? Names starting with . _ # or ending in ~ never are."""
    if any(part[0] in "._#" or part.endswith("~") for part in path.split("/")):
        return False
    return not any(path == x or path.startswith(x.rstrip("/") + "/") or fnmatch.fnmatch(path, x)
                   for x in exclude)


def main():
    problems = []
    files = repo_files()
    exclude = excluded_patterns()
    for f in files:
        if served(f, exclude) and not f.endswith(SERVED_TYPES):
            problems.append("%s would be published by GitHub Pages: add it to exclude in _config.yml" % f)
    pages = [f for f in files if f.endswith(".html") and os.path.isfile(f)]
    for f in pages:
        page = Page(f, problems)
        with open(f, encoding="utf-8") as fh:
            page.feed(fh.read())
        page.finish()
    if problems:
        sys.exit("\n".join(problems))
    print("%d pages parse; nothing but pages is published" % len(pages))


if __name__ == "__main__":
    main()
