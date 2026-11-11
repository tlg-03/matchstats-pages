# Working on the MatchStats pages

The way of working (worktrees, checkpoints, hooks) is the shared standard in `tlg-03/workspace`
(`STANDARD.md`); `make help` lists the commands. This file covers what is particular to this repo.

## Current state

Last updated: 11 Nov 2026.

- **In progress:** none. The live site serves `main` (3946da5) byte for byte.
- **Recent decisions:** 1 Aug 2026: the repo is public, because GitHub Pages on a free account needs that, so it holds only the privacy, support and index pages and the files for working on them, never app source. 20 Aug 2026: one privacy policy and one support page cover every sport, so there is one policy to keep in step and one pair of URLs to file. 10 Nov 2026: pages go live from `main` with `make publish`, which checks that the live pages match `main` and every other file answers 404, so nothing but the pages is ever served (see [Changing the pages](#changing-the-pages)).
- **Waiting on the owner:** none.
- **Next:** none.

## What this is

The privacy policy and the support page for every MatchStats app (lacrosse and netball, on iPhone,
iPad and Mac), served by GitHub Pages from `main`:

```
https://tlg-03.github.io/matchstats-pages/privacy.html   the Privacy Policy URL in App Store Connect
https://tlg-03.github.io/matchstats-pages/support.html   the Support URL in App Store Connect
https://tlg-03.github.io/matchstats-pages/               the support page again (index.html)
```

Both apps file the same two URLs, and an Apple reviewer opens them. This repo is the only source
of the pages: edit them here and nowhere else. They are written in the plural and name no sport,
so one policy and one support page cover every app. Keep it that way; a page per sport would mean
two policies to keep in step and more URLs to file.

The repo is public (GitHub Pages on a free account needs that), so nothing but the pages and the
files for working on them belongs here.

## Never rename this repo

Its name is part of both URLs. Renaming it breaks the URLs filed with App Store Connect, a 404 on a
form field a reviewer opens. The same goes for the two file names.

## Changing the pages

```
make wt-new NAME=fix-wording    from the main checkout
                                edit privacy.html or support.html in the worktree
cp support.html index.html      after any change to support.html
make view                       preview at http://localhost:8730/index.html (caching off)
make test                       then commit
make wt-done                    tests, fast-forwards main, pushes and verifies it on GitHub
make publish                    from the main checkout: waits until the live site serves main
make wt-rm NAME=fix-wording     from the main checkout
```

The push in `make wt-done` starts the GitHub Pages build. `make publish` runs the tests again,
pushes `main` if it is ahead of GitHub (it should not be after `wt-done`), checks that GitHub holds
that commit, then waits up to 10 minutes until every live `.html`, `.css` and `.js` file is byte for
byte the committed one; that part is `workspace/bin/publish matchstats-pages`, which also runs on
its own. Last, `tests/check_pages.py --live` asks the live site for every other tracked file, and for
the `.html` page each Markdown file would become (`README.html`, `DEVELOPMENT.html`), and expects a
404 for each.

`index.html` is a copy of `support.html` so that the bare URL serves the support page instead of a
404. Change both together; `make test` refuses a difference.

`privacy.html` promises a new date at the top whenever the policy changes: update its
"Last updated" line with any change of substance.

## What GitHub serves

GitHub Pages builds `main` with Jekyll (the legacy build, from the root). The pages have no front
matter, so Jekyll copies them unchanged. `_config.yml` keeps everything else off the site: it
excludes `Makefile`, `README.md`, `DEVELOPMENT.md` and `tests/`, and Jekyll skips names starting
with `.` or `_` (`.mailmap`, `.gitignore`, `_config.yml`), except `.htaccess` and the posts in a
`_posts` folder. An exclude entry hides every path that starts with it, so `tests` would hide a
`tests.html` too. Do not add a `.nojekyll` file: it would serve every file, these notes included.

A new file for working on the site goes into that exclude list; `make test` refuses one that would
be published. A new file the site needs that is not `.html`, `.css` or `.js` (an image, say) must
not be excluded: add its type to `SERVED_TYPES` in `tests/check_pages.py` and to the types
`workspace/bin/publish` compares with the live site, which today are only those three.

## Tests

`make test`:

- `cmp index.html support.html`: the two are byte-identical.
- `tests/check_pages.py`: every page starts with `<!doctype html>` and closes every element
  explicitly, in order (void elements such as `<meta>` and `<br>` have no closing tag); every
  file GitHub Pages would publish is a page (`.html`, `.css` or `.js`); and every page is
  published, since `make publish` looks for each one on the live site. It reads tracked files and
  new ones that are not ignored, and follows Jekyll's rules closely, not exactly: the live check in
  `make publish` is the proof.

## Local data

- In the repo: none (`LOCAL_DATA` is empty).
- Outside the repo: none.

## Commits

Neutral, present-tense messages, as `STANDARD.md` sets out (the hooks enforce it). Stage explicit
paths.
