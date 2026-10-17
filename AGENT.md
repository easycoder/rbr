# AGENT.md

This file provides guidance to agents when working with code in this repository.

## Project Summary

Room By Room (RBR) is an open-source smart central heating control system. It has three components:

1. **Controller** — Python/AllSpeak scripts running on Linux, that manage heating per-room via Zigbee thermometers and relays.
2. **UI** — A browser-based mobile webapp written in JavaScript/AllSpeak with Webson-rendered DOM, served from `index.html`
3. **REST server** — PHP on shared hosting (not in this repo)

Communication between controller and UI is via MQTT (broker: `rbrheating.duckdns.org`).

## Key Technologies

- **AllSpeak**: A high-level scripting language with both Python and JavaScript dialects. Scripts use the `.allspeak` extension. The Python runtime is in the AllSpeak repository. The JS runtime is loaded by the browser from this site's own `/dist/allspeak.js`, which is a **pinned build**: `resources/allspeak.js` is byte-identical to what `pin-allspeak.sh` has promoted, and the browser therefore runs that one, not the rolling CDN. Upstream AllSpeak moves ahead of it deliberately and only when someone promotes a build, so **a command that exists in the AllSpeak curriculum may not exist here yet** — check the pinned copy before reaching for a new one (measured 2026-10-16: `loop` is upstream but absent from the pinned bundle, and upstream's "does not exist" list has been trimmed to match). `ALLSPEAK.md` contains essential primer information for using the language.
- **Webson**: JSON-based DOM rendering. Layout definitions are in `resources/webson/*.json`. Element IDs in Webson must stay in sync with `.allspeak` scripts that attach to them.
- **MQTT**: All controller-UI communication. Broker `rbrheating.duckdns.org` (port 8883 for Python/controller, port 443 for the JS/UI websocket). Two accounts per system: the bridge on the box, whose password lives only in `/etc/mosquitto/conf.d/rbr-local.conf`, and the account the UI pages use, fenced to that system's topics and vended by `credentials.php` only to a paired device (MAC + token). The system's identity is `~/.mac_override` (currently `00:e0:27:5b:31:40`), not the NIC's MAC, and it is the topic namespace as well as the registration key in `rbr-users.json`.
- **Zigbee**: Used for controller-to-device communication

## Running

```bash
# Run the controller (checks for existing instance)
allspeak controller.allspeak

# The controller self-times 6 cycles of 10 seconds each, then exits.
# It is normally re-launched every 60 seconds, either by cron or a
# process supervisor — check which mechanism is in use on the target.
```

The UI is a static webapp — it has to be served over HTTP (not `file://`) because it fetches its scripts and Webson layouts by XHR, and it needs nothing else from a server. `allspeak viz [port]` starts the AllSpeak dev server (default port `8080`) if one is not already up, and opens the visualiser at `http://localhost:<port>/viz.html`; `allspeak server [port]` starts the same server and opens nothing, which is what you want when you are opening several pages yourself. Open `http://localhost:<port>/new-ui/index.html` for the new UI, or `http://localhost:<port>/index.html` for the legacy one; either prompts for the MQTT password on first use and stores it in localStorage. A plain `python3 -m http.server <port>` serves the same files when all you want is to look at a page, since nothing here needs anything but static hosting.

## Repository Structure

- `controller.allspeak` — Main controller script (AllSpeak Python dialect)
- `deviceControl.allspeak` — Device control logic: turns the controller's per-room decisions into HTTP calls on the local Zigbee bridge
- `simulator.allspeak` — Controller simulator for testing without hardware
- `resources/allspeak/` — JavaScript AllSpeak runtime modules (Core.js, Browser.js, Webson.js, etc.)
- `resources/allspeak/` — UI AllSpeak scripts (rbr.allspeak is main, plus mode/calendar/statistics/etc.)
- `TODO-docs.md` — where the documentation programme stands and what is left. It points at `docs/README.md`, which is the only place a page's status is recorded.
- `docs-reader/` — the documentation reader served at `/docs`. It is a page, an AllSpeak script and a Webson layout, and it holds no documentation: it fetches the Markdown from the public repository as it is read and renders it with this runtime's markdown renderer. See `tests/docs-reader-check.js`.
- `resources/webson/` — Webson JSON UI layout definitions
- `resources/css/`, `resources/icon/`, `resources/img/` — Static assets
- `map.json` — System map: rooms, thermometer MACs, device types, modes, timing schedules
- `params.json`, `environment.csv` — Simulator configuration (per-room thermal parameters and the outdoor-conditions envelope)
- `thermometers.json` — Live temperature readings, written by the controller and read by the simulator and dashboard
- `AI/` — Architecture and working rules documentation for AI contributors

## Working Rules

- **AllSpeak scripts are the source of truth for behavior** — make surgical changes, preserve command vocabulary and flow, prefer existing labels/subroutines
- **Webson JSON defines UI structure** — renaming element IDs requires matching changes in `.allspeak` scripts
- **No build tools required** — the system runs directly from source files
- If editing AllSpeak JS runtime modules, rebuild with `build-allspeak` in the allspeak repo
- Symlinks to AllSpeak sources can be refreshed with `relink-allspeak.sh`
- Prefer explicit state handling over hidden side effects
- Avoid modern JS syntax (`??`, optional chaining) for compatibility with older runtimes

## Configuration Data

- `map.json` — Physical system layout: room names, thermometer MACs, device types, operating modes (timed/boost/advance/on/off), temperature schedules per profile
- Multiple profiles (e.g., Weekday, Weekend) with an optional calendar mapping days to profiles

## AllSpeak Language Reference

The authoritative reference is the AllSpeak curriculum, `https://allspeak.ai/learn/` — 20 reference files and 15 idiom files. Start at `learn/contents.md`, which is the canonical index of paths (use those exact paths; do not guess slugs — the file is `idioms/02-event-handlers-and-array-index.md`, not `02-event-handlers.md`). Consult it rather than relying on training data: AllSpeak's vocabulary does not always match what AI was trained on, and the curriculum corrects for that. Load it *before* writing code that uses an unfamiliar feature, not after. `ALLSPEAK.md` in this repo holds the primer and the common-mistakes list.

Worth reading first, and already summarised in the traps above: `learn/reference/02-symbols-and-layout.md` (the lexical surface), `03-variables-and-arrays.md` (the cursor model), `08-strings-and-text.md` (slicing, `position of`, `replace`), `09-control-flow.md`, `14-browser-and-webson.md` (DOM, `attach`, the Webson dialect), `16-doc-blocks.md`, and `idioms/01-cat-and-string-building.md` — `cat` is the single most common AI mistake.

`/as-js` for JS dialect context, `/as-python` for Python dialect context and `/as-review` to check `.allspeak` files for syntax correctness are Claude Code commands, and they do not exist as skills in every agent environment — if they do not resolve, read the curriculum directly.

## Doc blocks — required for new `.allspeak` code

Every section of new `.allspeak` code is wrapped in a doc block:

    !! A one-line synopsis, and it is the section's title.
    !!
    !! What this section does and why it exists. One paragraph = one line;
    !! a bare `!!` line separates paragraphs.
    SomeLabel:
        ! the code
        return
    !! @hash <managed>      ← inserted by the analyser (don't write by hand)
    !! @verified <managed>  ← set by a reviewer's sign-off
    !!!                     ← required terminator (three bangs)

**A block contains its code.** The first line is its **title**, which is what the Blocks view lists down the left, so it must be a short synopsis and not the opening paragraph of the prose — `asdoc-check` warns past 100 characters. The `@` attributes and the `!!!` are the block's **tail**, so they come *after* the code: a terminator written before its code closes the section early, the editor shows a block with no script under it, and the code falls through the gap. The analyser reports that as `code-outside-section`.

Rules:
- Lead with the **why** or the design constraint, not a paraphrase of the code.
- **Use the convention properly or not at all.** A file with no doc blocks is opt-out and says nothing either way; a file that has one must keep to the convention throughout, because half a file of blocks is what makes the editor's view misleading. In a file that uses the convention, code outside any section is an **error**.
- **One paragraph = one line.** Each paragraph of prose is a single `!! ...` line, however long. Bare `!!` separates paragraphs. Don't insert hard line breaks for visual wrapping — they render badly in Blocks mode (which word-wraps the doc pane) and they fight you when editing. The flat-mode editor will show very long source lines; that's accepted, since the prose is meant to be read in Blocks mode and AI tools don't care about line length.
- Don't start a prose line with `@hash` or `@verified` — the parser treats those as metadata. Quote them ("@verified") if you must mention the names.
- **Explanatory comments belong in the block's prose, not in its code.** The code region carries short remarks — one to four lines, read *at* the statement they are about — and nothing longer. Anything that is design reasoning, a measurement, a trap or a history goes into the block's prose as an **appendix entry**, and its place in the code is a marker:

        !! Appendix
        !!
        !! §1 A note, as one paragraph on one line.
        !!
        !! §2 Another note.
            ! §1
            put 14 into DocAperture

  `§N` numbers **within the block**: §1 is the first appendix entry of *the block you are reading*. A reference to another block's entry therefore names the site rather than the number — *"see the note where the panel's width is set"*. A marker belongs **inline** on the label or statement below it (`HandleClick: ! §3`, `while N is less than Limit ! §7`) where that is safe, and on a `! §N` line of its own otherwise; never inline onto a line carrying an `@` attribute, because `!` ends an attribute. A `! ---- the toolbar ----` signpost is navigation and stays in the code where it points.
- After any code change inside a block, refresh hashes with `--write` (see below). Verifies that go stale show up as warnings — review the change and re-verify (asedit's Blocks mode has a one-click "Mark verified" button).

### Where the analyser lives

The convention has three implementations, all validating the same spec:

- **Canonical and always current, upstream:** `https://allspeak.ai/code/tools/asdoc-check.txt`. AllSpeak *publishes* its checks rather than shipping them in the packs, so that a project never holds a copy that has gone stale unannounced — a `.py` travels as `.txt` because the site runs Python rather than serving it:

      curl -fsS https://allspeak.ai/code/tools/asdoc-check.txt -o /tmp/asdoc-check.py
      python3 /tmp/asdoc-check.py --write <file>

- **Here:** `./asdoc-check.py` (Python CLI, recursive over a directory) and `./asdoc-check-cli.allspeak` (runs under the Python AllSpeak runtime). These are a **pinned copy** and they do drift — refresh them from `~/dev/allspeak/tools/` rather than editing them, and prefer the published one when a check has to be trusted. Measured 2026-10-16: the copy here predates the title-line check and the `code-outside-section` error, which makes it *quieter* than upstream rather than different in kind.
- **Browser-side** parsing lives inline in `asedit.allspeak` for the editor's in-process use.

`python3 ./asdoc-check.py <path>` lists the files that break the convention — existing files predating it are being fixed as they are found.

## Markdown documentation — one paragraph, one line

Applies to every `.md` file in this repo, and especially to the `docs/` tree.

The documentation is copied into a Doclet structure for easier (and remote) viewing, and the converter it uses renders each source line as its own HTML paragraph. A hard-wrapped paragraph therefore arrives as a column of one-line paragraphs instead of a single one.

- **One paragraph, one line.** A prose paragraph is a single unbroken line, however long; a blank line separates paragraphs. Never hard-wrap prose at a fixed column width.
- **One list item, one line.** Each bullet or numbered item is a single line, however long.
- **Keep the line structure that carries meaning.** Headings, tables (one row per line, plus the header separator), blockquotes and fenced code blocks each stay on their own lines.
- **The metadata blockquote is one line.** The `> **Audience:** … · **Status:** … · **Last verified:** …` line at the top of a document is a single blockquote line, not several hard-broken ones.

This is the Markdown counterpart of the `.allspeak` doc-block rule above ("One paragraph = one line"), and the reasoning is the same in both cases: the editor shows long lines, the reader sees real paragraphs, and the tools do not care about line length.

Existing `.md` files predate this rule and are still hard-wrapped. Reflow them as you touch them, taking care with indented code blocks, nested lists and callouts, whose layout must be preserved.

## Code review while documenting

When adding doc blocks to existing code, treat it as a review pass, not just a documentation pass. While reading each section closely enough to write its prose, also surface anything that looks off:

- **Unreachable symbols** — subroutines or labels with no caller; variables declared but never assigned, or assigned but never read.
- **Dead code** — branches that can never be taken; lines after an unconditional `stop`/`exit`/`return` that nothing jumps to.
- **Suspicious patterns** — duplicated logic that might want consolidating; hardcoded values that look like they should be variables; hidden coupling between sections (one writes a global the other quietly depends on).
- **Doc/code disagreement** — comments, names, or nearby docs that contradict what the code actually does.

Surface findings as a short list at the **start** of your response, separately from the doc-block edits. Don't silently fix them — let the user decide.

The point of the doc-block convention is to force close reading; reporting what that reading turned up is the natural payoff.

## Diagnostics while debugging

Reach for a log before reaching for a theory. `log` writes to the browser console, and the same line prints in the terminal runtime, so a script can tell you what it is actually doing rather than what you assume it is doing.

The reason to prefer a log over a dialog box is not that it is cheap — it is that it is **copyable**. A copied line can be quoted into a conversation, a bug report or a commit message, compared against earlier output, and read by somebody else; a dialog box leaves you to paraphrase it from memory, and that is where wrong ideas take hold. Be liberal with them, and cheerful about intrusive ones — they are not permanent. Remove each one once the question it was asked has an answer, and have each line name its own subject (`rooms: 8  relays: 3`) so the copy still makes sense on its own.

## Traps worth knowing before editing

Standing knowledge rather than next steps. Every one of these has cost real time in the AllSpeak projects, and each applies to the browser and controller scripts here.

- **`or` on a `rest get` stops the thread.** The rest of the section is abandoned; use `on failure` when the script has to carry on — and prefer the fallback that reports honestly over the one that papers over (`on failure set Config to \`{}\`` lets everything downstream run on broken assumptions).
- **But `on failure` does not carry on in the AllSpeak build pinned here.** It runs its clause and then stops the thread, exactly as `or` does: the statement after the clause never runs and nothing is reported. Measured 2026-10-16 against `resources/allspeak.js` — the same script run against the current build at `allspeak.ai` continues as the curriculum says it should, so this is the pinned build being old, not the language. Anything here that has to survive a failed fetch must be written `rest get X from URL or begin … go to Label … end`, which is the shape the controller scripts already use and which means the same thing on both builds. A script that silently stops at its first failure is the failure mode to watch for: the symptom is a blank pane and a quiet console, not an error.
- **A handler is registered by executing the line.** An `on click` or `on message` written *after* the `stop` that ends a script's linear flow is never registered — and a check that calls the handler by name will not notice. Both `resources/allspeak/rbr.allspeak` and `new-ui/resources/allspeak/shell.allspeak` deliberately register their handlers before the `stop` and put the runtime's own flow after it; keep that order when adding one.
- **`set the content of` writes `innerHTML`, so a message meant for a person must not carry markup.** A sentence that tells a reader to write `<page>` renders as nothing at all, because it is parsed as a tag and swallowed — the one thing the sentence exists for, silently gone. A placeholder in angle brackets wants a concrete example instead (`add '@app mypage.html' …`). And a check cannot see it: a stub element stores the string it is handed, while a browser parses it, so an assertion here has to be on what a reader *gets*.
- **`the text of` an element reads it by the *symbol's declared type*, not by the element's tag.** A `div` symbol takes `innerHTML` with every newline removed (a 2,700-line script read through one arrives as a *single line*); a `pre` keeps the newlines but returns escaped markup; a `textarea` reads `value`, which is the text and nothing else — that is what carries a script from an element into `run`.
- **A variable must be declared before the statement that *writes* it**, not merely before the section that reads it: the compiler is single-pass, so a declaration below the point where a handler is *registered* is not there yet. A duplicate declaration is an error.
- **All variables are global — there is no block-local scope.** A variable declared next to a label, or inside an `if`/`while` body, is still shared across the whole script.
- **`cat`'s right-hand side is the whole rest of the expression.** `left 4 of X cat newline` parses as `left 4 of (X cat newline)` — the newline is inside the value that `left 4 of` then truncates. Build a concatenation in steps when a value-producing keyword comes first.
- **A number that arrived as text stays text, and text compares lexically** — `9` is not less than `10`. Convert with `the value of`, or `add 0 to` when it is already in a variable. This bites hardest on values that came from a map, a form field or a URL.
- **`index X to N` selects a *slot*; `item N of X` and `element N of X` read from inside a JSON array.** `put V into item N of X` is not a valid target, and the two never overlap.
- **`element N of X` parses the whole array, and stringifies what it returns.** A json variable is held as *text*, so each indexed read is `JSON.parse(<the whole array>)[N]` plus a `JSON.stringify` when the element is an object: measured 2026-10-06 in the AllSpeak repo at **~15 ms per access on a 435 KB recording**, which makes **any loop over a json array quadratic in what it walks**. A map of this size is nowhere near that, but the shape to remember is *read it once, and cache a filtered copy rather than re-walking the original*.
- **A status code does not mean the file arrived.** A dev server can answer an unknown path with `200` and its own HTML page, so a fetch that matters should check its body for a leading `<` rather than trusting the response alone.
- **CORS is by file type, and only on some hosts.** The runtime is loaded from a CDN, but `.allspeak` scripts are fetched from this site's own origin (`resources/allspeak/…`, `new-ui/resources/allspeak/…`) — keep them there, and remember that a `.md` fetched from a third party arrives only if that host sends the header.
- **Never redirect stderr on a check whose stderr is its verdict.**
- **A project's own `server.allspeak` shadows the published dev server, and a stale one takes the whole server down.** The CLI honours a `server.allspeak` beside the project deliberately — *"a project that pins its own is asking for that copy"* — and fetches the published one only when the file is absent, so a copy kept here governs every `allspeak viz` in this directory. This repository keeps one on purpose, for the editor on a controller (see `doc/CONTROLLER-FILES.md`), and the copy it kept until 2026-10-16 answered **`503 Server handler not ready` to every request, for ever, saying nothing else**. Its own start-up update check fetches `https://allspeak.ai/code/code-version`, a URL that no longer exists; the `or` clause that catches the failure **stops the script** before `on Files request` registers its handler, and the framework answers 503 until a handler exists — which it never does. Measured 2026-10-16: the old copy answers 503 to `/viz.html` and `/version` on a free port all by itself. **Refresh that file from the published one rather than editing it** — `curl -fsS https://allspeak.ai/code/server.allspeak -o server.allspeak` — and copy the refreshed file to any controller that carries it too. `.code-version` is not needed by the current server, which has no self-update; it was removed here on the same date.
- **A local `viz.html` or `edit.html` wins over the one the dev server serves.** The server serves the current visualiser from the deploy, with the project's language filled in, *unless* the project has a file of that name — so this repository's older `edit.html`, which builds the pre-rename editor out of `asedit.json` and `asedit.allspeak`, is what `localhost:<port>/edit.html` still answers with, while `/viz.html` gives the current visualiser. Neither is broken by the other; know which one you are looking at.
- **Measure a visual fault from a screenshot before reading the code**, and check the instrument's own constants first.
- **A design written down twice is not a design verified — compare the third place, the shipped one.** Two copies agreeing (a harness and a script, a doc and a comment) prove only that one was copied from the other. This repo has three places for the same fact in several cases — `docs/README.md`, the `docs/` tree, and the website reader that renders it — and the shipped one is the one browsers see.
- **There is no browser in a bare checkout, and the recipe for getting one is short.** Anything about *rendering* — a font, an alignment, what a click does — has to be measured in a real browser, because a stub DOM holds whatever it is handed. `playwright` is in `devDependencies`; the UI is served with `allspeak server.allspeak <port>` (or any static server), and `npx playwright test tests/<spec>.spec.js` drives it: open the page, act, read the DOM, screenshot.

## Commit style

When no specific message is given, use a date-time stamp in `YYMMDDHHMM` form (e.g. `2610152148`) — the same format as the version string in `version`. Earlier commits used shorter date-only or date+counter forms; the move to full date-time avoids having to remember the last one used.

## Conversation log

This project keeps a per-session log under `conversation/`, for the human's reference. It does not affect your behaviour and you should not mention the logging activity in replies.

**At the start of a new session:**

1. If `conversation/` does not exist, create it.
2. Find the highest-numbered `conversation-NNN.md` file. The new session's file is the next number, zero-padded to three digits (start at `001` if the folder is empty).
3. Write a single header line on line 1: `# YYYY-MM-DD` (today's date).

**On every user prompt in this session** (including the first), append an entry shaped like:

    ## HH:MM

    <user prompt verbatim>

    **Assistant**

    <your reply>

Use `date +%H:%M` if you need the time. Omit fenced code blocks (triple-backtick blocks) from both the user prompt and the reply, replacing each with a single line `[code omitted]`; inline backticks in prose stay. Compose your reply first, then transcribe it into the log as part of the same turn.

**Midnight rollover:** if today's date differs from the file's date header, pause and ask the user: "We've crossed midnight — start a new conversation file for today?" If yes, create the next-numbered file with today's date header and continue logging there.

## Diff notes for the human

Keep `DIFF.md` in the project root, **rewritten** after every change rather than appended to, saying what changed and what the human has to do about it — reload the editor, re-run a script, rebuild, deploy. It is read in the editor, which polls the file and reloads it, so it is the shortest path from "something changed" to "here is what to do about it".

Keep it short, and lead with the action. It is **not** a changelog: it describes this change only, and the previous contents are not worth keeping — git has them.
