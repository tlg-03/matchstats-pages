# MatchStats privacy and support pages, served by GitHub Pages from main. The verbs (view, test,
# worktrees, checkpoints) come from the shared workspace repo, tlg-03/workspace: `make help`
# lists them. Every script below still runs on its own without make.

# `make view`: the pages from the repo root, the folder GitHub serves.
VIEW_DIR      = .
VIEW_PORT     = 8730
VIEW_PAGE     = index.html

# index.html is a copy of support.html, so the bare URL serves the support page. Then every page
# parses with its elements closed, and nothing but pages would be published (tests/check_pages.py).
TEST_CMD      = cmp -s index.html support.html || { echo "index.html differs from support.html: cp support.html index.html" >&2; exit 1; }; python3 -B tests/check_pages.py

# Nothing here is local by design.
LOCAL_DATA    =

# The live site, checked by `make publish`. The repo's name is part of it: never rename the repo.
SITE_URL      = https://tlg-03.github.io/matchstats-pages

WS := $(shell git config --get tlg.workspace)
ifeq ($(WS),)
$(error This repo needs tlg-03/workspace beside it: clone it, then run workspace/bin/bootstrap)
endif
include $(WS)/make/common.mk

.PHONY: publish
help::
	@echo "make publish        main checkout: test, push main if needed, check the live site serves it and nothing else"

# `make publish` after `make wt-done`: workspace/bin/publish checks GitHub holds this commit, then
# waits (up to 10 minutes) until every live page is byte for byte the committed file. Last, every
# other tracked file (and the .html a Markdown file would become) must answer 404 on the live site.
publish:
	@test "$$(cd "$$(git rev-parse --git-dir)" && pwd -P)" = "$$(cd "$$(git rev-parse --git-common-dir)" && pwd -P)" || { echo "make publish runs from the main checkout, after make wt-done" >&2; exit 1; }
	@$(MAKE) -s --no-print-directory test
	@"$(B)/publish" matchstats-pages
	@python3 -B tests/check_pages.py --live "$(SITE_URL)"
