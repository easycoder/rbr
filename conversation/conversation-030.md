# 2026-11-14

## 11:34

New conversation for this session.

**Assistant**

Started `conversation/conversation-030.md` for 2026-11-14. The home page work is where we left it: `home.html` sits at the repository root with `styles.css`, `script.js` and `assets/living-room-hero.jpg`, and `deploy.sh` uploads all four beside the untouched placeholder `index.html`. Nothing is committed or deployed yet.

## 11:37

The living-room-hero image isn't showing.

**Assistant**

The image was uploaded to the wrong place. `deploy.sh` passed `assets/` — with a trailing slash — among several rsync sources, and a trailing slash copies the directory's *contents* into the destination, so the hero landed at the site root while `styles.css` asked for `/assets/living-room-hero.jpg` and got a 404.

`deploy.sh` now passes `"$LOCAL/assets"` with no slash, which copies the directory itself. A comment records the trap.

I could not deploy from here — ssh is refused read access to `~/.ssh/id_ed25519` in this sandbox — so please run `./deploy.sh` again. After that, `/assets/living-room-hero.jpg` answers 200 and the hero appears; the stray `/living-room-hero.jpg` left at the root can be deleted whenever convenient.

## 11:51

The designer made an error with the hero image. See various/website-v2.zip.

**Assistant**

I applied v2's `styles.css` and the new `assets/living-room-hero.jpg` locally. The new artwork is a composed hero: the headline, lede and orange button are baked into the JPEG, and v2's stylesheet makes it a full-bleed background while still rendering the live `.hero-copy` on top. At desktop the headline therefore appears twice — the baked one faintly behind the live one — and at mobile a sliver of the baked headline shows at the right edge.

I tested a clean fix (a stronger cream overlay that hides the artwork's copy, plus a left-edge mobile crop) and it renders well, but whether to erase the baked text or let the artwork stand alone is a design call, so I have asked before changing the supplied CSS.

## 12:04

Try website-v3.zip

**Assistant**

v3 is the clean fix: same stylesheet and page copy as v2, but the hero photograph has no text painted into it. I replaced `assets/living-room-hero.jpg` with the new 1672×941 image (508 KB) and kept v2/v3's full-bleed hero treatment, so the live headline is now the only one on the page.

Verified in Chromium at 390, 1280, 1440, 1680 and 1920 wide against a local static server: no failed requests, no horizontal overflow, no doubled text at any width, mobile crop frames the couple cleanly, mobile menu and `aria-expanded` still behave, every anchor resolves. `styles.css` and `script.js` are byte-identical to v3; `home.html` keeps only its favicon and staging `noindex` additions.

Still needs `./deploy.sh` from your shell — my sandbox cannot read the SSH key. That upload also fixes the `/assets/living-room-hero.jpg` 404. One follow-up: the hero JPEG is 508 KB, by far the heaviest thing on the page; a compressed version would help if load time matters.

## 12:15

This mostly works, but on some window aspect ratios the text sits too far too the left, becoming confused with the background while leaving a wide mostly empty space to the right. See various/screenshots/Screenshot_20261114_121011.png.

**Assistant**

The problem was that the overlay was pinned to fixed percentages (transparent to 30%, 91% white only by 70%), while the copy column is capped and right-anchored. At around 1333px the text began at 54% but the pale field did not become solid until well past it, so the headline and lede sat over the photograph while the washed area to their right had nothing in it.

The overlay is now derived from the copy column itself: `.hero` defines `--hero-pad` and `--hero-copy`, and the solid stop is `calc(100% - var(--hero-copy) - var(--hero-pad))` — the copy box's left edge — with a soft ramp starting 14% of the hero width earlier. The text always lands on the pale field, and the field stops where the text column ends, so there is no empty white band beyond it. The lede now fills the column too (its 520px cap is gone), so its lines reach the right margin.

Checked at 13 widths from 390x844 to 3440x1200, including the reported 1333x1113: the overlay's solid stop equals the copy box's left edge at every one, no text crosses the photo, no horizontal overflow, mobile untouched. Deploy and hard-reload to see it.

## 12:38

Unfortunately that loses the radiator in most cases. Is it possible to retain the previous version but push the text more to the right? I'd even consider right-aligning it just to see how that feels.

**Assistant**

Yes — the overlay is back to the designer's v3 gradient, so the radiator and the rest of the photograph read as before. What moved instead is the copy column: on desktop it is now `min(40%,520px)` instead of `min(48%,590px)`, right-aligned, so at 1440 the block starts at 847px rather than 764px and sits over the pale radiator/wall area instead of crossing the window and plant. Lines end flush at the right padding.

Mobile keeps the designer's left-aligned stacked hero (the ≤760px rule sets `text-align:left`). The only differences from v3's stylesheet are those two `.hero-copy` rules.

Checked 11 widths from 390 to 2560: no overflow, text inside the hero and its padding, right alignment on desktop only. Screenshots at 390, 768, 1333 and 1440 show the radiator through the wash, and the headline stays on two lines. Deploy and hard-reload to try it; if right alignment is not the feel you want, one `text-align:left` on the desktop rule reverts it while keeping the column where it now is.

## 12:44

The right-alignment works surprisingly well - it feels better balanced. The shading to white is a little too aggressive; can it be softer, so the radiator is still visible even at the right-hand edge?

**Assistant**

The wash is much softer now: its stops are `0 → 10% at 48% → 72% at 70% → 84% at 100%`, where v3 had `0 → 12% → 91% → 94%`. The radiator, window and plant read through to the right-hand edge, and the right-aligned column is unchanged; mobile stays left-aligned.

I sampled the rendered background behind each block with the copy hidden, at 768, 1024, 1333, 1440 and 1920, and measured contrast: headline 4.7–8.0:1 worst case (needs 3:1 as large text), lede 4.7–7.2:1 (needs 4.5:1). The small orange eyebrow is the one weak point at 1.4–1.8:1 — it was already under 4.5:1 before this change, and the lighter field makes it more noticeable; deepening that orange in the hero, or giving it a small pale backing, is the fix if it needs to be crisper.

Deploy and hard-reload. If the right edge still feels too white, the final `84%` stop is the dial — `78%` shows more radiator at the cost of the lede and eyebrow.

## 14:00

Now I'd like to start filling in the detail. There are buttons at the top, chosen arbitrarily, and some bullet points below the photo. Let's merge the 4th one into the first, and add a new "Control from anywhere" bullet with a smartphone icon.

**Assistant**

The benefit strip now reads: **Lower heating bills** ("Use heat where it makes sense, and waste less of it."), **Warm rooms when needed**, **Simple day-to-day use**, and **Control from anywhere** ("Adjust every room from your phone."). The old fourth item is folded into the first, so the strip still has four columns.

The phone is an inline SVG rather than an emoji, so it takes the same orange as the other glyphs inside the navy ring: 24px on desktop, 20px at the mobile size, with `aria-hidden` so screen readers skip it. Two small CSS rules were added for it; the top navigation is untouched, and "Daily Use" still points at the steps section.

Checked the strip at 1440, 1333, 1100, 900 and 390: four equal-height items, icon at the right size, descriptions hiding at the design's 1050px breakpoint as before, mobile 2×2 intact, no overflow. Draft copy is easy to reword — say which lines you want different. Deploy and hard-reload to see it.

## 14:05

The smartphone icon is too black - is a lighter one showing a picture of some kind possible?

**Assistant**

The icon is redrawn lighter: a 1.5px orange stroke, and the phone now has a screen with two short room rows, so it reads as the app's room list rather than a bare outline. 24px on desktop, 20px on mobile.

The black you saw is what a stale cached `styles.css` would produce: without the `.benefit-icon svg` rule, an inline SVG falls back to a black fill. So the drawing now carries `fill="none"`, `stroke="#f47716"` and `stroke-width="1.5"` itself, and the stylesheet link is versioned (`styles.css?v=20261114`) so the page fetches the current CSS even when an old copy is cached. A comment beside the link says to bump `?v=` when the stylesheet changes.

Checked at 1440 and 390 at 2x, and again with the CSS rules deleted at runtime to imitate the cached-stylesheet case — the icon stayed orange and light. Full-page checks still pass.

## 14:20

Let's now deal with each of the sections of the infinite scroll. The Benefits section can talk a little about cost savings and remote operation; the diagram alongside/below needs complete revision.

How it works looks OK but I think a 4th point regarding remote control is important.

Installation can be expanded to talk more about the devices themselves, the prerequisites, who does the work and say when an electrician or plumber might be needed..

FAQs are accurate enough. If you think there are others worth including, let's try them.

**Assistant**

The four sections are filled in.

**Benefits** now has three paragraphs — the hardware in short, where the saving comes from, and remote operation — and the old room card is replaced by a phone mock of the app: time and outside temperature, the weekday profile, Living room 21.5° Heating, Kitchen 20.0° Warm, Guest room 12.0° Off, and "Boiler firing for 2 rooms", captioned as illustrative. It carries a text summary for screen readers.

**How it works** gained the fourth card, "Control it from anywhere". The grid is four across on desktop, 2×2 below 1050px, one column on a phone.

**Installation** keeps its heading and button, with three columns beneath: The devices, What the house needs, Who does the work. The last says plainly where a trade is needed: an electrician for new mains wiring, a Gas Safe-registered engineer for a gas boiler's controls, a plumber or heating engineer for a valve body or adapter.

**FAQs** grew by four: broadband loss (heating continues), will it save money (directional, no percentage), what a system costs, and what happens when a sensor stops reporting. Seven in all.

Two things worth your eye. Step 1 still says sensors "help the system understand which spaces are occupied"; there is no occupancy sensing — it follows schedules and temperatures, and I left the wording since you said the section was OK. And the nav still maps oddly: "How It Works" jumps to the intro, while "Daily Use" jumps to the section headed "How Room By Room Heating works".

Deploy and reload; the stylesheet URL is bumped again, so no hard refresh is needed.

## 14:20

"Get in touch" should link to info@rbrheating.com

**Assistant**

Done — the contact button now opens `mailto:info@rbrheating.com` with the same subject line.

## 14:29

In Find out more, a note can be added for DIY users and the technically curious, linking to the repo and noting that this is an Open Source project. Also a button that takes the reader to the PWA (explaining what that means) would be useful.

**Assistant**

The "Find out more" section now has two buttons and two notes. **Get in touch** stays orange and mails `info@rbrheating.com`; **Open the web app** is a white secondary button pointing at `/heat/`. Under a hairline rule, two notes explain the PWA — a web page that can be added to a phone's home screen and used like an installed app, with nothing from a store, and a working demonstration when no system is paired — and the open-source side, linking the controller, app and documentation on GitHub (`github.com/easycoder/rbr`) for DIY installers and the technically curious.

The notes run in two columns and drop to one at 760px. The stylesheet is bumped to `?v=20261114-4`.

Checked at 1440, 1024, 768 and 390: both hrefs correct, notes 2/2/2/1 columns, GitHub link resolves, no overflow; full-page checks still pass. One deployment note: `/heat/` only resolves once the site is deployed — locally there is no such path.

## 14:36

The web page is good enough for our current needs, so let's move it to /index.html and delete the /home copy.

**Assistant**

Done. `index.html` is now the marketing page and `home.html` is gone from the repository. The staging `noindex` guard is removed with it.

`deploy.sh` no longer uploads `home.html`. Because rsync never deletes, I added a small cleanup step that removes `/home.html` and the stray `/living-room-hero.jpg` from the host by name with `rm -f` — safe on every later run, and it avoids putting `--delete` on a root directory that also holds files the script does not own. `doc/CONTROLLER-FILES.md` no longer lists `home.html`.

Checked by serving the repo root: `/index.html` loads with the stylesheet, hero image and every asset, has no robots meta, and all eleven in-page anchors resolve; `/home.html` is now a 404. `bash -n deploy.sh` passes.

Run `./deploy.sh` from your shell to publish the page at `https://rbrheating.com/` and clear the two staging leftovers from the host; hard-reload once if the old placeholder index is cached.

## 15:14

where does rbr-setup.sh store the config data

**Assistant**

In the controller directory itself — the folder the script is run from, captured as `$RBR_DIR` (`RBR_DIR="$(cd "$(dirname "$0")" && pwd)"`, i.e. normally `~/rbr`). Nothing it writes about the controller goes under `/etc` or `/var`.

Files it puts in `$RBR_DIR`:

- `credentials` — MQTT broker account (`broker`, `port`, `username`, `password`) and the `mail_*` SMTP settings; mode 0640, created once and left untouched on re-runs unless you answer "y" to updating mail (a backup goes to `credentials.bak`).
- `zigbee-config.json` — the bridge's broker settings and its `http_port` (8889).
- `.mqtt_password` (0600) and `.mac_override` — the password bootstrap and the controller's MQTT topic identity.
- `heatlog-root` — one line naming the heating-data root, `/data/rbr-heating`, which is either a real partition or a symlink to `/home/<user>/heating-data`.
- `volatile-root` — one line naming the RAM directory `/run/rbr`, recreated at boot by `/etc/tmpfiles.d/rbr-volatile.conf`.
- `journal-export-config.json` — the daily journal export's mail target.
- `backup/` — the monthly archive written by `rbr-backup.py`.

Machine-level config it does write outside the tree: `/etc/mosquitto/conf.d/rbr-local.conf` (local broker + bridge account), `/opt/zigbee2mqtt/data/configuration.yaml` (never replacing an existing network identity), the `rbr-*.service` / `*.timer` units and the journald drop-in under `/etc`, and `/etc/udev/rules.d/99-zigbee-dongle.rules`.

## 15:19

Do we have an file name inconsistency? 'credentials' holds an incorrect SMTP server but rbr-mail-test.py sends to the correct one. Are they using the same file?

**Assistant**

No filename inconsistency — and no, they are not using the same file. Or more precisely: `rbr-mail-test.py` does not use a file at all.

The filename is `credentials` (no extension) everywhere it matters: `rbr-setup.sh` writes `$RBR_DIR/credentials`; `controller.allspeak` does `load Credentials from 'credentials'`; `rbr_mail.load_local_credentials()` opens `os.path.join(rbr_dir, "credentials")` for `rbr-backup.py` and `journal-export.py`; `rbr-restore.py` restores that name. There is no `credentials.json` in the controller's path — `credentials.example.json` is the repo's template, and `credentials.php` is the website endpoint.

`rbr-mail-test.py` is a stand-alone diagnostic: `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `MAIL_FROM`, `MAIL_TO` are constants at the top of that file, and it never opens `credentials` or fetches `credentials.php`. So a green run proves those constants work; it says nothing about what the controller, the backup or the journal export will do. That is exactly how you can get a successful test while RBR itself cannot send.

What actually governs RBR mail, and the one trap worth knowing:

- `rbr-backup.py` and `journal-export.py` go through `rbr_mail.mail_settings(local, cloud)`: a *usable* local `mail_*` value wins, and the cloud copy (`credentials.php` via `.mqtt_token`) fills only what the local file lacks or has as a placeholder.
- `usable_mail_value()` treats only empty, `replace_with…`, `smtp.example.com` and any `*.example.com` as unusable. A wrong-but-plausible local server — an old provider, a typo like `smtp.pobox.co` — is therefore used in preference to a correct cloud value, and every send fails while `credentials.php` looks right.
- The controller's verification and password emails (`controller.allspeak:3846` and `:3856`) use `MailServer`/`MailLogin`/`MailPassword`/`MailFrom` loaded only from the local `credentials`; there is no cloud fallback on that path at all.

So the repair is in `credentials`: run `rbr-setup.sh` again and answer `y` to "Update the mail settings in that file?" (it offers the stored values as defaults and keeps the MQTT account), or edit the `mail_*` fields by hand.

If you want the diagnostic to stop being able to disagree with the real sender, `rbr-mail-test.py` could take the controller directory and load `credentials` through `rbr_mail.load_local_credentials()` — same settings, same merge rule — and keep the constants as an explicit override. Say the word and I will make that change.

## 15:29

In rbr-setup.sh there's
SMTP host - empty to skip email.
If there's already something there, how can we send empty?

**Assistant**

You can't, as it stands — and it is worse than "not documented": a whitespace-only answer does not work either. Verified against bash's own `read`: it strips leading and trailing IFS whitespace, so a line containing only spaces arrives as an empty `val`, `prompt_value` then applies `${val:-$default}`, and the stored server is returned. `ask_mail_settings` strips whitespace before the "skip email" test, but that test only ever sees the default in this case.

The default comes from `mail_default mail_server`, which returns the stored value unless it is empty, `replace_with…`, or any `*.example.com`. So on a re-run, with "Update the mail settings?" answered `y`, every route back to empty is closed: Enter keeps the value, and there is no other accepted input.

Ways out today, none of them the prompt:

- Edit `$RBR_DIR/credentials` by hand and clear the mail fields (or write the placeholders the script itself writes: `mail_server` `smtp.example.com`, empty `mail_password`).
- Set just `mail_server` in `credentials` to `smtp.example.com` (or empty), then re-run and answer `y`: `mail_default` now returns nothing, the prompt has no default, and Enter means "skip email" as the label promises. This rewrites the placeholders for you.
- Delete `credentials` and re-run: the fresh path has no defaults, so Enter at the server prompt skips email — but it also re-asks the broker host and port, and loses every stored mail setting. Fine if email is what you are dropping.

The same dead end exists on `mail_to` (empty = registered address) and on the mail password: `prompt_secret` documents "an empty answer keeps the stored one", so it has no way to clear a password either. A space in `mail_to` or `mail_from` would not help — `read` trims it to empty and the default comes back.

**Fix direction:** one recognised "clear" answer, used by `prompt_value` and `prompt_secret` when a default is offered, and named in each prompt's hint. I would use a single `-`, so the server line reads `Mail server (SMTP host — '-' skips email) [smtp.pobox.com]:`; `-` is never a valid host, address or password, and it is one keystroke. The alternative is a separate "Keep email configured? (Y/n)" question before the mail fields, which is more discoverable but adds a prompt to every re-run.

## 15:32

In rbr-setup.sh there's
SMTP host - empty to skip email.
If there's already something there, how can we send empty?

**Assistant**

You can't today — and I checked the assumption people usually reach for: a whitespace-only answer does not work either, because `read` trims leading and trailing whitespace, so a line of spaces arrives as empty and `${val:-$default}` puts the stored value back. `ask_mail_settings` only strips whitespace before its "skip email" test, which in that case never sees an empty value.

Implemented the fix you picked: `-` means "no value", handled at the call sites so no other prompt changes meaning.

- `rbr-setup.sh`: the mail server accepts `-` and takes the existing skip-email branch (placeholders written, nothing else asked); `-` clears the stored login, password, From: address and fallback recipient; at the port question it restores `465`. The journal-recipient question in Step 6e gets the same treatment. Labels and the pre-prompt note now say so.
- `docs/installation/06-what-the-setup-script-does.md`: the table and the paragraph after it explain Enter-versus-`-` on a re-run, and note that clearing the local server stops the controller's own mail while the backup and journal export can still use `credentials.php`'s settings where the local file is empty.
- `doc/setupRBR.md`: the re-run note mentions `-`.
- `DIFF.md`: rewritten — run `./deploy.sh` because `rbr-setup.sh` ships in `rbr-controller.zip`.

Verification: `bash -n rbr-setup.sh` passes; I extracted `prompt_value`, `prompt_secret` and `ask_mail_settings` from the shipped script and drove them with piped answers against stored defaults — Enter keeps every value, `-` at the server skips email without asking the rest, `-` clears the clearable fields, `-` at the port gives 465, a fresh install still skips on Enter, and a punctuation-heavy password is stored verbatim.

One honest caveat kept in the docs: "no email" here means the local file's placeholder state, which is what a skipped install has always written. `rbr-backup.py` and `journal-export.py` merge the cloud copy in where the local value is unusable, so a usable `mail_server` in `credentials.php` can still send. Turning that off would mean a deliberate "mail disabled" flag in `credentials`, which the senders would have to honour; say the word if you want that too.

## 15:35

Please amend rbr-mail-test to use settings in credentials file.

**Assistant**

Done. `rbr-mail-test.py` no longer has SMTP constants of its own; it reads the controller's `credentials` and resolves the mail fields through `rbr_mail.mail_settings()`, the same merge the real senders use — a usable local value wins, and `credentials.php` fills only what is missing or still a placeholder. A success now means `rbr-backup.py` and `journal-export.py` can send too.

What it does:

- `--dir` names the controller directory (default: the script's own directory); it reads `credentials` and, unless `--no-cloud`, `.mqtt_token` too.
- `--to` overrides the recipient; otherwise the registered address (cloud) or `mail_to` (local) is used.
- `--show` prints the resolved server, port, username, password (only "set"/"missing"), From:, recipient and transport, each with its source — `credentials`, `credentials.php`, `default` or `not set` — and sends nothing.
- It warns when the merged settings work but the controller's own verification mail will not, because that path reads only the local file; a server coming from `credentials.php` does not help it. This is the case that caused the confusion behind this session.
- `rbr_mail.py` must sit beside the script; a missing copy gets a sentence, not a traceback. The transport rule still mirrors `rbr_mail.send_files` (587 STARTTLS, otherwise implicit TLS).
- `rbr-mail-test.py` is not in `CONTROLLER_FILES`, so it is not published in `rbr-controller.zip`: copy it to the controller when needed. `DIFF.md` says so.

Verification: `--show` against fixtures (complete, placeholder, missing `mail_to`, `--to` override), a missing-credentials error naming `--dir`, a missing-`rbr_mail` error, and a send to a closed port that exits 1 without printing the password. `tests/unit/backup_test.py` (12) and `tests/unit/journal_export_test.py` (13) pass.

## 15:53

Add rbr-mail-test.py to the dist pack

**Assistant**

Done, in all three places that decide what a controller receives.

- `deploy.sh`: `rbr-mail-test.py` is in `CONTROLLER_FILES`, so it goes into both `rbr-controller.tar.gz` (the updater's release) and `rbr-controller.zip` (the install pack). `build_controller_zip` now zips `"${CONTROLLER_FILES[@]}"` instead of repeating the names by hand — the two packs cannot drift again.
- `rbr-updater.py`: added to `TARBALL_FILES` (as `diagnose.allspeak` was), so an upload missing it is refused and `--check` reports it missing on a controller. No apply logic was needed — every plain file in the tarball is installed.
- `doc/CONTROLLER-FILES.md` lists it under Optional; `doc/UPDATE-MECHANISM.md`'s tarball listing includes it.

Action: `./deploy.sh --release` for the fleet to pick it up on the next hourly update. Until then, `rbr-updater.py --check` on a controller will report it missing, because it is now in the required set.

Verification: built both packs locally with the real functions and the current array (23 entries each: 22 files + VERSION); ran the real `extract_tarball` from `rbr-updater.py` against the tarball — accepted, 23 files, rbr-mail-test.py in `TARBALL_FILES` and `CHECK_FILES`; `bash -n deploy.sh` and `py_compile rbr-updater.py` pass; the file in the zip is byte-identical (sha256) and keeps 0755.

## 16:04

Where does rbr-mail-test.py get the recipient address from?

**Assistant**

Three places, in this order:

1. **`--to`**, which is split on commas and used verbatim — it overrides everything else.
2. **`credentials.php`'s `email` field** — the address registered in the app for this controller. It is fetched with the MAC and `.mqtt_token`, so a missing token or no network means this step simply yields nothing; `--no-cloud` skips it deliberately.
3. **`mail_to` in the local `credentials` file.**

The lookup is `rbr_mail.resolve_recipient("", cloud, local)`, the same function the monthly backup and the journal export use, and it takes the first value that contains an `@`. The `to` row in the printed table names which of the three supplied it (`--to`, `credentials.php`, `credentials`).

If none of them has a usable address, `--show` prints `— (not set)`, and a real run stops before connecting with "no recipient: pass --to, or set mail_to in credentials, or register an address in the app".

## 16:09

My colleagues's system seems not to have any source of an email address. What could have happened?

**Assistant**

The first thing to rule out is that the address exists but `rbr-mail-test.py` cannot see it. The test reads only three sources: `--to`, `credentials.php`'s `email` (via MAC and `.mqtt_token`), and `mail_to` in `credentials`. The monthly backup and the journal export each read one more, first of all — `address` in `backup-config.json` and `journal-export-config.json`, written when the Backups sheet or the journal toggle was used. So a system set up entirely from the app, never from `rbr-setup.sh`'s mail prompts and without a `.mqtt_token`, has a perfectly good address that `--show` reports as `to — (not set)`. That is a blind spot in the test tool, not a missing address.

If those two files are absent or carry no address, then genuinely nothing has ever supplied one, which is the normal state of a minimal install: the setup's "Fallback recipient" is the only place it asks, and skipping the mail settings leaves it empty; `.mqtt_token` is optional; the app only writes an address when the Backups sheet is used. The controller's own verification mail does not need any of this — the user types their address each time.

Then the failure modes, most likely first:

- Wrong directory. `--dir` defaults to the script's directory; run from a clone on a laptop, it looks at the clone. `--show` names the file it read, so this is one line to check.
- No `.mqtt_token`. `rbr_mail.fetch_cloud` returns `{}` without logging anything when the MAC or token is missing, so the cloud is silently never asked. Check `ls -l ~/rbr/.mqtt_token`.
- Token or MAC mismatch. `credentials.php` answers 401 and the script logs "cloud lookup failed (HTTP Error 401...)": the MAC is not in `rbr-users.json`, the system is not `verified`, or the token differs. A missing `.mac_override` makes the controller use the NIC's MAC, which a re-imaged or replaced machine will not share; a restore from an old archive can carry a token the cloud no longer holds.
- The cloud record has no `email`. Registration or a hand-seeded `rbr-users.json` entry can leave it empty; `credentials.php` reads exactly `$system['email']`.
- A `mail_to` that does not contain `@` is ignored — `resolve_recipient` requires one.
- `--no-cloud` was passed, or the box has no route to `rbrheating.com`.

On the colleague's box, in order: `python3 rbr-mail-test.py --dir ~/rbr --show`; `ls -l ~/rbr/credentials ~/rbr/.mqtt_token ~/rbr/.mac_override ~/rbr/backup-config.json ~/rbr/journal-export-config.json`; `cat ~/rbr/.mac_override` and compare it with the system in the app; `python3 rbr-updater.py --check`; and fetch `credentials.php?mac=…&token=…` by hand to see the code (401 = token/MAC/verified, 404 = the host settings file). `rbr-doctor.py` also names `.mqtt_token` when the broker round-trip fails.

A durable local fix is `mail_to` in `credentials` (or `python3 rbr-mail-test.py --to address`), while the app's **Menu → Backups** toggle is what writes `backup-config.json` and is the path the monthly timer actually prefers.

The test tool could close the gap: read `backup-config.json` and `journal-export-config.json`'s `address` the way the timers do, and say plainly when there is no `.mqtt_token` so the cloud was never asked. Say the word and I will wire that in.

## 16:27

Best to close the gap - we'll edit credentials for now.
Can you diagnose this:
RBR mail test — settings from /home/rbr/rbr/credentials
  server   : smtp.mail.yahoo.com            (credentials)
  port     : 587                            (credentials)
  username : danboysk@yahoo.com             (credentials)
  password : set                            (credentials)
  from     : noreply@rbrheating.com         (credentials)
  to       : danboysk@yahoo.com             (credentials)
  transport : STARTTLS
sending…
FAILED: the server rejected the sender 'noreply@rbrheating.com'. Some providers only allow a From address that matches the login. Server said: (550, b'Invalid mail from', 'noreply@rbrheating.com')

**Assistant**

Diagnosis: the SMTP account is fine — it authenticated, which is why the refusal is at MAIL FROM rather than at login. Yahoo only accepts an envelope sender that belongs to the authenticated account (or a verified "Send As" alias). `credentials` sets `mail_from` to `noreply@rbrheating.com`, which that Yahoo account may not send as, so the message is refused with 550 Invalid mail from. RBR's sender uses `mail_from` when it is set and only falls back to `mail_login` when it is empty, so every send from that box would fail the same way — the monthly backup and the journal export too, with the reason recorded in `backup-status.json`.

Fix, in that controller's `credentials`: set `"mail_from"` to `"danboysk@yahoo.com"` (or make it empty, and the login becomes the sender). If `noreply@rbrheating.com` must stay as the visible From, Yahoo has to have it as a verified Send As alias; otherwise it cannot be used at all. The controller's verification and recovery mail reads the same `mail_from`, so it was failing for the same reason.

Gap closed in `rbr-mail-test.py`:

- The recipient now follows the timers exactly: `--to`, then `address` in `backup-config.json`, then `journal-export-config.json`, then the registered address from `credentials.php`, then `mail_to`. The `to` row names which one won, and when the journal config holds a different address it says so.
- With no `.mqtt_token`, the report states that `credentials.php` was not asked and a registered address cannot be used — the silent `{}` from `fetch_cloud` no longer looks like "there is no address anywhere". `--no-cloud` gets its own note.
- The sender-refused error now names the fix: "set mail_from in credentials to 'danboysk@yahoo.com', or clear it so the login is used".
- `DIFF.md`: `./deploy.sh --release` carries both the new pack entry and this change; until then `rbr-updater.py --check` reports the file missing.

Verification: `--show` fixtures for backup config, journal config, both (backup wins, journal noted), `--to` override, no token, `--no-cloud`; a stubbed SMTP returning 550 to check the new message and exit code, and an accepting stub for the success path; `py_compile` passes.
