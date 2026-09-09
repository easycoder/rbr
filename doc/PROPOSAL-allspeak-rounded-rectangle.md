# Proposal: a `roundedrect` type for the graphics domain

**Status:** RESOLVED — superseded by the core `shape` type (landed in AllSpeak; see below). Kept as the record of the consultation.
**Author:** RBR project (Graham)
**Date:** 2026-08-23 (updated 2026-08-27)
**Related:** `learn/reference/20-graphics.md` (Python graphics domain), `desktop/` (RBR desktop app that motivated this)

## Resolution (2026-08-27)

AllSpeak now provides a generic **`shape`** variable type with subtypes — `rect`, `roundrect`, `ellipse`, `circle` — plus styling (`radius`, `fill`, `border`, `borderwidth`). See `learn/`. This delivers the core ask below (a declarative rounded-corner element) more generally than the original proposal, so **no further core addition is needed** and the desktop app's rounded corners can move from QSS strings to `shape`/`roundrect` at leisure.

## Original proposal (2026-08-23, for the record)

## Motivation

The Python graphics domain (`use graphics` / `init graphics`, PySide6) has no declarative element for a **rounded-corner rectangle**. The widget types are functional containers and controls (`window`, `layout`, `group`, `label`, `pushbutton`, `panel`, `dialog`, …) — none of them is a shape you can style as a rounded card.

Today the only way to get rounded corners is to embed a QSS stylesheet in a script:

```as
set the stylesheet of Card to `background-color: #FFFFFF; border-radius: 16px;`
```

This works (the RBR desktop app's room cards and the old RBR UI both use it), but it has real drawbacks:

1. **It is not declarative.** Rounded-ness lives in a style string, invisible to the compiler, undocumented in the language, and unthemeable at the type level.
2. **It is bolted onto other types.** `panel`/`group`/`label` mean "container/text", not "rounded shape"; styling one into a card overloads its semantics.
3. **It cannot be inspected or extended.** No `radius of X`, no per-corner radius, no border-width concept exposed to scripts.

The RBR desktop app — a PWA-mirror UI of white rounded cards on a light page — needs rounded containers everywhere, and the "what primary elements do you see" principle says a rounded card is a primary element worth a name of its own. If a generally-useful type like this stays plugin-side, every project re-implements it in QSS strings.

## Proposed vocabulary

### `roundedrect {name}` — declare a rounded-rectangle element

```as
roundedrect Card
```

### `create RoundedRect …` — make one

```as
create Card radius 16 color `#FFFFFF` border `#ECECEC` width 1
```

Attributes (all optional):
- `radius {n}` — corner radius in pixels (default 12)
- `color {color}` — fill colour (default white)
- `border {color}` — border colour (default none)
- `width {n}` — border width in pixels (default 0)

Like `panel`, a `roundedrect` is a container: `add {widget} to {roundedrect}` places children inside it, and it can be added to a layout. The rounded corners clip the children, so cards can hold labels, buttons, and text without square corners poking out.

### `set the radius/color/border of {roundedrect} to {value}`

Runtime updates for theming (e.g. a heating card turning accent-orange).

## Design principles

1. **A shape, not a canvas.** `roundedrect` is a single declarative shape with a fill and a border — it does **not** introduce arbitrary path drawing, gradients, or a paint API. Those are a separate, much larger feature.
2. **Container semantics.** The RBR use-case is a rounded *card* that hosts content; making `roundedrect` a container (like `panel`) covers both "decorative shape" and "styled card" with one type.
3. **QSS underneath, vocabulary on top.** The implementation is a thin wrapper over the same QSS `border-radius` the workaround uses today — no new rendering machinery, no PySide6 dependency change. The point is that scripts say *what* (a rounded card) instead of *how* (a style string).
4. **Extensible later.** `radius` per corner (`radius top-left 8 …`), gradients, and shadows can be added as optional attributes without breaking existing scripts.

## Example

```as
use graphics
roundedrect Card
label Title
pushbutton More

init graphics

create Card radius 16 color `#FFFFFF` border `#ECECEC` width 1
create Title text `Kitchen`
create More title `Details`
add Title to Card
add More to Card
```

## Scope and non-goals

- **In scope:** a declarative rounded container (fill, border, radius), create/set support, container behaviour, children clipped to the rounded shape.
- **Not in scope:** free-form painting, arbitrary paths, gradients, rounded-rectangle *drawing* outside a container (e.g. a `rect`-style shape with no children) — a follow-up could add a bare shape variant if a real need appears.
- **JS/Webson runtime:** this proposal targets the Python graphics domain only, where the gap exists; the web runtime already has CSS `border-radius`.

## Consultation request

This is the first "promote a generally-useful RBR type to the core pack"
request. Before submission to the AllSpeak project, the RBR maintainers
would like:

- confirmation that `roundedrect` (a rounded container) is the right
  shape for the core pack, versus a bare decorative shape or a `shape`
  base type with `roundedrect` as one variant;
- agreement on the vocabulary (`roundedrect`, `radius`, `color`,
  `border`, `width` — or `corner`/`fill`/`stroke` if those read better);
- a decision on whether `roundedrect` should be a `panel`-like container
  or a pure shape in v1.

The RBR desktop app (`desktop/`) will keep using QSS `border-radius`
until this is settled; nothing in the app depends on the proposal landing.
