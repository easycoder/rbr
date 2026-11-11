# What to do

- Restart RBR Studio.

# What changed

- On the **Scenarios** tab the shared log panel (Log, Wire, Console, Artifacts and the selected step's Step details) now sits below the whole library/table splitter and spans the page width.
- The four row-editing buttons (**Duplicate…**, **Duplicate for room…**, **Rename…**, **Delete rows**) stay on the left at the bottom of the library column, directly above the log panel.
- The **Show** tab is unchanged: the log stays under the table, beside the viewer.
- `tests/studio-shell-check.py` now checks that the Scenarios log matches the page width and that all four buttons sit above it. Measured in the check: the log is 976 px of the 986 px page.
- `README.md` and `docs/SPEC.md` describe the new placement.

# Try it

- Open **Scenarios**: the bottom panel should run the full window width, with the four buttons just above it on the left. Switch to **Show** and the log should still sit under the table beside the viewer.
