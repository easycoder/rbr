# Preparing the controller computer

> **Audience:** installer, commissioning technician, and anyone preparing a unit · **Status:** draft · **Last verified:** 2026-09-21 · **See also:** [Bill of materials](02-bill-of-materials.md) · [Naming and network conventions](03-naming-and-network.md) · [Installing the controller](../installation/01-installing-the-controller.md) · [Glossary](../appendix/glossary.md)

## The machine

A small mini-PC is the easy answer, and these days the cheap one: once a single-board computer has been given a case, a power supply and storage, the mini-PC usually costs less and arrives with the two things this document goes on to depend on — an SSD rather than a card, and ordinary firmware with the power-loss setting described at the end.

Any Linux will then serve. Where the machine has a screen of its own, a desktop distribution is the sensible choice; where it does not, a server distribution is enough, and the system is run over an SSH connection. Either way, work from the default user account, because the setup expects it.

Two things about the machine are worth settling before anything is installed on it:

- **Storage that is not a microSD card.** This is the reliability point from the [bill of materials](02-bill-of-materials.md), and it is much easier to get right now than to migrate later.
- **Where the lasting data goes.** The controller keeps each room's heating records under a data root, by preference on a partition of its own. Where no such partition exists the installation puts a folder in the controller user's home in its place, so that the configured path is the same on every machine. Adding a real partition afterwards means moving the folder, not changing the system.

## Getting the software onto it

There are two routes, and they differ only in where the files come from.

**A customer system** uses the bootstrap pack. One command fetches a script, and the script fetches and unpacks the controller files:

```
wget https://rbrheating.com/get-controller.sh
sh get-controller.sh
```

**A development machine** copies or clones the repository instead. Everything else is identical.

Then the runtime, which is a package from the Python index:

```
pip install allspeak-ai        # add --break-system-packages if pip refuses
```

That step is deliberately left to the operator rather than performed by the setup script, because modern distributions usually require the extra flag and it is the operator's call whether to use it. The script will tell you if the runtime is missing.

Everything else — the message broker, a recent Node.js, the Zigbee software and its build — is installed by the setup script in the next stage, so the machine needs working internet access while that runs.

## The radio: plug it in first

**Connect the coordinator before running the setup script, not after.** The script detects it as it starts and derives two things from what it finds: the stable device name the controller will use for it, and the port the Zigbee software is configured with. Attaching the coordinator afterwards leaves both as placeholders, and the Zigbee software will not start until they are corrected by hand.

The stable device name is worth understanding, because it is where an unusual coordinator costs you something. The setup writes a rule that gives the coordinator it expects a fixed name regardless of which socket it is plugged into — and the coordinator it expects is a Silicon Labs CP210x device, at USB `10c4:ea60`. Any other coordinator still works, but is pinned to whichever serial device it happens to be given, and that can change between reboots, which presents as the heating mysteriously failing to start after a restart. Giving another coordinator its own rule is a small piece of work, but it is work.

And keep it clear of metalwork, on a USB extension lead. The reason is in the [bill of materials](02-bill-of-materials.md), and it is the single most common cause of intermittent trouble on an installation.

## Storage: what must survive, and what need not

The controller writes constantly, and most of what it writes is not worth keeping. Sorting the two apart is what makes the machine reliable without making it fragile.

**What has to survive a power cut is small and changes rarely:** the plan, its history, and the rooms' heating records. These belong on persistent storage, and they are the reason for choosing an SSD over a card.

**What does not:** the readings as they arrive, the running summary the terminal dashboard draws from, and the logs. This data is regenerated within minutes or is of no lasting value, and it is the natural candidate for volatile storage.

The compromise to aim for is the one that minimises writing without risking anything that matters: keep the volatile data in volatile storage while the system runs, and refresh it to persistent storage periodically — hourly is a workable assumption — so that a power cut loses at most the window since the last refresh. For the readings and the logs that window is unimportant. In practice it removes the great majority of the writes the machine would otherwise make, which is what the card or the disk would have been wearing out on.

The plan is the exception, and should be written the way it is now: deliberately, to persistent storage, with its history kept beside it. It is the one artefact that represents somebody's work, and it does not change often enough to be worth buffering.

## Coming back after a power cut

A controller that does not return by itself is not a controller. The operating-system half is already handled, because every service the setup installs is enabled and the whole stack comes back without anyone logging in.

The half that the operating system cannot touch is the machine's own firmware. Set the BIOS or UEFI option for restoring after power loss — it may be called "Restore AC Power Loss", "AC Back" or "After Power Failure" — to **Power On**, and turn off **ErP/EuP Ready**, which can prevent the machine waking at all. Nothing in Linux can read or set those, so the only way to know is to test it: cut the mains, restore it, and watch the machine come up unaided.

**The firmware option is not always the one that decides.** Some mini-PCs settle it on the board instead, with an AT/ATX jumper: one pair of its pins leaves the machine waiting for the power button, the other starts it as soon as power arrives — and where that jumper exists, the firmware setting can be present, set correctly, and overridden. The board is normally silkscreened when it has one; a J1900 board of this kind marks a three-pin header "AUTO ON" beside its clear-CMOS jumper, and it is the pair the cap sits on that decides. So look at the board as well as the setup screen, and move the jumper before concluding that a machine cannot come back by itself.

This requirement is also what makes some otherwise tempting machines unsuitable. A panel or appliance board that boots a vendor's own operating system, with no ordinary firmware beneath it and no such setting to change, cannot be relied on to come back after an outage — and it usually limits which Linux you can run and how current it is. A built-in screen is not worth that.

## Where next

- [Installing the controller](../installation/01-installing-the-controller.md) — running the setup on the prepared machine.
- [Bill of materials](02-bill-of-materials.md) — the storage and coordinator choices this stage assumes.
- [Glossary](../appendix/glossary.md) — the terms used across these documents.
