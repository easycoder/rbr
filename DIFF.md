# What to do

- **Commit all of it, and push the docs.** Two reasons and they are separate: `docs-reader/` is **untracked** while being live on the site, so a `git clean` would empty `/docs`; and the reader reads the documentation from `main`, so the new installation page appears on the site only once it is pushed. Nothing needs deploying — `deploy.sh` ships the reader, and the reader has not changed since it went up.
- **Then glance at <https://rbrheating.com/docs>.** It is running the current build already (all three files byte-identical to the working tree), but the page count goes from 29 to 30 when the docs reach `main`, and `.scratch/docs-reader-shots/` holds the screenshots this was checked from.
- **Copy the refreshed `server.allspeak` to any controller that carries one.** It is not in the update tarball — that file is copied by hand — so a box used for on-box editing still has the copy that serves nothing. Same trap in `AGENT.md`, and in `doc/CONTROLLER-FILES.md`.
- **Nothing else.** The controller runtime, the PWA and the map are untouched. `/docs` is still deliberately unlinked anywhere on the site, the AllSpeak pin is left as it is, and the local `asdoc-check.py` is left as it is — all three recorded below rather than waiting on you.
- **For the next session:** [TODO-docs.md](TODO-docs.md) is the documentation programme's working state — the order of work, what is waiting on the world, and the conventions the work has settled on.

# What changed

## The documentation programme was refreshed, and its one new document moved into the tree

`RBR-SETUP.md` was written and committed on 15 October at the repository root — 188 lines of audience-facing documentation, carrying the docs convention's status line, and **linked from nothing**. It is now `docs/installation/06-what-the-setup-script-does.md`, listed in the map and therefore on the site.

- **Its links were rewritten for its new home.** The one in-tree reference became `../preparation/04-controller-computer.md`; the five that pointed out of the tree — `doc/setupRBR.md`, `doc/HEATING-DATA.md`, `doc/UPDATE-MECHANISM.md`, `doc/CONTROLLER-FILES.md` and `desktop/config.example.json` — are now **named in backticks rather than linked**. That is the convention this settles: the reader refuses to render a link that leaves the docs tree (it says so, rather than fetching something that is not product documentation), and a reader who does not live in a repository should not be sent to one. It matters most for the technical layer, where every document harvests from `doc/` or `AI/`.
- **`docs/README.md`** gained the page in the installer's role path, a row in the installation table, and a line in the Status paragraph. Nothing else in the map moved: the eighteen documents it lists as missing are exactly the eighteen that are missing, and the numbering of the five promised installation pages is untouched, because two written preparation documents link to `installation/01-installing-the-controller.md` by name.
- **`TODO-docs.md` is new** — the programme's working state: the order of work, the two items waiting on the world, and the conventions. It points at `docs/README.md` for per-page status rather than repeating it, and `AGENT.md` now points at it.
- **`tests/docs-reader-check.js` no longer asserts a page count.** It was asserting 29, and it reads the *published* documentation rather than the working tree — so it would have failed the moment the docs were pushed, and it passed all the while the new page was invisible. It now checks the shape: the first page, the last page, uniqueness, and a floor. The header says plainly that it tests `main`, not the working tree.

## The `docs/` tree is on the site at `/docs`, read live from the repository

Three files in `docs-reader/` — `index.html` (the page, its CSS, and the JavaScript half of the bridge), `docs.allspeak` (the reader) and `docs.json` (the Webson layout) — deployed to `/docs/` by one step in `deploy.sh` and in the deploy workflow, and **currently live**. No documentation is copied to the site; there is one copy of it, in the repository.

- **Rendering is this runtime's own markdown renderer** — the one the `docs/` tree's "one paragraph, one line" rule was written for.
- **The page list, the titles and the Prev/Next order come out of `docs/README.md`.** Its lists and tables hold the reading order, so a document added to the README appears on the site and nothing lists the pages a second time.
- **The status line is lifted out of each document** into a band above the text, and an unwritten document says it is unwritten rather than showing an error. A link that leaves the tree is reported rather than fetched.
- **The address bar follows the reader** — `/docs/#concept/02-what-rbr-is` — and Back and Forward work. The two halves are joined through the DOM, because AllSpeak for the browser has no JavaScript interop.
- **`tests/docs-reader-check.js`** drives the real reader in a DOM against the real runtime and the real documentation: page list, toolbar, deep links, and the three failure paths. It needs `jsdom`, which was installed but undeclared, so `package.json` now declares it.

## The dev server in this directory works again

`allspeak viz` here answered `503 Server handler not ready` to every request, because the CLI runs a project's own `server.allspeak` when it finds one and the copy here was from 27 September: its start-up update check fetched a URL that no longer exists, the `or` clause that caught the failure stopped the script before `on Files request` registered the handler, and nothing was ever served or reported. `server.allspeak` is now the published copy (byte-identical to `https://allspeak.ai/code/server.allspeak`), `.code-version` is gone with the check that needed it, and the trap is in `AGENT.md` along with a second one — a local `viz.html`/`edit.html` wins over the page the dev server serves.

# Noticed while in there

- **The Advance change of 11 October did not invalidate anything written.** The glossary's definition of Advance survives the settled semantics, and the settled rule still has to be *stated* in `operation/02`, which is unwritten: a note for that work, not a defect.
- **Two items are waiting on the world, not on us** — the battery TRV trial (five written documents to revisit, and two knock-ons for documents not yet written) and the current-measurement phase (settled design and install facts, for `technical/08`). Both are in `TODO-docs.md` with the detail, rather than in this file.
- **The local `edit.html` still shadows the served editor page, and its Restart button has nowhere to go** — `/restart` was removed from the server on 12 October. In practice the prompt never appears, because a process running the project's own copy always answers `OK`. `asedit.allspeak`, `asedit.json` and `edit.html` cannot be refreshed the way `server.allspeak` was: upstream no longer publishes them.
- **`resources/allspeak/README.md` documents a tool that is not here.** It names five `scripted*` files and a command to run one; not one of those files exists anywhere in the repository.
- **The AllSpeak build pinned at `/dist/allspeak.js` does not continue after an `on failure`.** It runs the clause and then stops the thread, exactly as `or` does, and reports nothing. Measured both ways on 2026-10-16: the same six-line script prints the statement after the clause only on the current build at `allspeak.ai`. Every `on failure` in this repository is therefore a silent stopping point, and promoting a newer build would make each one carry on where it used to stop — worth a look at what those clauses are followed by before you pin.
- **The local `./asdoc-check.py` is behind the published one**, which warns when a doc block's title runs past 100 characters and treats `code-outside-section` as an error. The checks are now published rather than shipped, so the choice is to refresh the copy here or drop it in favour of `https://allspeak.ai/code/tools/asdoc-check.txt`.
- **The repository is public and has live credentials committed to it** — `credentials.json`, `new-ui/credentials.json` (MQTT) and `rbrchat/credentials.json` (SMTP, not covered by `.gitignore`), all readable from `raw.githubusercontent.com`. Nothing about the reader made this worse, but the reader now depends on the repository staying public, so the two are connected.
- **`conversation/` is committed here and upstream's starter guidance says it should not be.** Left as it is — your record, your call — but the two documents disagree.
- **Bare URLs in the documentation are not linkified** by the renderer. The one URL in the tree sits inside a code fence, so nothing is broken; worth using `[text](url)` if a URL is ever written in prose.

# Verified, and not

**The reader: 48 checks, and the visual layer from screenshots.** `node tests/docs-reader-check.js` covers the page list, the toolbar, both halves of the bridge, deep links and the three failure paths — against the *published* documentation, since that is what the reader reads. The visual layer was checked from screenshots of headless Brave at 390×844 and 1280×900: the status band reads as a band, the reading measure is comfortable, prose arrives as real paragraphs, and no page scrolls sideways at either width. One fault came out of it and is fixed — the navigation buttons were separate flex items, so a phone stranded `Next →` below `← Previous`.

**The new installation page was rendered locally, under the pinned runtime**, because the reader cannot show an unpushed document: 1 `h1`, 7 `h2`, 14 `h3`, 3 code blocks, 2 blockquotes, 31 list items, a table, and two links that both stay inside the tree. Its screenshot is in `.scratch/docs-reader-shots/setup-script-page.png`.

**The dev server** was verified by asking it, not by reading it: `/viz.html` 200, the project's files 200, `/version` → `OK`, against the same file run on a free port answering 503 to everything.

**Still unchecked:** a real touch device, iOS Safari, how the reader *feels* on a phone, and whether the legacy editor at `/edit.html` does anything useful — nobody has opened it. One cosmetic nit is left alone: a long status line breaks inside the date on a narrow screen, because Chrome fills the line greedily and the hyphen is a break opportunity.
