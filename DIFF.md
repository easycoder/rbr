# 2026-11-18 — the Relay brief published in the documentation

**Action:** `./deploy.sh` publishes the new page — it copies `docs/` and `docs-reader/` to `/docs/` on the site. No version bump, so controllers are unaffected and nothing needs restarting. After the deploy the brief is at <https://rbrheating.com/docs/#succession>.

## What changed

`docs/succession.md` — the brief written for Relay, published in the documentation tree under its ten headings: what it is, who uses it, why it exists, how it works, how to run/test/deploy, the estate, the economics, the obligations, the state of play and the first 30 days. It is the brief the listing carried in full, unchanged in substance, with file names and paths as the repository has them.

`docs/README.md` — a **Taking it on** role path and a **Succession** table row. This is what puts the page on the site: the reader at `/docs` builds its page list from the README's own list items and table rows, in order of first appearance. Also, the "Four audiences" convention note became five, and the Status paragraph names the new page.

`relay-listing.json` — the `brief` field is now a condensed version of the same ten sections (6.2 KB instead of 18.7 KB), ending with the link to <https://rbrheating.com/docs/#succession>. Every other field is as it was.

## Checked

`node tests/docs-reader-check.js` — 72 passed, 0 failed. The page list is 33 documents, `succession` is second from the end and the glossary is still last, which is what the reader's order assertions require.

The page was then opened in the real reader under jsdom: the H1, the status band and all ten headings render, the estate table arrives as 11 rows, there are no console errors, and no "not written yet" notice.

## If it needs revisiting

The page sits at the top level of `docs/` rather than in a layer folder, so its slug is `succession` and not `succession/something`. Renaming the file breaks a link that has been published to Relay, so keep the slug if the page moves.

`DIFF.md`'s previous entry — the controller crash-loop fix (`controller.allspeak`, `rbr-watchdog.sh`, `rbr-doctor.py`) — still needs `./deploy.sh` if it has not been published yet; this change uses the same command, so one run covers both.
