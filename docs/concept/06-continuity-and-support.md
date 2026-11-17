# Continuity and support

> **Audience:** industry — installers, heating contractors, specifiers, housing providers · **Status:** draft · **Last verified:** 2026-11-16 · **See also:** [Deployment and roles](04-deployment-and-roles.md) · [Costs and payback](05-costs-and-payback.md) · [Glossary](../appendix/glossary.md)

## A fair question

An installer is being asked to fit a system whose software, website and shared messaging service are maintained by one small project. The reasonable question is not whether the system works today; it is what happens to the houses already fitted if the person or company behind it stops.

This page answers that as plainly as the project can, including the part where the answer is not yet complete. It is written for the firm that has to stand behind the installation, not only for the household.

## The short answer

The software contains a **handover mechanism**: a way for someone holding a sealed passphrase to point every controller at a replacement website, and at a replacement messaging service if necessary, without the original maintainer's involvement. It waits fourteen days before anything changes, notifies the maintainer immediately, and can be cancelled in that window. It is built and tested.

> **Not yet a support contract.** The arrangement that would use the mechanism may not currently be available. As of 16 November 2026 there is no named successor, no prepared replacement site and messaging service, and no sealed passphrase in an installer's hands. An installer should ask for the arrangement in writing before treating this page as a guarantee of continued support.

The distinction matters. The mechanism is the technical half: it removes the need for the maintainer to be present on the day. The other half — a named successor or company willing to take over, a replacement service prepared and paid for, and the passphrase held where it can be found — is a separate piece of work. The project is actively looking for a co-maintainer who can hold that role; the public repository describes what it involves.

## What the handover mechanism does

The mechanism is deliberately slow, because a false trigger is worse than a delayed one.

A person holding the passphrase visits a page on the RBR website and enters two things: the passphrase and the address of a replacement website that has already been prepared. The request is recorded with who made it and when, and the maintainer is notified by email and, in the app, by a prominent alert. Nothing else happens for fourteen days.

During those fourteen days the maintainer can cancel the request. If it is cancelled, nothing changes. If it is not cancelled, the system waits for the fourteen days to pass and then checks that the replacement website is actually ready to serve RBR. If it is, every controller is told on its next update check to use the new address; if the replacement names a different shared messaging service, the controller is told that too. If the replacement is not ready, the handover fails and nothing switches.

Two safeguards follow from that design. The switch is lazy: a replacement that is briefly unavailable at the moment of the check causes a failure, not a fleet pointed at nothing. And the heating itself never depends on the website being reachable: the plan runs on the controller in the house, so the radiators keep following their schedules even when the app cannot reach them. The handover affects where updates and remote access come from, not whether the house stays warm.

## What has to be ready

The mechanism cannot rescue a project on its own. Before it can be used, these have to exist:

- **A named successor or company** willing and able to run the service, recorded somewhere the people involved can find it.
- **A replacement website**, prepared in advance with the same software, the registered systems and the settings that let each controller fetch its own access details.
- **A replacement shared messaging service**, or a decision to keep the existing one, with the accounts and access rules that go with it.
- **The domain and hosting**, kept alive long enough for the change to be made, and transferred through their own processes.
- **The sealed passphrase**, held by the installer or successor and known to more than one person.
- **A dry run**, against a staging replacement, so the channel has been exercised before it is needed. A sealed envelope in a drawer is not a tested capability.

Until those are in place, the mechanism is dormant. It does no harm, and it is ready to be used when the rest of the arrangement catches up.

## What it does not cover

The handover mechanism moves controllers. It does not transfer the domain, the hosting account, the messaging accounts, the repository or any legal responsibility. It does not appoint a successor, change a contract or move customer data between sites. Those are separate processes, described in the project's continuity plan in the source repository (`CONTINUITY.md`), with the technical detail in `doc/HANDOVER.md`.

Nor is it a warranty. An installer's own support obligation to a household is a contract between them and the installer, not something the project can take over.

## What an installer should ask for

When continuity matters to a quotation, these are the questions worth putting in writing:

- Who is the named successor, and where is that recorded?
- Who holds the sealed passphrase, and can more than one person reach it?
- Has a handover been tested against a prepared replacement site?
- Where will the replacement website and messaging service run, and who pays for them?
- What happens to the registered systems and their data in a transfer?
- Is there a support agreement with response times, or only a best-effort arrangement?
- Can the installer obtain the source, the continuity plan and a working deployment recipe?

A reassuring answer is specific. An answer that says only that the software is open source is not the same as an arrangement.

## What is true today

| Claim | State |
|---|---|
| The controller keeps heating when the website or app is unreachable | **Yes** — the plan and the decisions run locally in the house |
| The handover mechanism exists in the software | **Yes** — implemented and tested on 16 November 2026 |
| The project is looking for a successor or co-maintainer | **Yes** — the public repository describes the role |
| A named successor is in place | **Not yet** |
| A replacement site and messaging service are prepared | **Not yet** |
| Sealed passphrases have been distributed | **Not yet** |
| A live handover has been exercised | **Not yet** |
| A written support contract stands behind the product | **Not part of this project** |

That table is the honest position, and it is the one an installer should quote from. The project intends the mechanism to be real reassurance rather than a diagram; the intention is not the same as the arrangement being in place.

## Where next

- [Deployment and roles](04-deployment-and-roles.md) — who prepares, fits, operates and stands behind a system.
- [Costs and payback](05-costs-and-payback.md) — what the system costs, and why the saving cannot yet be sized.
- [Glossary](../appendix/glossary.md) — the terms used across these documents.
