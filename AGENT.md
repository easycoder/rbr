# AGENT.md

This file provides guidance to agents when working with code in this repository.

## Project Summary

Room By Room (RBR) is an open-source smart central heating control system. It has three components:

1. **Controller** — Python/AllSpeak scripts running on Linux, that manage heating per-room via Zigbee thermometers and relays.
2. **UI** — A browser-based mobile webapp written in JavaScript/AllSpeak with Webson-rendered DOM, served from `index.html`
3. **REST server** — PHP on shared hosting (not in this repo)

Communication between controller and UI is via MQTT (broker: `rbrheating.duckdns.org`).

## Key Technologies

- **AllSpeak**: A high-level scripting language with both Python and JavaScript dialects. Scripts use the `.as` extension. The Python runtime is in the AllSpeak repository. The JS runtime modules are loaded from `allspeak.js` via CDN. `ALLSPEAK.md` contains essential primer information for using the language.
- **Webson**: JSON-based DOM rendering. Layout definitions are in `resources/webson/*.json`. Element IDs in Webson must stay in sync with `.as` scripts that attach to them.
- **MQTT**: Used for all controller-UI communication. Broker is `rbrheating.duckdns.org` (port 8883 for Python/controller, port 443 for JS/UI websocket). Auth: username `rbr`, password from `~/.mqtt_password`. Controller ID from `~/.mqtt_userid` (must match target device MAC, currently `38:54:39:34:62:d7/request`).
- **Zigbee** and **RBR-Now** (legacy): Used for controller-to-device communication

## Running

```bash
# Run the controller (checks for existing instance)
allspeak controller.as

# The controller self-times 6 cycles of 10 seconds each, then exits.
# It is normally re-launched every 60 seconds, either by cron or a
# process supervisor — check which mechanism is in use on the target.
```

The UI is a static webapp — must be served via HTTP (not `file://`) because it uses XHR to load scripts. Run `allspeak server.as <port>>` and open `http://localhost:><port></index.html`. The UI prompts for the MQTT password on first use and stores it in localStorage.

## Repository Structure

- `controller.as` — Main controller script (AllSpeak Python dialect)
- `deviceControl.as` — Device control logic for RBR-Now relay/thermometer devices
- `simulator.as` — Controller simulator for testing without hardware
- `resources/allspeak/` — JavaScript AllSpeak runtime modules (Core.js, Browser.js, Webson.js, etc.)
- `resources/as/` — UI AllSpeak scripts (rbr.as is main, plus mode/calendar/statistics/etc.)
- `resources/webson/` — Webson JSON UI layout definitions
- `resources/css/`, `resources/icon/`, `resources/img/` — Static assets
- `RBRNow/` — MicroPython firmware for ESP32 devices (master/slave networking via ESP-Now)
- `rbr_ui/`, `rbrconf/` — Python GUI tools for configuration
- `config.json` — RBR-Now device network configuration (SSIDs, MACs, pin mappings)
- `map.json` — System map: rooms, thermometer MACs, device types, modes, timing schedules
- `params.json`, `devices.json`, `thermometers.json` — Simulator configuration files
- `AI/` — Architecture and working rules documentation for AI contributors

## Working Rules

- **AllSpeak scripts are the source of truth for behavior** — make surgical changes, preserve command vocabulary and flow, prefer existing labels/subroutines
- **Webson JSON defines UI structure** — renaming element IDs requires matching changes in `.as` scripts
- **No build tools required** — the system runs directly from source files
- If editing AllSpeak JS runtime modules, rebuild with `build-allspeak` in the allspeak repo
- Symlinks to AllSpeak sources can be refreshed with `relink-allspeak.sh`
- Prefer explicit state handling over hidden side effects
- Avoid modern JS syntax (`??`, optional chaining) for compatibility with older runtimes

## Configuration Data

- `map.json` — Physical system layout: room names, thermometer MACs, device types, operating modes (timed/boost/advance/on/off), temperature schedules per profile
- `config.json` — RBR-Now network: device roles (master/slave), SSIDs, pin assignments, relay/LED config
- Multiple profiles (e.g., Weekday, Weekend) with an optional calendar mapping days to profiles

## AllSpeak Language Reference

Use `/as-js` for JS dialect context and `/as-python` for Python dialect context. Use `/as-review` to check `.as` files for syntax correctness.

## Doc blocks — required for new `.as` code

Every section of new `.as` code must be wrapped in a doc block:

    !! Brief explanation of what this section does and why it exists.
    !! Use multiple lines as needed. A bare `!!` line is a paragraph break.
    SomeLabel:
        ! the code
        return
    !! @hash <managed>      ← inserted by the analyser (don't write by hand)
    !!!                     ← required terminator (three bangs)

Rules:
- Lead with the **why** or the design constraint, not a paraphrase of the code.
- **One paragraph = one line.** Each paragraph of prose is a single `!! ...` line, however long. Bare `!!` separates paragraphs. Don't insert hard line breaks for visual wrapping — they render badly in Blocks mode (which word-wraps the doc pane) and they fight you when editing. The flat-mode editor will show very long source lines; that's accepted, since the prose is meant to be read in Blocks mode and AI tools don't care about line length.
- Don't start a prose line with `@hash` or `@verified` — the parser treats those as metadata. Quote them ("@verified") if you must mention the names.
- After any code change inside a block, refresh hashes with `python3 ./asdoc-check.py --write <file>`. Verifies that go stale show up as warnings — review the change and re-verify (asedit's Blocks mode has a one-click "Mark verified" button).
- A file with no doc blocks at all is treated as opt-out (no errors, no warnings). Adopt the convention file-by-file as you touch them.

Both implementations of the analyser validate the same convention:
- `./asdoc-check.py` — Python CLI, recursive over a directory
- `./asdoc-check-cli.as` — runs under the Python AllSpeak runtime
- (browser-side parsing also lives inline in `asedit.as` for the editor)

## Markdown documentation — one paragraph, one line

Applies to every `.md` file in this repo, and especially to the `docs/` tree.

The documentation is copied into a Doclet structure for easier (and remote) viewing, and the converter it uses renders each source line as its own HTML paragraph. A hard-wrapped paragraph therefore arrives as a column of one-line paragraphs instead of a single one.

- **One paragraph, one line.** A prose paragraph is a single unbroken line, however long; a blank line separates paragraphs. Never hard-wrap prose at a fixed column width.
- **One list item, one line.** Each bullet or numbered item is a single line, however long.
- **Keep the line structure that carries meaning.** Headings, tables (one row per line, plus the header separator), blockquotes and fenced code blocks each stay on their own lines.
- **The metadata blockquote is one line.** The `> **Audience:** … · **Status:** … · **Last verified:** …` line at the top of a document is a single blockquote line, not several hard-broken ones.

This is the Markdown counterpart of the `.as` doc-block rule above ("One paragraph = one line"), and the reasoning is the same in both cases: the editor shows long lines, the reader sees real paragraphs, and the tools do not care about line length.

Existing `.md` files predate this rule and are still hard-wrapped. Reflow them as you touch them, taking care with indented code blocks, nested lists and callouts, whose layout must be preserved.

## Code review while documenting

When adding doc blocks to existing code, treat it as a review pass, not just a documentation pass. While reading each section closely enough to write its prose, also surface anything that looks off:

- **Unreachable symbols** — subroutines or labels with no caller; variables declared but never assigned, or assigned but never read.
- **Dead code** — branches that can never be taken; lines after an unconditional `stop`/`exit`/`return` that nothing jumps to.
- **Suspicious patterns** — duplicated logic that might want consolidating; hardcoded values that look like they should be variables; hidden coupling between sections (one writes a global the other quietly depends on).
- **Doc/code disagreement** — comments, names, or nearby docs that contradict what the code actually does.

Surface findings as a short list at the **start** of your response, separately from the doc-block edits. Don't silently fix them — let the user decide.

The point of the doc-block convention is to force close reading; reporting what that reading turned up is the natural payoff.

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
