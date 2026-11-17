# RBR handover channel #

This document describes the mechanism that lets a heating installer, or a technical advisor acting for them, move Room By Room to a new website if the maintainer becomes unavailable. It is the technical counterpart to [CONTINUITY.md](../CONTINUITY.md), which covers the accounts, the legal position and the human process; this page covers what the software does and what has to be prepared for it to work.

> **Audience:** maintainer, hosting operator, successor · **Status:** implemented 2026-11-16 · **Last verified:** 2026-11-16

## Why it exists ##

Customers buy a heating system that depends on a website for updates and on a broker for remote control. A promise that the project will keep running must not depend on one person remembering to hand it over. The handover channel gives an installer a prepared route that works without the maintainer, while leaving the maintainer a notification and a fortnight in which to cancel a false request.

The mechanism deliberately does not transfer anything by itself. It points controllers at a new site; the domain, hosting, broker accounts, repository and customer register are still transferred by the processes in `CONTINUITY.md`. Preparing the new site is a separate project.

## The customer-facing page ##

`/handover/` on the site is a no-index page with two fields: the passphrase from the sealed envelope and the address of a new, already-prepared website. It posts to `/handover.php?action=request`.

The page explains three things a person needs before using it: nothing changes immediately; the maintainer is notified and can cancel; and the new site is checked when the request is made and again when the waiting period ends. It also has a cancellation mode, opened by the link in the notification email.

The address is the new site's root, for example `https://heating.example.com`. The controller appends `/heat/rbr-controller.tar.gz` and `/credentials.php` to it, so a path is allowed only when the new site really lives under one.

## Configuration ##

The host settings file above the site root — the same `../<host>.txt` that `credentials.php` reads — gains a `handover` field. It may be the passphrase alone (the short form) or an object:

```json
"handover": {
    "passphrase": "the secret in the sealed envelope",
    "owner_mac": "00:e0:27:5b:31:40",
    "notify": "owner@example.com",
    "days": 14
}
```

| Field | Meaning |
|---|---|
| `passphrase` | Required. Empty or absent means the channel is disabled and `/handover.php` returns 404. It is compared with `hash_equals`, never stored in the request record and never echoed. |
| `owner_mac` | The maintainer's own system MAC. Only this system is sent the PWA alert, and only this system can cancel from the app. It may also sit at the top level of the host settings. Without it the email cancellation link still works. |
| `notify` | Where notifications go. Falls back to `mail_from` in the same file. |
| `days` | Waiting period in days, 14 by default, bounded to 1–365. |
| `allow_http` | Testing only. Accepts an `http://` new site; production must be `https`. |
| `allow_private` | Testing only. Allows a loopback/private address as the new site. Never enable in production. |

Generate a passphrase with `python3 -c 'import secrets; print(secrets.token_urlsafe(24))'`. Put it in the host settings and in each sealed envelope, then keep the host settings file outside the document root and readable only by the hosting account. If `notify` is left out, the address registered for `owner_mac` in `rbr-users.json` is used, and `mail_from` is the last fallback; set `notify` explicitly if the notification should go somewhere else. The file already contains the MQTT account and SMTP password; the handover passphrase belongs with them.

The example file [credentials.example.json](../credentials.example.json) documents the shape. Do not enable a real passphrase in the repository or in any file that is served.

## Request state ##

Requests are kept in `rbr-handover.json` one level above the web root, beside `rbr-users.json`, mode 0600. It holds the request history and a small per-address rate-limit list; it does not hold the passphrase. A request record looks like this:

```json
{
    "id": "…32 hex characters…",
    "state": "pending",
    "url": "https://heating.example.com",
    "requested_at": 1763300000,
    "effective_at": 1764510000,
    "requester": {
        "ip": "203.0.113.10",
        "forwarded_for": "",
        "user_agent": "Mozilla/5.0 …",
        "accepted_at": 1763300000
    },
    "notified": true,
    "verified_at": null,
    "failed_at": null,
    "cancelled_at": null,
    "cancelled_by": "",
    "error": ""
}
```

Only one request can be `pending` or `active` at a time. A cancelled or failed request leaves the history in place and allows a fresh one.

### The states ###

| State | What it means | What controllers do |
|---|---|---|
| `pending` | Recorded, inside the waiting period. The owner has been emailed. | Nothing. The status response reports the countdown. |
| `active` | The waiting period ended and the new site passed the readiness check. | Switch to the new site on the next update check. |
| `cancelled` | The owner or an email link stopped it before it became active. | Nothing. |
| `failed` | The waiting period ended but the new site did not pass the readiness check. | Nothing. Fix the new site and submit a fresh request. |

Activation is lazy. The server does not run a timer; the transition from `pending` to `active` happens on the first status request after `effective_at`, which is a controller's hourly update check. That is also the moment the new site has to be reachable, so the check is made there and then. If it fails, the request is marked `failed`, the owner is emailed, and nothing switches.

### Endpoints ###

| Request | Who may call it | Purpose |
|---|---|---|
| `POST /handover.php?action=request` | anyone with the passphrase | Record a request and email the owner. |
| `GET /handover.php?action=status&mac=…&token=…` | a verified system | Report the live request. Without a token, a verified MAC learns only that an active handover exists and its URL; pending details are not disclosed. |
| `POST /handover.php?action=cancel` | the owner's MAC and token, or `id` and the HMAC signature from the email | Cancel a pending request. Refused once the waiting period has ended. |

The full status response looks like `{"ok":true,"handover":{"state":"pending","url":"…","requested_at":…,"effective_at":…,"days_left":14}}`. A site with no live request returns `{"ok":true,"handover":null}`.

## The readiness check ##

A new site is accepted only when all of these are true:

- The address is `https` (or `http` when `allow_http` is set for testing), has a host and no username, password, query or fragment, and resolves only to public addresses. Resolving to a private or reserved address fails the check unless `allow_private` is set.
- `GET <site>/heat/version` returns HTTP 200 and a body of 8–14 digits, the release stamp the updater itself reads.
- `GET <site>/credentials.php` returns HTTP 401. That proves the endpoint exists and is refusing an unauthenticated caller; a 200 would be a misconfiguration, and a 404 or an HTML error page means the site is not an RBR site.
- Redirects are not followed. TLS certificates are verified.

At the moment of activation the controller repeats the `/heat/version` check before it switches. The PHP side repeats both checks at activation, so a site that worked at submission but has been taken down before the deadline causes the request to fail rather than leaving the fleet pointing at nothing.

The new site also needs a copy of the customer register (`rbr-users.json`) and the host settings, or an equivalent, so that each controller can fetch its own broker credentials after the switch. That is part of preparing the new site, not part of this page.

## What the controller does ##

`rbr-updater.py` runs hourly. On each run it:

1. Reads `.site_url` if present, otherwise uses `https://rbrheating.com`.
2. Asks `<site>/handover.php?action=status` with this system's MAC and, when it has one, its token.
3. `pending` or `failed`: logs the state and changes nothing.
4. `active`: verifies `<new-site>/heat/version`, fetches `<new-site>/credentials.php` with the same MAC and token, writes the new address to `.site_url`, and rewrites mosquitto's bridge `address`, `remote_username` and `remote_password` from the response. It records the switch in `.handover`.
5. Continues the run against the new site: the tarball and every later check come from there.

`.site_url` is written before the bridge is touched, so a bridge update that fails is retried by the next run, which already reads the new site. A new site that is unreachable at that moment does not write `.site_url` at all; the box stays on the old address and tries again an hour later.

The channel only reaches a controller that already runs an updater carrying this code. The release that introduces it travels to controllers through the old update path, so it has to be shipped and applied before the channel is relied on. A request made while controllers are still on an older updater will wait, and those controllers will switch on the first run after they take the release.

The bridge's `address` is `<broker>:<mqtt_port>`, where `mqtt_port` comes from the credentials response (default 8883). That is the MQTT bridge port, not the browser's websocket port (`port`). A broker host change is therefore handled by the same reconciliation that repairs a stale password; it is not a separate code path.

Both `.site_url` and `.handover` are machine-specific runtime state. They are in backups and restores, so a rebuilt controller does not revert to the old site after a handover.

## Cancellation ##

There are two routes, both available only while the request is `pending`:

- **From the app.** `credentials.php` includes a `handover` object only for `owner_mac`. The PWA paints a flashing banner at the top with the days left and a Cancel button. The button posts the owner's MAC and token to `action=cancel`.
- **From the notification email.** The email contains a link to `/handover/?cancel=<id>.<signature>`. The signature is an HMAC over the request id keyed by the passphrase, so the link works without a second secret and cannot be guessed. The page asks for confirmation before calling `action=cancel`.

The app route needs a token on the device; the email route does not. If neither is available, the owner can edit `rbr-handover.json` on the host directly and mark the request `cancelled`, but that should be a last resort and the services on the box should not be relying on it. The app learns about a request when it next fetches credentials, which is each time it is opened; a page that is already open picks it up on its next load or reload.

## Email ##

Notifications go to `notify` (or the owner's registered address, or `mail_from`) through PHP's `mail()`. Shared hosting normally provides it; if the host disables `mail()`, the request is still recorded, the PWA alert still appears, and the page reports that the request was received. The `notified` field in the request record says whether the mail call returned true.

The notification includes the requester's IP, forwarded-for header and user agent, the new site address, the effective date, and the cancellation link. It does not include the passphrase.

## Security notes ##

- The passphrase is the only guard on the public form. Wrong attempts are counted per address for an hour (ten allowed) and each one is delayed half a second. A correct passphrase that leads to an invalid URL does not consume the limit.
- The state file is outside the web root, mode 0600, written under an exclusive lock. Concurrent requests cannot interleave a read and a write.
- The host must allow outbound HTTPS (cURL, or `allow_url_fopen`) for the readiness check; without it no request can be accepted, and the page says the new site is not ready.

The readiness check is an outbound HTTP request driven by form input. It refuses non-public addresses by default, follows no redirects, bounds the body and verifies TLS. The passphrase is the real gate; the address rules keep a leaked passphrase from turning the host into a probe of its own network.
- `owner_mac` is an ordinary MAC, not a secret; what makes the app cancellation authoritative is the token check against `rbr-users.json`. A local edit to the page cannot cancel anything.
- After a handover, rotate the broker accounts and the per-system tokens in the usual way. The old credentials should be assumed exposed by the change of hands, whether or not there is evidence of it.

## What has to be prepared, and by whom ##

Before this mechanism can rescue anything, someone has to do the human work:

- Generate the passphrase, put it in the host settings, and seal a copy for each installer or successor. Do not put it in this repository.
- Prepare the new site: a working deploy of the same code, a copy of the customer register and host settings, valid TLS, `/heat/` populated, a broker (the same one or a new one), and a tested `credentials.php`.
- Decide when the waiting period is appropriate. The 14-day default is short enough to reassure an installer and long enough for the owner to notice an email; the continuity plan's 30-day trigger is a separate, slower process.
- Test the page against a staging new site, including a cancellation, before it is needed. A sealed envelope nobody has opened is not a tested channel.
- Keep the old site reachable. It is the only thing that can tell controllers to move; a domain that lapses takes the channel with it.

## What this does not do ##

It does not transfer the domain, hosting account, broker, DuckDNS name, mail account or repository. It does not appoint a successor or change a legal position. It does not migrate customer data between sites. It does not keep the old site alive. Those are in [CONTINUITY.md](../CONTINUITY.md) and in the separate preparation project.

## Review ##

Review this mechanism whenever the site layout changes, whenever `credentials.php` or the update tarball changes, and after any test of the channel. A handover that has never been exercised is a design, not a capability.
