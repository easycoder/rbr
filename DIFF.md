# What to do

- Deploy the PWA (`./deploy.sh`, or copy `new-ui/` to the controller), then reload the room page.
- No controller script changed.

# What changed

- The **simple room page's Advance button label is now 40px** — twice the 20px it was. It is the big square, so the label reads across the room; the widest line ("Advance" / "advance") measures 163px inside the 200px content box, so the square keeps its 240px size and neither label wraps beyond its two intended lines.
- The **full room view's Advance button is unchanged** at 14px: its label is a sentence ("Advance to next schedule period (18:00)") in a compact row, and doubling that would wrap it to three lines. Say if that view should grow too, and by how much.

# Tests

- `tests/ui/simple-view.spec.js` now asserts the 40px size and that the widest label line still fits inside the padding box.
- `simple-view` spec passes (2/2); the change is CSS only, so no other spec reaches it.
