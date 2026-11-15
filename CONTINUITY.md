# Continuity plan

> **Status:** draft · **Last reviewed:** 2026-11-15 · **Maintainer:** Graham, `info@rbrheating.com`, GitHub `@easycoder` · **Applies to:** `github.com/easycoder/rbr`, `rbrheating.com`, `rbrheating.duckdns.org` and the systems they serve

This is the succession plan for Room By Room. It exists so that a heating engineer, an installer, a developer or a member of the maintainer's family can see what to do if the maintainer becomes unavailable, rather than leaving a working system behind a set of accounts nobody else can reach.

It is an operational plan, not legal advice, and it does not by itself transfer ownership of anything. GitHub, the domain registrar, the hosting provider, the broker and local law each have their own process; this document says what to ask for and in what order.

## The maintainer and the successor

The maintainer is Graham, reachable at `info@rbrheating.com` and on GitHub as `@easycoder`.

The **successor** is the person or company named in the signed addendum to this plan. The role is expected to be an installer or company that already has an operational relationship with the system, or a developer trusted by the maintainer; it needs both the willingness to maintain the project and the ability to hold the accounts listed below. The named individual, their relationship to the project and their contact details are kept in the addendum rather than in this public file, so that a contact does not have to be published to make the plan real.

Until that addendum is completed, this document records the role and the process, not a named person. Completing the addendum is an open item, not a reason to leave the rest of the plan unwritten. The project is actively looking for a co-maintainer who can take that role; the README's **Looking for a co-maintainer** section describes what is involved and how to get in touch.

## When the plan is invoked

The trigger is **30 days without a response from the maintainer, after two contact attempts on separate channels**, with no public repository activity in that period.

The attempts and the waiting period are deliberately defined:

1. **First attempt.** Send a message to `info@rbrheating.com` and, if appropriate, a GitHub mention or direct message to `@easycoder`. Record the date, channel and message.
2. **Second attempt.** At least seven days later, use a different channel from the first — GitHub if the first was email, the private contact route in the addendum if one exists, or a letter to the maintainer's address of record. Record the date and channel.
3. **The trigger.** If there has been no response 30 days after the second attempt, and no public repository activity in the same period, the successor may treat the maintainer as unavailable and begin the steps below. Keep the written record of both attempts; it is the evidence a registrar, host or GitHub may ask for.
4. **Earlier confirmation.** A death certificate, a medical confirmation of permanent incapacity, or a statement from the maintainer's legal representative satisfies the trigger immediately. In that case the 30-day waiting period is not required.

A short illness, a holiday or a busy month is not the trigger. The waiting period is there to protect a temporarily absent maintainer from being locked out of their own project. If the successor is uncertain, they should wait, make a third attempt, and record why they acted.

Before acting, the successor should also, where possible, confirm the position with the maintainer's family or legal representative. If there is no named successor and no legal representative, this plan cannot by itself appoint one; the repository remains public under the MIT licence and may be forked, but the domain, hosting and broker accounts cannot be transferred without their own processes.

## Who may invoke it and under what authority

- **The successor named in the addendum** may invoke the plan and begin the transfer steps, with the evidence of the two attempts.
- **The maintainer's legal representative** may invoke the plan, appoint a successor if none is named, or act directly.
- **The successor should act with the legal representative where one exists.** No single person should be able to redirect the domain or the broker merely by asserting that the maintainer is unavailable.
- **If the successor is also the person who wants to take over permanently**, the transfer should still be recorded in writing — what was transferred, when, by whom, and on what evidence.

## What the successor does

The successor takes over the maintenance and operation of the project, not the maintainer's personal affairs. The order matters because some accounts are the keys to others.

1. **Confirm and record the trigger.** Complete the two attempts, the waiting period and any legal confirmation. Keep copies of the evidence with this plan.
2. **Secure the GitHub repository.** Follow the GitHub steps below. Do not share the maintainer's password; transfer ownership through GitHub Support or, if the repository is in an organization, through the organization's owner controls.
3. **Secure the domain and hosting.** The domain is the key to the controller update channel and the documentation. Transfer or take over the registrar, DNS and hosting accounts; change the recovery email and password; enable two-factor authentication.
4. **Secure the broker and the accounts.** Take over the DuckDNS name and the broker host, the MQTT accounts and the access rules. Rotate the broker passwords and the per-system tokens before publishing anything; the old credentials must be assumed exposed.
5. **Keep the system running.** The controllers update from the site and talk to the broker; the site serves the app and the documentation. Confirm that a test controller can fetch an update and exchange a message before making wider changes.
6. **Tell the users.** Publish a short notice in the repository, on the site and by email to the registered addresses. Say who is maintaining the project now, what has changed, and how to get support. A token rotation will require every phone to pair again; say so plainly.
7. **Preserve the data and the licence.** Keep the MIT licence and the project's open-source terms; do not publish customer data, controller archives, journals or `rbr-users.json`; follow the privacy expectations of the installations.
8. **Update this plan.** Record the transfer, the new maintainer, the new successor or the decision to wind the project down. A plan that still names the previous maintainer is a trap for the next person.

The successor may maintain, release and publish the project as the maintainer could. Changing the licence, selling the project or closing it down are decisions for the project's legal owner and should be taken with legal advice, not as an emergency step.

## Access inventory

The plan is only as good as the list of things that have to move. This table is the inventory; it deliberately contains no passwords, keys or personal contact details.

| Asset | Where it lives | How it transfers |
|---|---|---|
| Source repository | `github.com/easycoder/rbr`, owned by the `easycoder` GitHub account | GitHub ownership transfer; see the policy section below. If the repository is moved into an organization, add the successor as an organization owner. |
| Website and app | `rbrheating.com`, served from the hosting account at `/home/rbrheating/rbrheating.com` | Registrar and hosting support; transfer the account or create a new one and restore the files. The domain is the critical asset. |
| Documentation | `docs/` in the repository; the reader at `/docs/` | Travels with the repository and the hosting account. No separate service. |
| Controller update channel | `/heat/` on the site: `rbr-controller.tar.gz`, `rbr-controller.zip`, `version` | Travels with the site. A controller's updater downloads the tarball and applies a newer `version` stamp. |
| Account register | `/home/rbrheating/rbr-users.json`, one entry per system MAC | Hosting account. Contains passwords and tokens: handle as a secret, do not publish it, and rotate after transfer. |
| Host settings | `/home/rbrheating/rbrheating.com.txt` | Hosting account. Contains broker and mail settings. |
| Broker | `rbrheating.duckdns.org`; DuckDNS account and the broker host | DuckDNS account plus broker host access. The broker accounts and access rules are per system; rotate them after transfer. |
| Mail | `info@rbrheating.com` and the SMTP settings used by the controller | Mailbox and mail-provider account; reset and enable two-factor authentication. The address is used for support and for the controller's emailed backups and journals. |
| Deployment key | The SSH key used by `deploy.sh` and the deploy workflow | Hosting account and GitHub secrets; replace it rather than sharing the old key. |
| Backups | `backup/` and `map-history/` on each controller; any archive copies held by the maintainer | Held with the installation or the maintainer's records, not in this repository. They contain customer data and secrets. |
| Upstream AllSpeak | `allspeak.ai` and its repository, not controlled by this project | No transfer needed. The project continues to depend on it. |

## GitHub: the repository and the deceased-user policy

The repository is `github.com/easycoder/rbr`, under the personal account `@easycoder`. Three routes are available, in order of preference.

**The pre-designated successor, before anything happens.** GitHub lets the maintainer record a successor for a personal account in the account settings. Once the addendum names the successor, the maintainer should add them there; the successor is then recorded by GitHub rather than inferred after the event. The setting and its scope are described at <https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/maintaining-ownership-continuity-of-your-personal-accounts-repositories>. This is the cleanest route for a personal repository.

**The organization route.** If the maintainer creates a GitHub organization for the project, the successor can be added as an organization owner while the maintainer is still active. Ownership then survives an individual account problem, and the successor has a normal, auditable role rather than an emergency transfer. It should be done before it is needed if both people are willing.

**The emergency route.** GitHub publishes a policy for deceased users and for account ownership after a user dies. The statement for this project is:

> In the event of my permanent incapacity or death, the designated successor may apply to GitHub Support for transfer of repository ownership in accordance with GitHub's Deceased User Policy.

The policy is at <https://docs.github.com/en/site-policy/other-site-policies/github-deceased-user-policy>. It names next of kin, a pre-designated successor and other authorized individuals as the people who may ask. The successor should open a request with GitHub Support, explain the relationship, say whether they are the pre-designated successor, provide the evidence of the trigger and any legal confirmation GitHub asks for, and request transfer of the repository to the successor or to the project organization. GitHub may require proof of death or incapacity and proof of the successor's authority; the addendum and the legal representative's statement are the documents to have ready.

For permanent incapacity rather than death, the same policy is the starting point, but GitHub Support decides what proof it needs. Ask them rather than assuming the deceased-user route applies unchanged.

Do not attempt to take over the account by using the maintainer's password. Use the transfer process, keep the audit trail, and enable two-factor authentication on every account as soon as it is under the successor's control.

## The domain, hosting and broker

These are the parts a code fork cannot replace. The domain is what the controllers and the app are pointed at; the broker is what carries the messages; `rbr-users.json` is what makes a system's pairing work.

- **Registrar.** Transfer the domain or add the successor as the registrant/technical contact. Change the registrar recovery email, password and two-factor authentication. Keep the DNS records working while the transfer happens; a lapsed domain takes the update channel and the app with it.
- **Hosting.** The account at `/home/rbrheating` holds the site, the docs reader, `rbr-users.json`, the host settings and the deployment key. Transfer the account or restore its files into a new one. Test `./deploy.sh` from a checkout before announcing the transfer.
- **DuckDNS and broker.** Claim or transfer the DuckDNS name and take over the broker host. The broker has per-system accounts and access rules; after a transfer, rotate the broker passwords and the system tokens. `provision-system.py --rotate-token` rotates one system's token and unpairs every phone holding it, so coordinate it with the notice to users.
- **Mail.** `info@rbrheating.com` is the support and recovery address. Reset it, enable two-factor authentication, and update the SMTP settings in the host settings if the mail account changes.

## Credentials and emergency access

No password, private key, token or recovery code belongs in this repository. The project's credentials live in the maintainer's password manager. The emergency-access material — the recovery instructions and the location of the addendum — should be held where the successor or the maintainer's legal representative can reach it; placing it there is an open item in this plan.

The addendum to this plan should record:

- the successor's name, relationship and contact details;
- where the password manager's emergency kit is held and how the successor obtains it;
- the location of the domain, hosting and broker account records;
- the date the successor last confirmed that the material is reachable.

The successor should test the emergency access before it is needed, not during an emergency. A sealed envelope in a drawer that nobody can find is not access.

After a transfer, rotate every credential the maintainer held: GitHub, domain, hosting, mail, broker, deployment keys and the per-system tokens. Treat the old credentials as compromised by the change of hands, even if there is no reason to think they were exposed.

## What the successor should not do

- **Do not publish `rbr-users.json`, controller archives, journals, backups or customer data.** They contain passwords, tokens, addresses and household information.
- **Do not reuse the maintainer's personal password or recovery email.** Use the transfer processes and set up the successor's own recovery.
- **Do not transfer the domain or broker without the evidence of the trigger and, where one exists, the legal representative's authority.** A false claim of incapacity is a hostile takeover, not continuity.
- **Do not change the licence as an emergency measure.** Keep the MIT terms; any change is a separate decision with legal advice.
- **Do not promise customers that their data is unchanged if a rotation is required.** Say what was rotated and what they have to do.
- **Do not delete the old repository or site until the new owner has a working copy and a tested deploy.** Keep a backup until the transfer is complete.

## Communication

When the plan is invoked, the successor should publish:

- a notice in the repository's README and in a pinned issue, naming the successor and the new support route;
- a notice on the website, where customers and installers will see it;
- an email to the registered address of each system, using the same channel the project already uses for backups and journals;
- a clear statement if tokens or broker credentials were rotated, and what each phone or controller has to do.

Keep the notices short and factual. Do not publish personal details about the maintainer beyond what the family or legal representative has agreed.

## Review

This plan should be reviewed:

- once a year, even if nothing has changed;
- whenever repository, domain, hosting, broker or mail access changes;
- whenever the named successor changes;
- after any test of the emergency-access material.

Update the date at the top and the signed addendum. A continuity plan that has not been reviewed is a document about the past.

## To complete

The plan is written; the following are deliberately left as actions because they need a person or a legal decision:

- Name the successor, their relationship and their contact details in the signed addendum.
- Place the emergency-access material where the successor or legal representative can reach it, and test that it is reachable.
- Pre-designate the successor in GitHub account settings, and decide whether to create a GitHub organization and add the successor as an owner while the maintainer is active. These are cleaner routes than the deceased-user transfer.
- Record the domain, hosting, DuckDNS, broker and mail account recovery arrangements, without putting secrets in this file.
- Review the plan with the maintainer's legal adviser if the project's ownership or the domain is held through a company.

## Licence

The project is released under the MIT licence; see [LICENSE](LICENSE). The successor should keep that licence in place and preserve the copyright notice.

## Legal note

This document is an operational plan. It is not a will, a power of attorney, a contract or legal advice. The transfer of a domain, a hosting account, a broker or a GitHub repository is governed by the provider's procedures and by local law, and a legal representative should be involved where one exists. If the project is held through a company, the company's own succession arrangements take precedence over this plan.
