# What to do

- Restart RBR Studio and reload the 9 November journal scenarios. The PWA lines now name the event they carry — Advance, Cancel Advance, Schedule, Calendar, Boost, System Name, and the rest of the controller's request types — and the two schedule saves say what changed.
- Other journal days re-convert if you want the same; existing scenarios without the new field fall back to their labels.

# What changed

- `journal_to_scenario.py` writes `user.event` from the controller request: **Operating Mode** → Advance, Cancel Advance, Boost, Target or Mode; **Update Profiles** → Schedule (schedule screen), Calendar (profiles/calendar screen) or Update Profiles; **Select Profile** → Calendar; **System Name**, **Request Relay**, **Add Room**, **Update Rooms**, **Room Override**, **Backup**, **Backup Now**, **Journal Now** and **Test** keep their names.
- The table's Event column uses the event; the actor is PWA; older scenarios without `event` map their labels to the same names.
- A schedule save's label names the changed period and temperature. In the Sunroom, `s131` is **Schedule saved — Weekend 17:00–19:00: 22.5 → 22.0 °C** and `s133` is **22.0 → 22.5 °C**. The Advance at `s75` is unchanged.
- The scenario schema accepts `user.event`; the 9 November full-day and Sunroom scenarios are regenerated.

# Try it

- The Sunroom: `s75` PWA/Sunroom/**Advance**, `s131` and `s133` PWA/Sunroom/**Schedule** with the changed period in the label, and `s136` PWA/Sunroom/**Cancel Advance**. The full day has five user steps.
