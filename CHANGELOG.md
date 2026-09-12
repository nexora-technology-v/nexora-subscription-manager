# Changelog

## [Unreleased]

### Added — CI, so the tests actually run

The project had 475 tests that only ran when someone typed the command by hand.
`.github/workflows/ci.yml` now runs all of them on every push and pull request:
Python suites, seam tests, the bot text preview, the frontend build, and the three
Node suites. Tags additionally run the release gate.

### Added — `tools/test-seams.py`

Every bug that reached a customer in this project was a wiring bug, not a logic bug.
One half of the code declared something and the other half never heard about it: a
button with no dispatcher branch, a query against a table that was never created, a
backend route with no caller, a method defined twice.

Ordinary tests never caught these, because a test exercises a *function* and a seam
is not a function. This file counts both sides of five seams and diffs them:

- backend routes against frontend callers
- SQL table names against the real schema
- settings keys the bot reads against fields the panel can write
- duplicate function definitions in one scope
- handler names referenced but never defined

It found twelve real problems on its first run.

### Fixed — Eight bot settings the panel could never set

`trial_enabled`, `ask_phone`, `support_username`, `order_ttl_minutes`, `email_prefix`,
`sub_base_url`, `help_text` and `admins` were all read by the bot and written by
nothing. Each had a sensible fallback, so nothing crashed — the features were simply
frozen at their defaults forever. The free trial in particular could not be switched
on by any means.

The bot settings page now has a "رفتار ربات" section for all eight.

### Fixed — Error alerts you can act on

When an update failed, the admin group got the update id and "details are in the
server log", which meant opening an SSH session to learn anything. The alert now
carries the exception type, its message, and the button or command that triggered it —
none of which is sensitive. Customer message text is deliberately still excluded.

### Added — `tools/release-check.py`

The release checklist used to live in someone's memory. It is now a command that
verifies VERSION, `package.json` and the git tag agree, that CHANGELOG has a
non-empty section for the version, that the tree is clean and on `main`, and that
every suite passes. It exits non-zero if anything is missing, and CI runs it on tags.

### Known — Four backend routes with no caller

`test-seams.py` reports these as open debt rather than failing on them:
`/api/admin/reset-defaults` (resets all config with no confirmation),
`/api/admin/billing/overview`, `DELETE /api/admin/billing/payments/{id}` (the panel can
record a payment but not remove one), and `/api/admin/health/local`.

## [1.3.0]

### Fixed — Topping up the wallet crashed every time

`wallet_topup` and `wallet_topup_amount` both ran `SELECT * FROM cards`. There is no
`cards` table — bank cards live in the tenant's settings JSON, and always have. Every
customer who pressed "شارژ کیف پول" hit an `OperationalError` that the dispatcher
swallowed, so the button simply did nothing and nobody was told why.

Both call sites now read `ctx.s["cards"]` and pick one through `core.pick_card()`, the
same path the purchase flow has always used.

This was found by building a preview that renders every bot screen. The two screens had
never been exercised by a test because no test had ever pressed that button.

### Added — Every date the bot shows is now Jalali

The bot told an Iranian customer their subscription expires on `2027-01-15`. Nobody
reads that and knows whether it is next week or next year.

`core.fa_date()` and `core.fa_datetime()` convert through `jdatetime`, so expiry now
reads `۲۵ دی ۱۴۰۵` and an order timestamp reads `۱۴۰۵/۰۶/۲۰ — ۱۶:۵۱`. If `jdatetime`
is missing or the stored value is malformed, the old Gregorian string comes back
unchanged — showing a date must never be able to kill a message.

### Added — Firewall rule suggestions in the panel

The backend has had `/api/admin/firewall/suggest` and `/apply-plan` since 1.1.0 with
nothing in the panel calling them. The endpoints were dead code.

The firewall workspace now reads what is actually listening on the server and, for each
service, says whether the port should stay open or be closed, and why. Close suggestions
arrive pre-ticked because they are the reason the section exists; keep suggestions do
not, so nobody accidentally opens a door that was shut. Nothing is applied without an
explicit confirm, and SSH is still refused as a close target.

### Added — `bot/preview_texts.py`

Renders all forty bot screens to a text file without touching Telegram or a real panel:
the purchase flow, wallet, coins, referrals, tickets, renewals, the expiry reminder, the
automatic-renewal success and failure notices, every admin page, and the daily group
report.

It exists so bot copy can be reviewed as a whole instead of one screen at a time — and
it earned its keep immediately by surfacing the wallet crash and a Gregorian date that
had been missed.

### Added — `tools/test-bot-buttons.py`

Walks every `callback_data` the bot can emit and asserts the dispatcher has a branch for
it. Two buttons had shipped with no handler at all: "تمدید" and the admin ticket-reply
button. Both were dead on arrival and neither was noticed by a human.

### Fixed — `slow-doctor.sh` printed garbled IP addresses

The Persian labels inside `awk printf` collided with the terminal's bidirectional text
handling, and the connection parser read a fixed `$5` where the column position varies
by `ss` version. Rewritten in English, parsing `$NF`.

## [1.2.0]

### Fixed — Every bot message re-read the settings 31 times

`ctx.s` was a property that opened a fresh SQLite connection, ran a query and parsed JSON
on **every access** — and handlers touch it in 31 places. One simple message meant dozens
of disk round-trips before the bot did any actual work.

Measured: 2ms per read on an SSD, 62ms of pure overhead per message, and that is a fast
disk. On a VPS with shared storage it is several times worse.

Settings and tenant data are now cached for two seconds — short enough that a change made
in the panel appears effectively instantly, long enough that a single message reads them
once. Overhead per message dropped from 70ms to under 0.1ms.

### Fixed — SQLite locked the whole database on every write

The bot opened its database in the default journal mode, where a write blocks every
reader. That stayed invisible while updates were processed one at a time, but 1.0.0
introduced a pool of eight workers, and this is exactly where they queued up behind each
other.

WAL is now enabled, with `synchronous=NORMAL` and a 20-second busy timeout. Eight threads
running 60 mixed read/write operations each complete with no lock errors. Filesystems
that cannot support WAL fall back silently to the previous behaviour.

### Added — `slow-doctor.sh`

The panel can only see so much from inside. This script measures the server itself and
says what each number means: CPU saturation relative to core count, memory and swap
pressure, real disk write speed, service restart counts, **latency to Telegram** — which
dominates how fast the bot feels — SQLite journal mode and size, and the busiest IPs.

Run it with `sudo bash slow-doctor.sh` and send the output.

### Changed

- Tunnel peer lookup is cached for two minutes. Detecting them cost an extra `ss` call on
  every sample, which on a page refreshing every eight seconds is work for nothing

### Reverted

A cache for the panel's `load_config` was written and then removed: measured against the
real config it was *slower* than reading the file, because the defensive deep copy cost
more than the read it replaced. Complexity that does not pay for itself does not ship.

## [1.1.0]

### Fixed — The referral link never told anyone anything

Every signup action — welcome bonus, admin group notice, telling the referrer — lived in
`cmd_start` behind an "if this user is new" check. But `_on_message` calls
`_get_or_create` first, so the user already existed by the time `cmd_start` ran and the
whole block was skipped. With the phone gate enabled, `cmd_start` does not run on first
contact at all. The code had been dead for a long time while looking entirely reasonable.

It now lives where the user is actually created. The referrer hears the moment someone
joins with their link, sees how many people they have invited, and is told the coin
arrives after that person's first purchase — rather than waiting for a reward that was
never coming yet.

### Fixed — The renew button did nothing

It was rendered in "my subscriptions", but no branch in the callback dispatcher handled
it. The callback fell through and returned `None`, so pressing it produced no reply and
no log line.

Renewal now opens a page naming the plan, its volume and duration, days remaining and the
config name. Someone holding three subscriptions could not otherwise tell which one they
were about to pay for. Auto-renewal messages name the plan for the same reason.

### Fixed — Tunnels counted as suspicious traffic

The Iranian node carries every customer's traffic, so it always topped "unusual usage"
and buried real warnings underneath itself. Tunnel peers are now identified from the
tunnel database and from processes belonging to known engines, shown separately as your
own infrastructure, and excluded from the heavy-usage check.

### Added — The firewall proposes rules

Reads what is actually listening and suggests what to do with each port: keep SSH and the
panel's own services, with the reason attached to each; close anything public that
belongs to neither; ignore loopback-only ports; skip ports that already have a rule.
Nothing is applied without an explicit confirmation.

### Changed

- Maintenance renamed to "تازه‌سازی خودکار سرویس", with a description that explains why
  an admin would want it and says plainly that a healthy server does not need it
- More guidance text moved into blockquotes, which Telegram renders with a side rule so
  an explanation reads as an explanation rather than another instruction

## [1.0.0] — First release

Nexora is a subscription manager for 3x-ui: a customer-facing subscription page, a
Telegram sales bot, reseller billing, tunnels, a firewall manager and server monitoring.

### Subscription page

A customer page with 32 appearance combinations, one-click add to Happ, v2rayNG and
V2Box, install guides per platform, four languages, and a live usage view fed from the
panel's own headers. Ships as a single self-contained HTML file with the IRANSansX
webfont embedded, so it renders identically wherever x-ui serves it from.

### Telegram bot

Sells plans, takes card-to-card receipts, and delivers configs. A receipt is only marked
approved once the config actually exists in the panel, so a failed provision leaves the
order in the queue to retry rather than stranding a paying customer.

Every config arrives with a QR image, a one-tap copy button for the link, and the raw
config URLs as a fallback if no subscription link could be built. Card numbers and
amounts get their own copy buttons, stripped of dashes so banking apps accept them.

Updates are processed concurrently — eight at a time by default, tunable with
`BOT_POOL_SIZE`. Messages from the same chat stay strictly ordered, so a slow config
build for one customer never blocks anyone else.

### Billing

Periodic invoices for resellers, per-plan and per-gigabyte rates, commission tracking for
affiliates on every purchase rather than only the first, and a sales report. Volume above
the highest configured rate falls back to that rate instead of silently billing zero.

### Tunnels

Connects an Iranian server to an overseas one with five engines — Backhaul, Chisel,
Rathole, GOST and FRP — with two-sided deploy, latency measurement and health checks.

### Firewall

Reads and manages ufw rules from the panel. Enabling the firewall is refused when no rule
would keep SSH reachable, automatic reboot needs an explicit confirmation, and rules
covering critical ports cannot be deleted without acknowledging what they protect.

### Monitoring

CPU, memory, disk, network, services and open ports, each with the threshold that makes
it dangerous. Open ports lead with counts by risk and filter by risk, exposure and
search. Active connections show which IPs hold the largest share, with tunnel traffic
recognised rather than flagged. Usage history samples every five minutes and reports the
quietest hour of the day, which is what the maintenance schedule should be set to.

### Testing

```
test_bot.py             73
test_flow.py            76
test_admin.py           39
test_xui.py             24   against a simulated 3x-ui v3 panel
test-billing.py         13
test-maintenance.py     24
test-firewall.py        23
test-bot-throughput.py  12
test-subpage.js         21
check-api-contract.py, test-render.cjs, test-serve.py
```
