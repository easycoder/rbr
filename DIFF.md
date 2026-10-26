# What to do

- **Repair the live calendar now.** Your calendar says Mon–Fri → `Monday-Friday`, but there is no profile by that name any more — it is called `Weekday`. Until those five days are reassigned, every weekday falls back to the selected profile (`All Off`, as it did this morning). In the app: Profile → Calendar → tap Mon → pick `Weekday`; repeat for Tue–Fri; Save. I can do this for you if you prefer.
- **Deploy the PWA** (`./deploy.sh --release`) and reload it once. The service worker is network-first, so no double reload is needed. The controller change travels in the same release; no map or broker change.
- **Carried over from the earlier docs session, still uncommitted:** commit and push the new `docs/technical/01-architecture.md`; the `/docs` reader reads `main`, so the page appears about five minutes after the push.

# What changed

The Profile sheet stored profile names in two places — the profile list itself and every calendar day — and a rename changed only the list. The calendar's days kept the old name, resolved to no profile, and fell back to the selected profile silently. That is what happened here: the weekday profile was renamed from `Monday-Friday` to `Weekday`, the Mon–Fri calendar entries stayed on `Monday-Friday`, and the first weekday morning ran the selected `All Off` profile — no heat.

A rename now moves every day that named the old profile to the new name, and a delete clears the days that named the deleted profile (unless another profile still has that name). A duplicate profile name is refused, as the Devices sheet refuses a duplicate room name, because a name is how a profile is referenced. A day naming a profile that does not exist is shown as `Name (missing)` in the accent colour instead of looking ordinary, and the controller now logs `Calendar: today's profile "…" is not in the profile list — using the selected profile` when it hits one — the silence was what made this take a morning to find.

`tests/pwa-profile-sheet-check.js` drives the real sheet in the real runtime: it renames and deletes through the sheet's buttons, checks the whole `calendarData` array the shell ships, checks a duplicate is refused, and checks the `(missing)` marker. It is in `npm run check`. The module's reply was wrong against the old code in 7 places.
