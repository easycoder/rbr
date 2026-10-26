# 2026-10-26

## 10:10

Problem thi morning - it seems to be ignoring the calendar and using the selected profile insted.

**Assistant**

Confirmed and fixed — and the live system has been repaired.

The cause: the calendar stores profile *names*, and the profile list stores the profiles themselves. Renaming a profile in the Profile sheet changed only the list. Your weekday profile is now called **Weekday**, but the calendar's Mon–Fri entries still said **Monday-Friday**. That name resolves to no profile, so both the controller and the page fell back to the selected profile — **All Off** — without saying so. Over the weekend the calendar's "Weekend" entry still matched, which is why it worked on Saturday and Sunday and broke on the first weekday morning.

Repair already done on the live system: Mon–Fri now point at **Weekday**; the header reads "TODAY'S PROFILE Weekday" and the rooms show the weekday schedule again.

Code fix: a rename now moves every calendar day that named the old profile to the new name; a delete clears the days that named the deleted profile; a duplicate profile name is refused (a name is how a profile is referenced); a day naming a profile that does not exist is shown as "Name (missing)" instead of looking ordinary; and the controller logs when it has to fall back. `tests/pwa-profile-sheet-check.js` drives the real sheet — it failed against the old module in 7 places. `npm run check` and the unit suite pass.

`DIFF.md` says to deploy the PWA; the desktop app's profile manager has the same rename gap, unexercised and left alone.
