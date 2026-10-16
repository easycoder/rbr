# AllSpeak Project — Agent Bootstrap

## Language

This is an **English** AllSpeak project. Communicate with the user in English. Generate AllSpeak scripts using English keywords.

## What is AllSpeak

AllSpeak is a scripting language designed to read like natural human language. Scripts use the `.allspeak` file extension. AllSpeak runs in the browser (JavaScript version) or from the terminal (Python version) — or both together.

AllSpeak uses an **AI-writes, human-reviews** workflow. The AI generates `.allspeak` code; the human checks that it reads sensibly and questions anything unclear. Use the full language — don't avoid a command because it might be unfamiliar. The human only needs to read it, not write it from memory.

## Reference — read this when writing AllSpeak

The complete AllSpeak language reference and idioms live at:

  **https://allspeak.ai/learn/**

The site has 20 reference files (`reference/`) and 15 idiom files (`idioms/`). When you need to look up syntax, runtime behaviour, or idiomatic patterns, consult it rather than relying on training data — AllSpeak's vocabulary doesn't always match what AI was trained on, and the curriculum corrects for that.

**Note that the curriculum describes current AllSpeak while this repository runs a pinned build of it.** The browser here loads `resources/allspeak.js`, promoted deliberately by `pin-allspeak.sh`, so it lags upstream by design: if the curriculum shows a command the scripts here do not already use, check the pinned copy before reaching for it. (Measured 2026-10-16: `loop` exists upstream and not in this bundle.)

**Read `learn/contents.md` first** — it is the canonical index of file paths. Use those exact paths when fetching specific files; do not guess slugs. (For example: the file is `learn/idioms/02-event-handlers-and-array-index.md`, not `02-event-handlers.md`.)

Recommended first reads:

- `learn/idioms/12-working-with-ai.md` — the AI-writes / human-reviews workflow and the common mistakes AI makes on AllSpeak.
- `learn/reference/16-doc-blocks.md` — the documentation convention used in every section of code (see "Required practices" below).
- `learn/reference/02-symbols-and-layout.md` — the four punctuation symbols and the lexical surface.
- `learn/reference/03-variables-and-arrays.md` — the cursor model that variables follow.
- `learn/reference/09-control-flow.md` — `if`, `while`, `gosub`, `stop`.
- `learn/idioms/01-cat-and-string-building.md` — `cat`, the single most common AI mistake.

## Required practices

Two practices apply to every piece of AllSpeak code written in this project, including the initial setup:

### 1. Doc blocks on every section

Every contiguous section of code is wrapped in a `!! … !!!` doc block, with prose explaining *why* the section exists.

**Open with one tight sentence on its own line**, then a bare `!!` paragraph break, then any further detail. This keeps Blocks-mode legible at a glance — the reader sees a summary, with the elaboration available below if they want more. Don't pile every detail into the first line; the code already shows the details.

Example:

```
!! Build the board: nine cells arranged as a 3x3 grid.
!!
!! Each cell is a div sized by the CSS-grid layout. A single click handler is shared by all cells; it reads `the index of Cell` to discover which one fired.

    div Cell
    set the elements of Cell to 9
    put 0 into N
    while N is less than 9 begin
        index Cell to N
        create Cell in Board
        add 1 to N
    end

    on click Cell gosub HandleClick
!!!
```

Add doc blocks **as you write** — not after. The prose forces you to state intent in plain language, which surfaces mistakes (a doc block saying "creates 9 cells" while the code creates 1 makes the mismatch obvious before you ever run it). See `learn/reference/16-doc-blocks.md` for the full convention.

Two further points of that convention, both of which trip up a first pass. **The opening sentence is the block's title** — what the editor's Blocks view lists down the left — so keep it under 100 characters and let the prose that follows carry the detail. And **a block contains its code**: the `@hash` lines and the `!!!` are the block's *tail*, so a terminator written before its code closes the section early and the code falls through the gap (`code-outside-section`). A file with no doc blocks is opt-out and fine; a file that has one must keep to it throughout.

After any code edit, refresh the hashes:

```
curl -fsS https://allspeak.ai/code/tools/asdoc-check.txt -o /tmp/asdoc-check.py
python3 /tmp/asdoc-check.py --write <file>
```

Upstream *publishes* that analyser rather than shipping it in the packs, so that no project holds a copy that has gone stale unnoticed (a `.py` travels as `.txt` because the site runs Python rather than serving it). This repo also keeps a pinned copy at `./asdoc-check.py`, refreshed from `~/dev/allspeak/tools/` — either will refresh the `@hash` lines so that future edits can detect drift between prose and code, but trust the published one when the two disagree.

### 2. Consult `learn/` before writing, not after

Before producing code that uses a feature you haven't already used in this project, fetch the relevant `learn/` file. Don't guess from training data — fetch the reference, read it, then write. This is especially true for: `cat` placement, failure clauses (`or` vs `on failure`), arrays of DOM elements (`create` must be inside a loop with the cursor set, not outside), and `set the content of` with markdown.

## Common mistakes to avoid

Even with the reference in front of you, AI tools reliably get these wrong on AllSpeak. Keep them in mind:

- **`cat` is infix.** It goes BETWEEN two values, never before the first.
  - ✓ `put \`Hello, \` cat Name cat \`!\` into Greeting`
  - ✗ `put cat \`Hello, \` cat Name into Greeting` (leading `cat` — parse error)
  - ✗ `put \`Hello, \` Name \`!\` into Greeting` (missing `cat` — no implicit concatenation)

- **No `for` or `for each` loops.** Use `while` with a counter, or a label-driven loop. See `learn/idioms/03-looping-patterns.md`.

- **Arithmetic uses keywords, not operators.** `add 1 to Counter`, not `Counter += 1` or `Counter = Counter + 1`.

- **No parentheses for grouping.** `(A + B) * C` doesn't exist. Compute into a temporary variable.

- **No `else if` shortcut.** `if … else if … else …` works (it's `else` followed by another `if`), but `elif` doesn't exist. No `case` / `switch` either.

- **Two failure clauses with different behaviour.** `or` runs the clause then stops the thread. `on failure` runs the clause then continues. See `learn/reference/10-errors-and-recovery.md`.

- **`gosub Label`, not `Label()`.** AllSpeak has no callable function syntax.

- **None of these exist:** `try`/`catch`, `break`, `continue`, `loop`, `return X` (value), `await`, `import` (other languages' meaning).

- **Every variable must be declared before use.** This includes scratch loop counters (`variable N`), not just the obvious data variables. Forgetting to declare a loop counter is a common first-pass mistake. Names start with a capital letter; camel case is the convention: `Counter`, `UserName`, `IsLoggedIn`.

- **All variables are global — no block-local scope.** Declaring a variable next to a label (`HandleClick:`) or inside an `if`/`while` body does not make it private to that block; it is shared across the whole script. The only way to get private state is a module (`learn/reference/12-modules.md`). A declaration must come before the statement that *writes* the variable — the compiler is single-pass — and a duplicate declaration is an error.

- **A handler is registered by executing the line.** An `on click` or `on message` written after the `stop` that ends a script's linear flow is never registered. Register handlers before the `stop`.

- **Strings are delimited by backticks.** No single or double quotes.

- **Floats are strings.** `3.14` is a four-character string, not a number. Use integer arithmetic with a scale factor — see `learn/idioms/05-floats-and-scaled-integers.md`.

When in doubt, consult `learn/` rather than guessing.

## First-time setup

> **Beginner tip:** If nothing happens when you start up, type **go**.

**IMPORTANT: On EVERY user message** (including "go", "hello", "start", or anything else), first check whether a file called `.allspeak-init` exists in this directory. If it does NOT exist, you MUST immediately run the initialisation process below — do not ask what the user wants, do not wait for further instructions, just start at step 1.

### Initialisation process

1. **Greet the user** and briefly explain what AllSpeak is — a scripting language that reads like plain English, designed so AI writes the code and the user reviews it.

2. **Ask the user for the project name.** This will be used as the script name and in filenames.

3. **Ask whether this is a command-line project, a GUI project, or both.**

4. **Create the project files** based on the answer:

   - **Command-line**: Create `<project>.allspeak` from the CLI template below.
   - **GUI**: Create `<project>.html`, `<project>-main.allspeak`, and `<project>.json` from the GUI templates below.
   - **Both**: Create all files.

5. **Create `.allspeak-init`** containing the project name and type (cli/gui/both) so this setup is not repeated.

6. **Explain to the user how to run their project:**

   - **CLI**: Run with `allspeak <project>.allspeak`.
   - **GUI**: Run with `allspeak viz [port]` (default port `8080`). It starts the AllSpeak dev server if one is not already up, and opens the visualiser at `http://localhost:<port>/viz.html`; the project's own page is at `http://localhost:<port>/<project>.html`, which you can open in a second tab. `allspeak server [port]` starts the same server and opens nothing, which is what you want when you are opening several pages yourself. Closing the server (Ctrl+C) closes the app. This single command is what gets baked into Start-menu shortcuts. The AllSpeak runtime is still loaded from the CDN; the server only serves project files.

7. **Walk the user through how the files work together.** For GUI projects, explain:

   - The HTML file is just a launcher — it loads the AllSpeak runtime and runs a tiny bootstrap script that fetches the main `.allspeak` file.
   - The `.allspeak` file is the program logic. It creates a body element, fetches the `.json` layout, and uses `render` to turn the JSON into real page elements. It then `attach`es to those elements by their `@id` to interact with them.
   - The `.json` file defines the page layout using Webson — a JSON format where keys like `#element` create HTML elements, `@id` (and any `@<name>`) set attributes, `#content` sets text, `$Name` defines named components, `#` lists children, and any other key is a CSS style. Full details in `learn/reference/14-browser-and-webson.md`.
   - This separation means the layout can be changed without touching the code, and vice versa.

   For CLI projects, explain that the `.allspeak` file is a standalone script run from the terminal, and walk through what each line does.

8. **Explain the editor.** Nothing of it lives in the project: the dev server serves the visualiser page itself, with the project's language filled in, so `allspeak viz [port]` gives you the editor and your app side by side — `/viz.html` in one tab, `/<project>.html` in another. The page opens, edits and saves `.allspeak`, `.json`, `.html` and other project files (the dev server provides the read and write routes), and the runtime it runs is the published one.

   This repository is the exception, and knowingly so: it still carries the pre-2026-10-12 editor (`edit.html`, `asedit.json`, `asedit.allspeak`) because a controller can be given those files by hand when someone needs to debug on the box. A local `edit.html` wins over the served page, so `localhost:<port>/edit.html` gives that older editor while `/viz.html` gives the current visualiser. See `AGENT.md` for what a stale `server.allspeak` does to the dev server.

9. **Ask what they'd like to build.** From here, just respond to what the user wants.

---

**If `.allspeak-init` DOES exist**, skip initialisation and proceed normally. Read `.allspeak-init` to learn the project name and type.

---

## CLI template

```
!   <project>.allspeak

    script <Project>

!! Entry point: log a greeting and exit. Replace this with the project's actual logic, keeping each contiguous code section wrapped in its own doc block.

    variable Message
    put `Hello from <Project>` into Message
    log Message

    exit
!!!
```

## GUI template

A GUI project uses three files:

- **`<project>.html`** — minimal HTML launcher
- **`<project>-main.allspeak`** — AllSpeak script (code)
- **`<project>.json`** — Webson layout (UI definition as JSON)

### `<project>.html`

```html
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><Project></title>
</head>
<body>
    <pre id="allspeak-script" style="display:none">
    variable Script
    rest get Script from `<project>-main.allspeak`
    run Script
    </pre>
    <script>
    (function() {
        var t = Date.now();
        var s = document.createElement('script');
        s.src = 'https://allspeak.ai/dist/allspeak.js?v=' + t;
        s.onload = function() { AllSpeak_Startup(); };
        document.head.appendChild(s);
    })();
    </script>
</body>
</html>
```

### `<project>-main.allspeak`

```
!   <project>-main.allspeak

    script <Project>

!! Boot the GUI: render the Webson layout into the body and attach to the elements the rest of the script will manipulate. Each subsequent section of code should get its own doc block.

    div Body
    variable Layout

    create Body
    rest get Layout from `<project>.json`
    render Layout in Body

    div Display
    attach Display to `display`
    set the content of Display to `Hello from <Project>`

    stop
!!!
```

### `<project>.json`

```json
{
    "#doc": "<Project> layout",
    "#element": "div",
    "@id": "page",
    "font-family": "sans-serif",
    "margin": "2em",
    "#": ["$Display"],

    "$Display": {
        "#element": "div",
        "@id": "display",
        "padding": "1em",
        "border": "1px solid #ccc",
        "min-height": "4em"
    }
}
```

In all templates, replace `<project>` with the project name (lowercase for filenames) and `<Project>` with the capitalised project name.

---

## Conversation logging

At the start of each new session (or when the user asks for a new conversation), create a new conversation log file `conversation/conversation-NN.md` where `NN` is the next available number. Use the format:

```
# Conversation NN — Brief title

Date: YYYY-MM-DD

---

## Summary

...
```

Append to the file as the conversation progresses, labelling each entry with the speaker and date.

---

## Language extension policy

If a needed construct does not exist in AllSpeak, **do not invent syntax**. Instead, pause and propose a new command to the user, keeping it consistent with AllSpeak's English-like style.
