# Proposal: virtual-keyboard legend sizing + window-width keyboard

**Status:** PROPOSED — for upstream discussion in the AllSpeak project **Author:** RBR project (Graham) **Date:** 2026-08-30 **Related:** `allspeak/as_keyboard.py` (Python runtime virtual keyboard), `desktop/` (RBR desktop app that surfaced this)

## Problem

The virtual keyboard's key legends overflow their buttons, and the keyboard ignores the host window's width:

1. **Legend overflow.** `KeyboardButton` sizes its font from the key **height** only (`as_keyboard.py`, `KeyboardButton.__init__`):

   ```python
   self.setFixedSize(int(width), int(height))
   self.setFont(QFont('Arial', max(10, int(height) // 2)))
   ```

   With `VirtualKeyboard.buttonHeight = 42` that is a 21 px font on every key, regardless of the legend. Single letters fit, but the wide-legend keys — `Shift`, `Back` (1.5×42 = 63 px wide), `Space`, `Enter`, `123/#+=` — overflow their fixed-size buttons (e.g. `123/#+=` is ~72 px of text at 21 px).

2. **Fixed width.** The keyboard dialog is hard-coded to 500 px (`as_keyboard.py`, `Keyboard.__init__`):

   ```python
   dialog.setFixedWidth(500)
   ```

   On windows narrower than 500 px it overflows sideways (the RBR landscape window is 450 px); on wider windows it sits centred with unused space instead of filling the window.

## Proposed changes

### 1. Legend-aware font sizing (`KeyboardButton.__init__`)

Fit the font to the legend, shrinking from the height-derived size until the text fits the button width:

```python
font = QFont('Arial', max(10, int(height) // 2))
fm = QFontMetrics(font)
padding = 6
while font.pointSize() > 8 and fm.horizontalAdvance(text) > int(width) - padding:
    font.setPointSize(font.pointSize() - 1)
    fm = QFontMetrics(font)
self.setFont(font)
```

This keeps the current look for single letters and shrinks only the wide legends until they fit — no key sizes change.

### 2. Window-width keyboard (`Keyboard.__init__`)

Size the dialog to the caller window **only where that is appropriate**: in portrait (the window fills the screen, so a centred 500 px keyboard leaves awkward side gaps) or when 500 px is too wide for the window. On a wide landscape window the keyboard stays a compact, centred 500 px rather than taking over the whole window:

```python
width = 500
if caller is not None:
    if caller.height() > caller.width() or caller.width() < 500:
        # portrait, or the fixed width would overflow the window
        width = max(420, caller.width() - 20)
dialog.setFixedWidth(width)
```

The keypad rows already distribute extra horizontal space via their `Expanding` stretch spacers (`VirtualKeyboard._stretch`), so a wider dialog spreads the keys across the full window — no per-key width logic needed. The 420 px floor matches the minimum content width of the letter rows (10 × `buttonHeight`).

## Scope / non-goals

- No changes to the keypad layout, legends, or interaction (typing, shift, back, enter semantics all unchanged).
- Key size scaling on very wide screens (e.g. `buttonHeight` derived from window width) is explicitly out of scope for this change — the stretch spacers already fill the width.
- The RBR app itself cannot work around either issue: the keyboard is a core widget in `allspeak/as_keyboard.py`, shared by every AllSpeak graphics app.

## Verification (suggested)

- Offscreen/desktop: open the keyboard on a sheet with an input; confirm `123/#+=`, `Shift`, `Back`, `Space`, `Enter` legends fit their buttons at every window width from 420 to 500+ px.
- Portrait window (e.g. 800 wide): keyboard spans the window width.
- Landscape window 500+ px wide (e.g. 675): keyboard stays a compact centred 500 px, not full-width.
- Narrow landscape window (< 500, e.g. 450): keyboard shrinks to fit (≤ window width), no sideways overflow.
