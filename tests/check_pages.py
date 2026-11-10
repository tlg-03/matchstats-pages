"""Checks the pages and what GitHub Pages would serve (Python 3.9 standard library only).

`make test` runs it from the repo root:

1. Every page parses: it starts with <!doctype html>, and every element is closed
   explicitly, in order (void elements such as <meta> and <br> have no closing tag).
2. GitHub Pages serves the pages and nothing else. Every file Jekyll would publish
   (tracked, or new and not ignored) is .html, .css or .js, and every such file is
   published, because workspace/bin/publish compares each one with the live site.

`make publish` runs it with `--live <site URL>` after workspace/bin/publish: every tracked
file the site must not serve, and the .html page a Markdown file would become, has to
answer 404.
"""

import fnmatch
import os
import re
import subprocess
import sys
import urllib.parse
from html.parser import HTMLParser

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "source", "track", "wbr"}
# The types workspace/bin/publish compares with the live site. A file of another type that the
# site needs (an image, say) goes here and into that script's list, so it is checked live too.
SERVED_TYPES = (".html", ".css", ".js")
MARKDOWN = (".markdown", ".mkdown", ".mkdn", ".mkd", ".md")    # Jekyll renders these to .html


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


def repo_files(new_too=True):
    cmd = ["git", "ls-files", "-z", "--cached"] + (["--others", "--exclude-standard"] if new_too else [])
    out = subprocess.run(cmd, stdout=subprocess.PIPE, check=True).stdout.decode("utf-8")
    return sorted(set(f for f in out.split("\0") if f))


def config_list(text, key, default, problems):
    """The list `key: [a, b]` from _config.yml, written on one line; default if the key is absent."""
    lines = [line for line in text.splitlines() if re.match(r"%s\s*:" % key, line)]
    if not lines:
        return default
    m = re.match(r"%s\s*:\s*\[([^\]]*)\]\s*(#.*)?$" % key, lines[0])
    if len(lines) > 1 or not m:
        problems.append("_config.yml: write %s on one line, as %s: [a, b]; this check reads only that form"
                        % (key, key))
        return default
    return [x.strip().strip("'\"") for x in m.group(1).split(",") if x.strip()]


def site_rules(problems):
    try:
        with open("_config.yml", encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        text = ""
    # Jekyll 3 (the version GitHub Pages runs) replaces its default lists with the ones set here.
    return (config_list(text, "exclude", [], problems),
            config_list(text, "include", [".htaccess"], problems))


def matches(patterns, path, is_dir):
    """Jekyll's test against exclude or include: a glob, a plain string prefix (so `tests` also
    covers tests.html), or `name/` for a folder."""
    return any(fnmatch.fnmatchcase(path, p) or path.startswith(p) or (is_dir and p == path + "/")
               for p in patterns)


def served(path, exclude, include):
    """Would GitHub Pages publish this file? Jekyll walks the folders and drops every entry whose
    name starts with . _ # or ~, ends in ~, or (as a path from the root) matches exclude, unless
    its name matches include (by default .htaccess). A _posts folder is read anyway: its files are
    published as posts. Symbolic links are never published."""
    if os.path.islink(path):
        return False
    parts = path.split("/")
    for i, name in enumerate(parts):
        is_dir = i < len(parts) - 1
        if matches(include, name, is_dir):
            continue
        special = name[0] in "._#~" and not (is_dir and name == "_posts")
        if special or name.endswith("~") or matches(exclude, "/".join(parts[:i + 1]), is_dir):
            return False
    return True


def check_files(exclude, include, problems):
    files = repo_files()
    for f in files:
        page = f.endswith(SERVED_TYPES)
        shown = served(f, exclude, include)
        if shown and not page:
            problems.append("%s would be published by GitHub Pages: add it to exclude in _config.yml "
                            "or, if the site needs it, add its type to SERVED_TYPES in %s and to the "
                            "types workspace/bin/publish compares" % (f, sys.argv[0]))
        elif page and not shown:
            problems.append("%s would not be published by GitHub Pages (a symbolic link, a name "
                            "starting with . _ # or ~, or exclude in _config.yml hides it), but "
                            "workspace/bin/publish expects it on the live site: rename or move it" % f)
    pages = [f for f in files if f.endswith(".html") and os.path.isfile(f)]
    for f in pages:
        page = Page(f, problems)
        with open(f, encoding="utf-8") as fh:
            page.feed(fh.read())
        page.finish()
    return "%d pages parse; GitHub Pages would serve them and nothing else" % len(pages)


def check_live(url, exclude, include, problems):
    paths = []
    for f in repo_files(new_too=False):
        if not served(f, exclude, include):
            paths.append(f)
            stem, ext = os.path.splitext(f)
            if ext.lower() in MARKDOWN:
                paths.append(stem + ".html")
    for p in paths:
        live = "%s/%s" % (url.rstrip("/"), urllib.parse.quote(p))
        code = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                               "-H", "Cache-Control: no-cache", live],
                              stdout=subprocess.PIPE).stdout.decode().strip()
        if code != "404":
            problems.append("%s answers %s, not 404: it must not be served" % (live, code or "nothing"))
    return "the %d other paths answer 404: the site serves only the pages" % len(paths)


def main():
    problems = []
    exclude, include = site_rules(problems)
    if problems:
        sys.exit("\n".join(problems))
    if len(sys.argv) == 3 and sys.argv[1] == "--live":
        done = check_live(sys.argv[2], exclude, include, problems)
    elif len(sys.argv) == 1:
        done = check_files(exclude, include, problems)
    else:
        sys.exit("usage: %s [--live <site URL>]" % sys.argv[0])
    if problems:
        sys.exit("\n".join(problems))
    print(done)


if __name__ == "__main__":
    main()
