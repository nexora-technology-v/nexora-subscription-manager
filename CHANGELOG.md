# Changelog

## [1.9.1]

### Fixed — Paying to renew created a second config instead

The renew screen's buttons were `chk:` and `wpay:` — the same callbacks a new
purchase uses. `create_order` defaults to `kind="new"`, so pressing **تمدید**
built a brand new subscription: the customer paid to renew, received a second
config, and watched the one they meant to renew expire anyway.

### Fixed — Auto-renewal extended whichever subscription was newest

The renewal path did `subs[0]` — the most recently created subscription, not the
one that had triggered the renewal. A customer with three subscriptions saw the
wrong one extended while the expiring one lapsed.

Orders carry `renew_sub_id` now, set when the order is created and read back at
provisioning time. The lookup is scoped to the paying user, so an order can only
ever extend a subscription that belongs to them.

`bot/test_wallet.py` builds three real subscriptions, renews the middle one, and
checks the order carries that id — and that a subscription belonging to another
user cannot be found by the same query.

## [1.9.0]

### Added — `nexora check`, so the guessing stops

Three separate problems in this project were each chased twice before the real
cause turned up in a log that happened to get pasted. That is a waste of the
maintainer's time and it is on me.

`nexora check` collects, in one pass, everything those investigations needed:
the version on disk against the version actually running, the agent job queue
and exactly where it stalls, which ports the firewall can see and who owns them,
whether accounting can read x-ui, and whether any balance went negative.

The version comparison alone answers a question that came up repeatedly — a
panel that was updated but never restarted keeps serving the old code, and every
symptom then looks like "the fix did not work".

### Fixed — The agent restarted before reporting, so updates looked stuck

`update_self` ran `systemctl restart` and returned. The restart killed the
process before the result was posted, so the job sat on `taken` forever and the
panel showed an update that never finished — job 1840 in the reported log.

The result goes out first now; the restart happens after.

### Fixed — The intrusion page took over a minute to open

The owner lookup I added in 1.5.1 made one blocking DNS query per address, up to
sixty of them at 1.5 seconds each. The page now renders from cache immediately
and fills the names in behind it, so the second visit has them and the first
does not wait.

### Changed — Long lists are paginated, not expanded

"Show more" made the list longer, which is the problem it was meant to solve.
Numbered pages keep the page height fixed no matter how much data there is, with
first/last and a window around the current page once there are more than seven.

### Added — Export attacking addresses straight into the blocklist

Two buttons on the intrusion page: every attacker, or only the unknown ones —
the second skips tunnels and addresses your own clients connect from, because
blocking those means cutting your own customers. The file is in the format the
bulk blocker reads.

### Changed — The accounting date filters are Jalali too

The client filter's date range used bare Gregorian text fields. Anyone working
in a Persian panel holds the range in their head as Jalali.

## [1.8.1]

### Changed — The bot's messages now use the layout you asked for

A bold title under an emoji anchor, a rule beneath it, then sections with their
own thin rule, label-value rows, and copyable values in monospace. The delivery
and renewal screens lead the way.

The separator lines are back, but fixed at twenty characters. That was the
original objection and it was a real one — a long decorative line wraps on a
narrow phone and shreds the message. Twenty fits the narrowest screen there is.

### Fixed — A subscription showed the inbound's name instead of what was bought

`plan_id` is declared `ON DELETE SET NULL`, so the moment a plan is edited away
or replaced, the subscription loses the name of the thing the customer actually
paid for — and the label falls back to the inbound's remark, a server name the
customer never chose.

The plan name is written onto the subscription at purchase now and preferred
everywhere the subscription is named. Existing rows are backfilled from the
plans table on upgrade, for as long as those plans still exist.

## [1.8.0]

### Fixed — The monitoring report was cut in half before it arrived

`job-result` truncated the payload to 4000 characters and then parsed the
truncated string as JSON. A full server snapshot is larger than that, so the
parse always failed — and the failure was swallowed by a bare `except`, which
recorded the job as **successful** while storing nothing.

The agent log told the story: `sysmon` jobs returning real data with
`"level": "crit"`, and a page that stayed empty. The report arrived, was
destroyed on the doorstep, and the error went in the bin.

The full result is parsed now; only the copy stored in the jobs table is
shortened. The agent stops truncating structured output at all, and says so
explicitly if a result ever exceeds its limit instead of sending half a JSON
document.

### Fixed — Agents could never update themselves

`update_agent` kept failing with "این آدرس خارج از پنل مجاز نیست". The panel
runs behind nginx, so `request.base_url` gives `http://127.0.0.1:8100` — the
internal address, not the domain the agent knows. The agent rejects any URL that
does not start with its own panel address, and it is right to.

The URL is built from the forwarding headers now, so it matches what the agent
expects.

### Added — Blocking addresses in bulk, and proving they are blocked

A scan arrives with a hundred addresses and typing them one at a time is neither
practical nor error-free. Paste a list or load a file, and every address reports
its own result — "97 of 100" is useless without knowing which three.

The list exports in the same format it imports, so one server's blocklist loads
straight into another.

And each blocked address has a **verify** button that asks the kernel directly.
"I saw a success message" is not the same as "it is blocked", and only the
routing table settles it.

### Changed — Every date in accounting is Jalali, and picked not typed

The reseller start date, the settled-until date, and payment dates all use the
Jalali picker now. A date typed by hand into a Gregorian field is one mental
conversion away from being wrong, on numbers that end up on an invoice.

### Changed — Long lists stop taking the whole page

`LongList` shows the first few rows, keeps the rest behind a button, and adds a
search box once a list is long enough for that to matter. Applied first to the
service and process lists in monitoring, where a real server produces dozens of
rows and the two that are actually broken were buried among them.

## [1.7.2]

### Fixed — The monitoring report was only ever requested by hand

The agent log from a live server showed twenty-three `health` jobs in a row,
five minutes apart, and not a single `sysmon`. That is the whole explanation for
a page that never filled in: the scheduler queued health checks automatically
but `sysmon` was only ever queued when an admin pressed a button.

So the page was empty until the first click, and stale immediately after — which
looks exactly like a broken feature, because in every way that matters it was
one.

`sysmon` is queued in the same loop as the health check now, skipped while the
last report is under five minutes old so the queue does not fill with redundant
work. Open the page and the numbers are already there.

## [1.7.1]

### Fixed — Rejecting an order handed out free coins

The rejection path refunded `coins_used` back to the customer. Coins were never
taken at that point — they were only deducted when an order was **approved** —
so every rejected order credited coins that had never left the balance.

Sending a deliberately bad receipt was therefore a coin printer: order with 100
coins of discount, get it rejected, receive 100 coins, repeat. Unlimited coins
means unlimited discounts.

### Fixed — The same coins could pay for two orders

Because the deduction waited for approval, nothing stopped a customer creating a
second order while the first was still pending. Both stored the same
`coins_used`, both got approved, and both deducted from a balance that had only
ever covered one — with no condition on the UPDATE, so the balance simply went
negative.

Coins are now **reserved when the order is created** and released on rejection,
expiry or cancellation. Reserving makes both faults impossible at once: a second
order cannot reserve what is already held, and the refund on rejection now
returns something that was genuinely taken.

`spend_coins()` is atomic in the same way `spend_balance()` became in 1.6.1 —
the row only updates while the balance covers the amount, and a failed reserve
writes no transaction. Releases are marked so the same hold cannot be returned
twice.

`bot/test_wallet.py` now covers both currencies: ten threads race for coins that
cover three reservations, and exactly three win.

## [1.7.0]

### Added — Blocking an address without turning the firewall on

Enabling ufw on a remote server is a real decision, and treating it with caution
is right. But "this address is eating my server and I want it gone now" should
not have to wait for that decision.

A blackhole route does not involve the firewall at all: the kernel drops every
packet destined for that address, so the TCP handshake never completes and the
connection dies at the first step. It takes effect immediately, touches no
service, and is undone with one command.

Its limit is stated on the page rather than hidden: it kills the reply, it does
not filter the inbound flood. Enough for a scanner or a password guesser; a
volumetric attack still needs the firewall.

Blocked addresses persist across reboots — a routing table lives in memory, so
without a saved list an address the admin blocked would quietly reopen after the
next restart while they believed it was still shut.

### Added — Why a node sends no report

Twice I guessed at this and twice I was wrong, because nothing showed where the
job stopped. The queue has four stages — recorded, taken, executed, returned —
and any of them can be the one that stalls.

The diagnose panel now shows all four with timestamps and the actual error text,
plus the last fifteen jobs. A job stuck at "queued" means the agent is not
connected; stuck at "taken" means it is running and not answering; "failed"
shows what it said. Each state comes with the command to run next.

### Added — Jalali date picker

`<input type="date">` shows a Gregorian calendar. Someone recalling when they
started working with a reseller remembers it as "اول مهر ۱۴۰۳", not
"2024-09-22" — and converting in your head is where the error enters, on a field
that feeds straight into an invoice.

The picker is Jalali; the value sent to the backend is still ISO Gregorian, so
nothing changed on that side. The conversion is tested against known dates
including leap years and a thousand consecutive days round-tripped.

The first leap-year formula I wrote was wrong for 1403 — which is a leap year —
and the test caught it immediately.

### Fixed — Two focus rings stacked on every search box

A global `input:focus-visible` outline applied to the input inside the search
box, which already shows focus on its container. The result was a soft ring plus
a hard 2px outline a few pixels inside it. One indicator now, not two.

### Fixed — Number fields showed the browser's spinner arrows

They sit in the corner, match no theme, and in a right-to-left layout land
exactly where the eye expects the number. Where stepping is genuinely useful,
NumberStepper has its own buttons that match the rest of the panel.

## [1.6.2]

### Fixed — Accounting was throwing on every page load

Adding the month-source breakdown in 1.6.0 needed a `sources` field on each
group row. That edit silently failed and I did not notice, so the aggregation
wrote into a key that was never created: `KeyError: 'sources'` on every call to
the billing overview. The whole accounting section was down.

Two more faults were underneath it, both found by the end-to-end test written
to reproduce the first:

`app.py` imports the regex module as `_re`. Two functions added in 1.6.0 wrote
`re.match` instead — which compiles fine, because Python resolves free names at
call time, and only throws `NameError` when a user actually presses the button.

And the bulk start-date call asked the billing overview for its group list while
holding an open write connection. The overview opens its own connection and
writes to `client_seen`, so SQLite deadlocked and the page stopped with
"database is locked".

### Fixed — `۱۴۰۳-۰۶-۱۰` was accepted as a date

`\d` in Python matches Persian and Arabic digits too, so a Jalali date passed
the format check and was stored as if it were Gregorian. Every calculation on
it afterwards was meaningless. The pattern is `[0-9]` now.

### Fixed — The start-date banner disappeared after one visit

Once the panel records that it has seen a client, the month source changes from
"default" to "first seen" — but first-seen is today, which still gives one
month. The banner only looked for "default", so it vanished after the first page
load while the billing stayed wrong. Both sources count now.

### Fixed — The firewall could not see ports bound to a specific address

A port counted as public only when bound to `0.0.0.0` or `*`. Anything bound to
the server's own address — which is how tunnels are usually configured — was
treated as unreachable and skipped by both the suggestions and the pre-flight
check. The ports that mattered most were the ones missing.

Only loopback is exempt now. A private address is not: ufw filters those too, so
calling them safe would have let the pre-flight miss a service that enabling the
firewall then cut.

### Fixed — `nexora fix-xui` printed scrambled output

Seven of its messages had Persian and English mixed on one line, and the Persian
had been mangled in the file itself — leaving fragments like `ok "mode from and"`
and `ok " Service "`. Rewritten in English, the same way slow-doctor was.

## [1.6.1]

### Fixed — The wallet could be spent twice

Both places that take money used the same shape:

    fresh = db.get_user(tg_id)
    if fresh["balance"] < price: return
    db.add_balance(user_id, -price, ...)

Read, decide, then write — with nothing holding the balance still in
between. That was survivable while the bot processed one update at a time.
It stopped being survivable when the bot grew an eight-thread pool, and the
auto-renew scheduler runs in a thread of its own that the per-chat lock does
not cover. A customer buying a plan at the moment their own auto-renewal
fires is two deductions reading one balance.

Worse, the UPDATE had no condition on it, so the result was a negative
balance that appeared in no report and no alert.

`spend_balance()` makes the database hold the invariant instead:

    UPDATE users SET balance = balance - ?
     WHERE tenant_id=? AND id=? AND balance >= ?

No rows updated means not enough money — no transaction row is written and
the order is rejected with the reason. `add_balance` keeps its unconditional
behaviour for top-ups, refunds and admin corrections, where a negative
balance is a legitimate thing to record.

`bot/test_wallet.py` spends real money down real threads: ten of them race
for a balance that covers exactly five purchases, and exactly five win.

## [1.6.0]

### Fixed — Why node monitoring never arrived

Three faults stacked on top of each other, and none of them printed anything.

The agent reported version `1.0.0` from the first release and never bumped it,
so the "this agent is too old" check could not fire. The update job then sent a
relative URL, which the agent rejected as outside its own panel — so it could not
update either.

The root cause was underneath both: the agent downloads `monitor.py` from the
panel and cached it forever. `if not mod_path.exists()` was the only condition.
When the panel later grew a `snapshot()` function, the agent still held a copy
from months earlier and answered "no such function" — a failure that reached a
row in the jobs table and stopped there.

The panel now sends its version with every check-in and the agent re-downloads
its modules whenever that version changes. `netid.py` ships alongside them, so
a remote server detects tunnels and mapped loopback the same way the main one
does.

### Added — Signed agent requests

The token alone was enough to impersonate a node if it ever leaked — from a log,
a backup, anywhere — and it travelled on every request. Requests now carry an
HMAC-SHA256 signature over the body and a timestamp, so the token itself is not
what goes over the wire and a recorded request cannot be replayed later. Clock
drift beyond five minutes is rejected, comparison is constant-time, and agents
that do not sign yet still work so nothing breaks overnight.

### Fixed — Accounting counted from today instead of from the start

`_months_for` now reports **where its number came from**: a logged renewal, the
client's creation date, the group's start date, or the first time the panel saw
the client. Groups show the mix, so "one month" is no longer a silent guess.

Two real errors fell out of that. A config that ran for two years and expired
yesterday was billed as one month, because the span was measured to the expiry
date and came out negative; it now measures to today. And the panel records the
first time it sees every client, so this cannot recur for anything added from
here on — the past cannot be reconstructed, but it can stop growing.

The dashboard now says how many groups have no start date and sets them all at
once, instead of expecting eleven visits to eleven settings pages.

### Changed — Charts are curves

Catmull-Rom through the real data points with a gradient fill underneath, a
crosshair, and the value under the cursor. The line still passes through every
measurement — nothing is smoothed away, it just stops looking like a saw.

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
