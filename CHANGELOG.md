# Changelog

## [1.5.2]

### Fixed — The firewall offered to cut the tunnel

On a real server the panel suggested closing port 7777 with the note "nothing to
do with your service — process: backpack". backpack **was** the tunnel. Ticking
that box would have cut every customer whose traffic comes through Iran.

The keep-list was a hardcoded set of process names that knew about xray and nginx
but nothing about tunnel engines. It now uses the same list as everything else,
and a tunnel port is treated like SSH: it cannot be ticked, and `apply_plan`
refuses to close it even when asked directly.

Suggestions now have a third bucket. A port with no process name — a UDP port on
this server, which could easily have been the tunnel — used to be confidently
filed under "close". Guessing on the admin's behalf is worse than saying nothing,
so those go to "we don't know what this is" with the command to find out.

### Added — Turning the firewall on without risking lockout

Enabling ufw on a remote server is a bet: one missing rule and the connection
dies with no way back except the provider's console. Most people therefore never
enable it, which is the worst outcome.

The new page removes the bet. It lists exactly what would be cut, refuses to
proceed while SSH or a tunnel is uncovered, and then enables with a rollback
timer. If the admin does not confirm within the chosen window — because they got
cut off — the server disables the firewall itself and everything returns to how
it was.

### Fixed — Blocked addresses did not appear in the list

`ufw status` prints no rules at all while the firewall is inactive, even though
rules added then are stored and take effect the moment it is enabled. So blocking
an address reported success and then showed an empty list. Those rules are read
from `ufw show added` now and marked as pending.

### Fixed — The panel went white again, for the same reason as before

`Power` was used in the navigation without being imported — exactly the shape of
the `Activity` bug from 1.5.0. A sixth seam test now compares every component and
icon used against what each file imports, so this class cannot reach a release a
third time.

## [1.5.1]

### Fixed — The black screen had a second, simpler cause

`ConfirmModal` called `createPortal` with no container argument at all. React
throws #200 — "Target container is not a DOM element" — and tears down the tree,
so the panel went black **every single time that dialog opened**. 1.5.0 fixed
the error-message path but not this, which is why blocking an IP still failed.

`tools/test-components.cjs` now mounts every UI component in a real DOM and
asserts none of them throw. Pattern-matching tests could never have caught this;
only running the code does. It found a second one immediately: `EmptyState`
crashed whenever its optional icon was omitted.

### Fixed — Node monitoring stayed empty

The agent had reported version `1.0.0` since the beginning and never bumped it,
so the "agent too old" check never fired. Worse, the update job sent a relative
URL that the agent rejected as outside its panel, so the update could not happen
either. The agent now reports the real version, builds the URL itself when the
panel does not supply one, and an agent reporting no version at all counts as
too old.

### Fixed — "undefined کانفیگ در ۱۱ گروه"

The accounting dashboard read `totalClients`, which only a different endpoint
ever returned. It is part of the overview response now, along with how many of
each group's clients came from the bot.

### Fixed — Resellers billed for one month regardless of history

Months came from the client's creation date, and older x-ui versions do not
record one — so every client counted as a single month and a reseller working
for two years was billed for one. A group's **start date** is now used as the
fallback, which gives the admin a lever for exactly this case.

### Added — Whose address is this?

Reverse DNS names the owner of an attacking address. `65.108.213.175` resolves
to `your-server.de` — Hetzner, a datacentre, not someone's home line. The page
labels each address as datacentre or consumer ISP, which is as close to
"identify the real user" as anything can honestly get: a VPN exit cannot be
traced back from outside, but knowing it is a datacentre tells you blocking it
is low-risk, and knowing it is Irancell tells you it is probably a person.

### Changed — Firewall suggestions no longer need scrolling

Search, a capped list, and a "show the rest" button.

### Changed — Spacing is a system, not a habit

Every pair of sibling blocks inside a section is spaced by one rule using a
shared scale, instead of the previous rule that only matched a few specific
class combinations and left everything else touching.

### Changed — The bot sales report looks like the invoice

Same palette, same header, summary cards, alternating rows, a total line, and a
daily trend chart — instead of a bare table. The funnel shows drop-off between
steps, and the daily chart has a mean line and per-day detail on hover.

## [1.5.0]

### Fixed — Blocking an IP blanked the whole panel

FastAPI returns a validation error's `detail` as an **array of objects**. Forty-five
places in the panel rendered `j.detail` straight into JSX, and React refuses to
render an object as a child — it tears down the tree and the screen goes black
until a refresh.

`errText()` now normalises any detail shape into a readable string, and every one
of those places goes through it. An `ErrorBoundary` wraps the page content as a
second line of defence, so the next unknown crash costs one section rather than
the whole panel, with the menu still usable.

### Fixed — "ناعدد" in the accounting pages

`Number("...").toLocaleString("fa-IR")` returns the literal string **ناعدد** when
the input is not a number, and that is what was printed where an amount belonged.

`faNum` now separates three cases: nothing recorded gives an em dash, a real
number is formatted, and a non-numeric string (a clock time, a kernel version)
just has its digits converted. No path reaches that word any more.

### Fixed — Boxes with no gap between them

Spacing came only from a hand-written `mb-4` on each card, so wherever it was
forgotten two boxes touched. Sibling blocks inside a section now get automatic
spacing; existing margins collapse with it rather than doubling, and grid cells
keep their own gap.

### Fixed — Loopback counted as the busiest customer

`ss` reports local traffic as `::ffff:127.0.0.1`, which the loopback filter did
not match. On the live server that single entry held **751 connections — 26.7%
of everything** — and sat at the top of the "busiest peers" list as though it
were a customer. Addresses are normalised before any comparison now, so mapped
IPv4, private ranges and link-local are all excluded.

### Fixed — Only some tunnels were recognised

Tunnel detection matched a short list of process names and depended on `ss`
reporting them, which needs privileges it often does not have. **backpack** was
missing entirely. `netid.py` now identifies tunnels from the process table,
falls back to the ports those processes own, and knows eighteen engines.

### Added — Is this attacker a customer of mine?

Many attacking addresses are themselves VPN exits. The real address behind a VPN
cannot be discovered from outside — by this panel or anything else — and the
page says so rather than pretending otherwise.

The useful question has an answer: every attempting address is checked against
the addresses your own clients connect from, drawn from x-ui's IP records, the
Xray access log, and current connections. A match means a customer is sitting
behind that VPN, and blocking it cuts them off.

While wiring this up: `_connected_ips()` read a key named `top` that
`connections()` has never returned, so customer detection had silently never
worked at all.

### Fixed — Node monitoring never arrived

The `sysmon` command shipped in 1.4.0, but a node running an older agent simply
leaves the job queued for ever — the panel showed an empty page and no reason.
It now reads the agent's reported version, says plainly that it is too old, and
offers a button to update it without opening an SSH session. A failed job's
error is shown too.

### Changed — Accounting is separate from the bot

Bot customers are your direct customers; accounting exists to bill resellers.
Clients the bot sold are identified from the bot's own database — not guessed
from a name pattern — and are never billed to a reseller, even if they end up
inside a group. Each group reports how many of its clients came from the bot.

## [1.4.2]

### Fixed — slow-doctor treated resellers as if they did not exist

The previous patch compared x-ui's client list against the bot's subscriptions
and reported everything else as unaccounted. That is wrong for anyone selling
through resellers: those clients are real, they belong to a group, and the
panel bills them through accounting. The script was calling normal business
"a problem".

It now breaks clients down per reseller group and only warns about clients that
belong to no group *and* were not sold by the bot — the only ones genuinely
outside every channel.

The connections-per-client figure had the same fault. Dividing 2250 connections
by the bot's 6 subscriptions produced 375 and a red BAD line, when the real
denominator is every enabled client in x-ui. The basis is now printed alongside
the number, and says so explicitly when x-ui cannot be read.

## [1.4.1]

### Fixed — slow-doctor printed its own separator lines as data

The script defined a shell function named `head`. A function shadows the
coreutil of the same name, so every `| head -8` in the script was calling that
function with "-8" as a title — printing a decorative line instead of the first
eight rows.

On a real server that meant the process list, the busiest peer IPs and the
whole Xray section came back as `-7`, `-1` and rows of `──────`, with no error
anywhere to explain it. The function is now called `section`.

`tools/test-slowdoctor.py` asserts that no function in the script shares a name
with a coreutil it pipes into, so this cannot come back.

### Added — slow-doctor compares x-ui against what the bot sold

A connection count that looks impossible usually has a dull explanation: x-ui
holds clients that were added by hand and the bot never sold. The script now
counts them, says how many are enabled beyond the bot's subscriptions, and
lists the heaviest clients by traffic — one client far above the rest is a
shared config, many clients evenly spread is simply more users than you thought.

## [1.4.0]

### Added — The bot uses what Telegram actually offers

Messages built HTML by hand inside f-strings. One unclosed tag makes Telegram
reject the whole message, so the customer sees nothing and the log holds only a
400. `bot/fmt.py` turns the tag vocabulary into functions that always escape
their input and always close, and `tg.py` validates every message before it
goes out — a malformed one is sent as plain text rather than vanishing.

What that bought, per the formatting request:

- monospace for everything copyable — card numbers, subscription links,
  referral codes, order ids
- blockquotes for asides, and **expandable** blockquotes for the install guide
  so a long explanation no longer buries the screen
- strikethrough on the old price beside the bold new one, so the customer sees
  the saving instead of reading "20% off"
- spoilers where curiosity is the point
- hyperlinks instead of raw URLs
- an emoji at the start of each line as a visual anchor

`bot/test_fmt.py` runs the validator over all 44 rendered screens, so a broken
tag fails the build rather than a customer's message.

### Fixed — "تمدید" meant nothing when you had three subscriptions

Three subscriptions produced three identical buttons. Every screen now names a
subscription by plan **and** by the inbound's own remark — the name you gave the
server in 3x-ui — so a customer with servers in two countries can tell them
apart. The welcome screen listed only the first subscription's days remaining
without saying which one it meant; it now lists up to three by name.

### Added — Who is knocking on SSH

A new firewall page reads the auth log and groups failed logins by IP. The
distinction that matters: IPs currently connected to your service are almost
certainly your own customers mistyping, and blocking one costs you a customer.
Those are separated, coloured differently, and skipped by batch blocking.

Each hardening gap — root login, password auth, port, fail2ban — comes with the
exact command to fix it, and the one that can lock you out says so.

### Fixed — The firewall rules table was twice as long as it needed to be

ufw lists every rule twice, IPv4 and IPv6. They are merged now, with filters by
action and scope, so the page stops being a scroll.

### Added — Expenses, and what they do to profit

Servers abroad, the Iran server, traffic top-ups and domains had nowhere to
live, which made "revenue" a number that feels like profit and isn't.

Expenses now have a page, split by category, with the recurring monthly total
called out. Euro costs convert through the free-market rate, but the toman
amount is **frozen at entry** — recomputing later would make last month's cost
move with the market. A manual rate always beats the live one. An expense that
cannot be converted is refused rather than stored as zero.

The ledger page answers the question directly: billed, received, outstanding,
spent, and profit from money actually received. Debtors are listed so a
reseller's payment lands against the right balance.

### Added — The Iran server, managed from this panel

The agent now runs the panel's own `monitor.py` and `firewall.py`, downloaded
from the panel at run time. A second copy inside the agent would drift within a
release and report different numbers for the same server; this way every node
reports with identical thresholds and field names. No second panel install.

### Added — Bot sales report as a PDF

Same house style as the reseller invoice. Its CSV download was also broken: the
link carried no auth header, so the browser saved a 401 body and called it a
spreadsheet.

### Fixed — Things found while building the above

`app.py` referenced a `log` that was never defined and had no module-level
`import logging`. The panel's node list came from an endpoint that does not
exist. `test-seams.py` only recognised `fetch` and `call()`, so a helper named
`useJson` made four new routes look uncalled.

CI now also runs on Python 3.10: `install.sh` uses whatever `python3` the distro
ships, and testing only 3.12 would let syntax that breaks on Ubuntu 22.04 ship
silently.

### Changed — App.jsx was 11,418 lines in one file

Every panel change meant searching a file with 110 components in it. That is the
reason the firewall suggestion UI stayed missing for two releases: the backend
endpoint existed, nothing called it, and nobody could see the gap.

It is now 24 modules in four layers, each importing only downward:

    lib/        constants, formatting, shared hooks
    ui/         base components, no domain logic
    sections/   one file per domain — bot/ is split again by page
    shell/      the workspace switch
    App.jsx     334 lines: state, routing, layout

The split was done mechanically rather than by hand — a script mapped every
top-level declaration, worked out which identifiers each module actually uses,
and generated the imports from that map. Two bugs in the script were caught by
the tests before anything was committed: the app component being swallowed into
the wrong module, and the first icon in the lucide import list going missing,
which the build did not catch but `test-panel-runtime.js` did.

Behaviour is unchanged; the bundle is the same size to within a kilobyte, and
all 487 tests pass.

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
