# Provisioning a system

How a controller gets an account: what lives in `rbr-users.json`, which parts the web endpoints create, which part nothing creates, and the one command that leaves an entry complete.

## What an account consists of

Each entry in `rbr-users.json` is keyed by the system's MAC address — the one the controller generates at install and stores in `.mac_override`, written `xx:xx:xx:xx:xx:xx` with colons, lower case. The fields are:

| Field | Written by | Meaning |
| --- | --- | --- |
| `email` | `/register`, or the tool | The owner's address. Also the second half of the `/recover` key. |
| `password` | `/register`, `/recover`, or the tool | A **six-digit** code, generated on the server with `rand(0, 999999)` zero-padded. Shown once and stored nowhere on the controller. Not to be confused with the MQTT password in `~/rbr/credentials`: that is a different, longer secret and will be rejected everywhere this one is accepted. |
| `verified` | `/verify`, or the tool | False until the password has been used once. A pending entry can be silently overwritten by registering the same MAC again. |
| `token` | `/verify`, or the tool | 24 random bytes, 48 hex characters. The bearer credential the browser sends to `credentials.php`. Rotating it unpairs devices holding the old one. |
| `created` | `/register`, or the tool | Unix time. |
| `credentials` | **nothing but this tool, or by hand** | The broker account: `broker`, `port`, `username`, `password`. `credentials.php` returns **401** without it. |

The file sits at `/home/rbrheating/rbr-users.json` — one level **above** the document root, so Apache can never serve it. Mode 600. PHP runs as the account owner, so the server can read and write it.

## The two endpoints, and the gap between them

`auth.php` handles three routes (mapped by `.htaccess`):

- **`/register`** with `{mac, email}` validates both, refuses if the MAC already exists *and is verified*, and otherwise creates the record with a freshly generated six-digit password, returning it in the response. That is the only time the password exists.
- **`/verify`** with `{mac, password}` sets `verified` and mints `token` on first success.
- **`/recover`** with `{mac, email}` issues a new six-digit password when the pair matches a verified entry; otherwise it answers success anyway, so it cannot be used to discover which systems exist.

**The gap:** neither endpoint creates `credentials`. A system registered and verified through the UI alone therefore pairs successfully, then asks `credentials.php` for broker details, is refused with 401, and falls into demo mode — with nothing in the browser or on the controller to say why. That failure is silent, and it looks exactly like a wrong password.

## provision-system.py

An admin tool that runs **on the web host**, as the account owning `rbr-users.json`, and is deliberately kept outside the document root beside it. It needs no packages.

```
./provision-system.py --list
./provision-system.py --mac 00:e0:27:5b:31:40 --email owner@example.com            # dry run
./provision-system.py --mac 00:e0:27:5b:31:40 --email owner@example.com --write
```

Without `--write` it is a dry run: it reports every change it would make and touches nothing. It brings an entry to a complete state rather than blindly overwriting, so running it repeatedly is safe — a complete entry reports `already complete`.

- **Broker defaults** come from the per-system block first, then the host settings file (`rbrheating.com.txt`), which is what `credentials.php` falls back to. The two cannot drift apart.
- **Secrets are never printed** — with one exception. A newly generated system password is printed once, because it exists nowhere else and has to be written down at that moment.
- **The broker login is tested before writing.** It performs a minimal MQTT 3.1.1 CONNECT over TLS on the MQTT port (`--mqtt-port`, default 8883) — not the websocket port served to the UI, which speaks a different protocol — and refuses to write if the broker rejects the credentials, since that is precisely the state that produces a system that pairs and then sits in demo mode.
- **Writes are atomic and ownership-preserving.** This file gates every customer's pairing; a half-written one locks everybody out and the symptom would look like wrong passwords. A timestamped backup is kept, and the result is re-read before success is reported.
- **Changing a verified system's email or password needs `--force`.**

## What the tool cannot do

It writes the account the UI uses; it does not create or fence accounts on the broker. That lives on the broker host (`rbrheating.duckdns.org`), which is a separate machine from the web host. Today every system shares the single account `rbr`, and separation between systems rests on each UI only knowing its own MAC rather than on an ACL. Genuine isolation between customers would be broker work, not a change to this file.

## Checklist for a new system

1. Install the controller and note its MAC (`cat ~/rbr/.mac_override`).
2. On the web host: `./provision-system.py --mac <mac> --email <owner> --write`.
3. Write down the six-digit password it prints and give it to the owner with the MAC.
4. In the browser UI, pair with that MAC and password. `credentials.php` now answers, so the app connects rather than falling into demo mode.
