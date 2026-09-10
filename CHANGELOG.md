# Changelog

## [1.5.0]

### Added — Which customer is consuming, not just which IP

Connection counts answer "which address", never "which customer". This reads real
traffic from the panel database and ranks configs by consumption: gigabytes used, share
of the server total, and how much of their own quota is gone.

Anyone past 90% of their quota is flagged. That is the moment to offer a renewal rather
than wait for them to run out and complain.

### Added — Usage history and the quiet hour

A sample of CPU, memory, connections and unique IPs is stored every five minutes,
alongside the existing health loop so it costs nothing extra. Two days are kept — more
would grow the file without improving any decision.

The page shows the last 24 hours as two charts, plus a 24-bar strip of the average for
each hour of the day with the busiest hour in red and the quietest in green. The quiet
hour is the one that matters: it is exactly what the maintenance schedule should be set
to, and until now that was guesswork.

Charts are inline SVG with no library — a line chart does not justify 120 KB of
dependency. Series are downsampled to 64 points, because 288 samples across a few
hundred pixels renders noise rather than a trend. Each series carries its own label and
value, so colour is never the only thing distinguishing them.

### Changed — Server page rebuilt

Reordered so the page answers questions in the order they get asked: how is it doing
now, what has it been doing, who is causing it, who is connected, what is exposed, when
does it get maintained.

## [1.4.0]

### Added — Active connections

Open ports tell you which doors exist. This tells you who came through them. When the
server feels slow, the first question is which IP is taking the largest share, and the
panel could not answer it.

Reads established connections and reports the total, unique IPs, the heaviest IPs with a
share bar, and the busiest local ports. An IP holding 15% or more of all connections
while having at least 20 of them is flagged — below that it is normal variance and
alerting would just be noise. Loopback is excluded, since the server talking to itself
is not customer usage.

The flag comes with the two things that actually cause it: one subscription shared
between several people (lower the plan's concurrent IP limit) or someone scanning
(`ss -tunp | grep <ip>`).

### Added — Scheduled maintenance

Restarts Xray in a low-traffic window so memory leaks and dead sessions do not
accumulate. Defaults to 05:00 server time — the trough for Iranian VPN traffic, after
the night users sleep and before the morning ones wake.

Restarting Xray costs about a second of downtime; a full server reboot costs one to two
minutes. The two are deliberately not equal in the interface: automatic reboot is
refused by the API unless `confirmedReboot` is explicitly set, and the save button stays
disabled until the warning has been acknowledged. A mis-click should not be able to take
the sales server down overnight.

If more than a configurable number of connections are active when the window arrives,
the run is skipped and the reason is recorded rather than restarting mid-peak.

### Changed — Open ports no longer bury the page

A real server lists dozens of ports, and the full table pushed everything below it off
screen. The card now leads with counts by risk and shows only what needs attention —
high and medium risk, capped at six — with the rest behind one button.

### Changed — Type scale raised across the panel

Body text below 12px fails the readability floor, and 334 of the panel's 653 font-size
declarations were under it, some as small as 7px. Every size moved up one step: the
smallest body text is now 12px, headings gained a point, and the phone-preview mockup
keeps its deliberately small type.

### Added

- `tools/test-maintenance.py` — 24 tests covering the schedule window, both safety
  gates, and connection counting

## [1.3.0]

### Added — Server monitoring

A new **مانیتورینگ سرور** page. Until now, knowing what the server was doing meant SSHing
in and running commands by hand — and even then, a raw number like `load: 3` tells you
nothing unless you remember how many cores the machine has.

Every metric here arrives with its threshold and an explanation of what it means for a
VPN server specifically, behind a "چرا مهم است؟" toggle:

- **CPU, load, memory, swap, disk** — with the load explanation dividing by the actual
  core count, since that is the only way the number means anything
- **Live throughput** — receive and transmit per second, per interface. This is what your
  customers are actually consuming
- **Active connections** — a direct read on how many people are connected right now, plus
  SYN-flood and TIME-WAIT detection
- **Xray** — service state and a count of warnings in the last 30 minutes, so a
  misconfiguration surfaces before customers complain
- **Open ports** — every port facing the internet, with the listening process and a risk
  rating. An unrecognised public port is flagged
- **Heaviest processes** — what is actually eating the machine
- **Services** — including services that restart repeatedly, which is worse than being
  down because it looks healthy at a glance
- **Pending updates** — security updates are treated as critical, because on a box with
  public ports a published vulnerability is the most urgent risk you carry
- **Security** — failed SSH logins over 24h with the worst offending IPs, fail2ban, and
  firewall state

The page refreshes every 5 seconds. Package and security checks take seconds to run, so
they stay on demand behind a button rather than blocking the live view.

Only read-only commands from a fixed list are used; no user input reaches a shell.

### Fixed — A disabled firewall was reported as enabled

The `ufw` check tested whether the output contained `active` — and `inactive` contains
`active`. A firewall that was off reported as on, which is precisely the moment the check
existed to warn about. Found by the new tests, not in production.

## [1.2.0]

### Added — Message a customer straight from the panel

`POST /api/admin/bot/message/{tg_id}` sends through the bot, so there is no need to
leave the panel and hunt for someone in Telegram — which was impossible anyway for users
with no username. It arrives headed "پیام از پشتیبانی". If the customer has blocked the
bot you are told so plainly instead of the message vanishing.

Reachable from the users list and from the customer's file.

### Added — Filters for the users section

The old page showed the last 50 users and a search box. It now filters by subscription
state (active, expired, never subscribed), buyers, phone on file, wallet balance, coins,
referred, and blocked — each chip showing its own count, so you can see the shape of your
user base without clicking. Sorting by newest, oldest, highest spend, balance, coins or
last activity, with paging.

Each row now carries what you actually need to decide something: phone number, number of
approved orders, total spent, and whether a subscription is live.

Search also covers phone numbers, and runs as you type.

### Fixed — Half the panel was using the wrong font

`JetBrains Mono` was loaded from Google Fonts. From Iran that request usually fails, so
every number, ID, card number and config name — 140 places — silently fell back to the
system monospace and looked nothing like the rest of the panel.

Those now use a `--mono` variable with a local fallback chain that exists on every
system. The Google stylesheet is still requested, but no longer blocks rendering, so a
blocked request costs nothing.

### Changed — Telegram's own features in bot messages

- a **copy button** on the delivery message puts the subscription link straight on the
  clipboard, no text selection
- `blockquote` for asides, so tips read as tips rather than more body text
- a typing indicator while the config is being built, which takes a few seconds and
  previously looked like the bot had died

## [1.1.9]

### Fixed — The config was built but never reached the customer

Telegram only accepts `http`, `https` and `tg` URLs in inline keyboard buttons. The
delivery message carried `happ://`, `v2rayng://` and `v2box://` one-click buttons, so
Telegram rejected **the entire message** with `BUTTON_URL_INVALID` — not just the
offending button. The config existed in the panel, the customer got nothing.

The same exception then travelled up through `approve_order` into the callback handler,
so the admin's confirmation never ran either and the receipt kept its ✅/❌ buttons,
looking exactly as if the approval had never registered.

Three layers now stop this:

- `kb()` drops URL buttons whose scheme Telegram will not accept. A missing button beats
  a message that never sends
- delivery retries without the keyboard if Telegram rejects the markup — the text is
  what matters, the buttons are decoration
- a delivery failure can no longer break the approval flow. The admin is told the config
  exists but did not reach the customer, with the link to send manually

One-click app buttons need an `https` redirect to work through Telegram; the delivery
message now links to the subscription page when its address is `https`, and the raw link
stays copyable in the text either way.

`dispatch` also gained the try/except its docstring had been promising, so one bad update
can no longer take down a tenant's loop.

### Fixed — Configs billed at zero despite rates being set

`_price_for` matched an exact rate, then the nearest higher one, then gave up. A group
with rates at 30, 50 and 100 GB and a customer on a 200 GB config found nothing above
200, returned no rate, and that line was billed as **zero** — silently, while the panel
reported rates were configured.

It now falls back to the highest defined volume rate. Unlimited configs are deliberately
still unpriced without an explicit unlimited rate, since a volume rate cannot be
generalised to unlimited — but the review list now says which of the two situations it
is, because the fix differs.

Added `tools/test-billing.py` covering rate selection, including the case that was
silently zeroing money.

## [1.1.8]

### Fixed — Approving a receipt did nothing, forever

Tapping ✅ on a receipt produced no config, no error, and no visible change: the same
receipt sat there with the same buttons, apparently waiting to be approved again. Two
bugs stacked on top of each other.

The callback handler called `approve_order` and **discarded its return value**. Success
or failure, nothing was answered, nothing was edited, no message was sent. The admin
had no way to know anything had happened — and the panel's real error message was
thrown away every single time.

Worse, the order was marked `approved` *before* the config was built. When the build
failed the status stayed `approved` with no subscription attached, so the next attempt
was rejected with "this order is already approved". The order was unrecoverable and the
customer had paid for nothing.

Now the config is built first and the order is only marked approved once it exists. A
failure leaves the order in the review queue so it can be retried, reports the panel's
actual error to the admin, and says the order is still pending. Orders already stuck in
the `approved`-without-a-config state from earlier versions can be approved again
instead of being refused.

### Changed — Bot messages are readable again

1.1.7 removed the decorative `━━━` rules, which was right, but stripped the functional
emoji along with them and left blocks of undifferentiated text. Rows now carry a leading
marker so the eye can scan them — 📦 for volume, ⏳ for validity, 📱 for devices, 💰 for
amounts, 💳 for the card, 🔗 for links — on plan details, checkout, delivery, my
subscriptions, the wallet, and the in-bot admin panel. No decorative rules were brought
back.

## [1.1.7]

### Fixed — A paid order produced nothing when no default inbound was set
`provision` refused outright with "inbound پیش‌فرض تنظیم نشده است" when neither the
plan nor the tenant named an inbound — which is the state a fresh install is in, and
the state the production panel was found in. From the customer's side that is paying
and receiving nothing, because of one unset setting. It now falls back to the first
enabled inbound in the panel and logs that it did.

`xui-trace.py` never caught this because it already fell back to the first inbound
itself, so its seven green steps said nothing about the path the bot actually takes.

Upgrade from 1.1.6 if a config was never delivered after an approved receipt.

## [1.1.6]

### Fixed — Renewals and blocking never worked against 3x-ui 3.x
Checked against the panel's own OpenAPI spec (183 routes), four assumptions in the
client were wrong:

- The config read-back used `GET /panel/api/clients/{email}`, a route that does not
  exist. It 404'd silently, so the uuid we stored was one we had invented locally
  rather than the one the panel issued. The customer's config worked, but every later
  lookup searched for a uuid the panel had never heard of
- Even on the right route, the code took the `id` field — in a v3 `ClientRecord` that
  is a numeric database row id. The real uuid lives in `uuid`
- Updates went to `POST /panel/api/inbounds/updateClient/{uuid}`, which this panel does
  not have. The v3 route is `POST /panel/api/clients/update/{email}`. Until now,
  renewals, auto-renewals and blocking a user always failed with "client not found"
- Lookup by uuid only searched the inbound's settings JSON, where v3 keeps no clients

The client now reads the uuid back from the correct route, accepts only uuid-shaped
values, updates through the v3 route, and prefers the email — which is the real
identifier in v3 — wherever one is available.

### Fixed — Customers could be delivered an empty message
When no custom subscription domain was set, the subscription URL stayed empty and the
delivery message said the link could not be generated. The panel's own subscription
service runs on a separate port and path, so the panel address alone is not enough;
those settings are now read from `POST /panel/api/setting/all` and the link is built
from them. A custom domain still takes precedence. If there is still no link, the raw
config URLs are sent rather than nothing.

### Fixed — The panel's own connection test lied
`find_client` was called with the probe email in the inbound argument, so the "read the
config back" step reported failure even when everything had worked. Cleanup passed the
email where a uuid was expected, which left test clients behind in the panel.

### Added — Inbound selection page
The endpoint existed since 1.1.5 but had no interface. The bot workspace now has an
Inbounds page: every inbound by name with its protocol, port and enabled state, and the
three modes as a choice — every enabled inbound, the default one only, or a manual
selection.

### Added — Regression test for the 3x-ui client
`bot/test_xui.py` runs the client against a simulated v3 panel that mirrors the real
API contract: JSON-only bodies, a server-minted uuid alongside a numeric row id, the
nested read response, and an empty 204 on delete. Each of those was a real bug once.

### Changed — Bot message rewrite
Warmer wording with the structure of a real storefront. Decorative `━━━` rules are gone
— they wrap badly on phones. Numbers a customer reads are now in Persian digits, while
anything meant to be copied — card numbers, links, referral codes, order ids — stays in
Latin so it can still be pasted and searched.

## [1.1.5]

### Fixed — Broadcast never sent anything
It called `ctx.bot.send_msg`, which does not exist — the method is `send`. Five other
calls had the same mistake, including affiliate commission notices and wallet top-up
confirmations, so none of those messages were arriving either.

Broadcast now shows live progress, respects Telegram rate limits, and separates users
who blocked the bot from real failures — marking them inactive so they stop being
counted.

### Added — Choose which inbounds a config lands on
Instead of typing an inbound id, the panel lists them by name with protocol and port.
Three modes: every enabled inbound, the default one only, or a specific selection. A
plan can override the global setting when one product belongs on particular servers.

### Fixed
- A custom subscription domain now takes precedence over the link the panel generates.
  The panel builds from its own address, which may carry a non-standard port or a hidden
  path; if you set a clean domain, that is what customers get
- `ctx.xui` was called as a method where it is a property, so usage figures never loaded
- Delivery message now names the plan, shows the expiry date and config name, and says
  plainly when no link could be generated instead of arriving half-empty

### Fixed — The customer received nothing
A config was created but no link was sent. The subscription URL was only built when a
base URL happened to be configured; otherwise it came back empty. Version 3 exposes the
links itself, built from the real inbound settings, so they are now fetched from the
panel.

### Changed
- Clients attach to every enabled inbound, so a customer keeps working when one server
  goes down
- flow defaults to xtls-rprx-vision, without which REALITY configs do not work
- The subscription list now shows a usage bar with real traffic from the panel, how much
  is left, days remaining with the expiry date, and the config name

### Fixed — Nested response and traffic paths
Version 3 returns a client wrapped in a `client` key with usage and inbound ids beside
it, not flattened. Reads are now unwrapped so the rest of the code keeps working with a
plain dictionary.

Traffic and traffic-reset also moved: `/panel/api/clients/traffic/{email}` and
`bulkResetTraffic` on this version. Both fall back to the inbound paths on older panels.

### Fixed — Reading a config back after creating it
The lookup tried four guessed paths and gave up. It now falls back to fetching the full
client list and matching on email, which works whatever the single-client route is
called. `xui-trace.py` lists every client GET route the panel offers, so the right one
can be used directly instead of searched for.

### Fixed — Reading back and deleting a config
Creation works, but the two operations around it did not. Lookup assumed a string
response and crashed on the dict the panel returns. Delete used paths from older
versions and passed a UUID where this version wants an email — and it treats an empty
204 body as an error when that is exactly what a successful delete returns.

Both now pick their path from the panel route list, delete falls back to bulkDel, and an
empty body with a 2xx status counts as success.

### Fixed — Config creation, from the panel own example
The OpenAPI spec for `/panel/api/clients/add` carries an example, and it settles the
question:

    {"client": {"email": ..., "totalGB": ..., "expiryTime": ...,
                "tgId": 0, "limitIp": 0, "limitHwid": 0, "enable": true},
     "inboundIds": [3, 5]}

Nineteen shapes had been tried and every one missed it. The closest was `{"client": ...}`
without `inboundIds`, which the panel rejects with a message about a missing email — the
field was there, but the request was incomplete.

This one call both creates the client and attaches it, so the separate attach step is
skipped. The panel generates the UUID, so it is read back afterwards; using our own would
have broken later deletes and renewals.

`xui-trace.py` now prints the panel own definition for the route, which is what should
have been read first.

### Added
- **«تشخیص عمیق»** next to the connection test. It walks the whole path — login,
  inbounds, the routes the panel serves, the field names it declares, creating a real
  config, reading it back, cleaning up — and shows the panel'''s own error verbatim when
  a step fails. No SSH needed to find out why a config will not build

## [1.1.5]

### Fixed — The panel reads form data, not JSON
Every attempt was sent as JSON. 3x-ui reads form-urlencoded — which is why the legacy
addClient path always used data=. The panel never parsed the body at all, then reported
the email field as missing when it was right there.

Each body shape is now sent as form first and JSON second, with nested values serialised
for the form encoding. The style that works is remembered.

### Fixed — Config creation, for real this time
The trace against a live 3.7 panel read 183 routes and showed the create path is
`/panel/api/clients/add`, not `/panel/api/clients`. Every attempt was hitting a path
that does not exist, which the panel answered with a message about a missing email field
— misleading, since the body was fine.

Attaching to an inbound had the same problem: this version uses `bulkAttach`. Both are
now chosen from the panel's own route list rather than assumed, and a client that gets
created but not attached raises an error instead of leaving a config that exists
nowhere.

`xui-trace.py` now prints which create path it picked and, on failure, every body it
tried — so the panel's complaint can be read against what was actually sent.

### Fixed — Buttons across the whole panel looked wrong
Adding the form-font rule in 1.1.3 accidentally pulled three `body` properties into it,
so every button and input took the page background and lost the sizing from its own
class. `body` gets them back, and the font rule now carries nothing but the font.

`tools/check-api-contract.py` checks for both: that the form-font rule holds only a
font, and that `body` still has a background.

### Added — Server health monitoring
Eleven checks across every server, run automatically every five minutes, with a Telegram
alert when something changes:

- Disk, memory and swap, CPU load, uptime
- Critical services, including services that keep restarting — active but unstable is
  how a 3 AM outage usually starts
- Listening ports, taken from the enabled inbounds, so a port customers connect to that
  has nothing behind it is caught
- DNS resolution and speed
- **Dead IPv6** — an address configured but unroutable makes Xray hang on every AAAA
  record until timeout, which customers experience as sites not opening
- Clock sync, since TLS breaks on drift
- Kernel errors, with OOM kills named and the victim identified
- Certificate expiry

Every finding carries the command to fix it — knowing the disk is 92% full does not help
on its own.

Alerts fire only when the state changes, not on every cycle; an alert that arrives every
five minutes stops being read. Iranian nodes are checked through the agent, which fetches
the same module from the panel so both sides stay in step.

### Fixed
- **The new font never reached form elements.** Inputs, selects and buttons take their
  font from the browser rather than inheriting it, so they kept the system default while
  everything else showed IRANSansX. One rule fixes all of them
- **Reading a config back used the legacy path**, which fails on v3 where clients are
  standalone. It now asks the client endpoint first and falls back only if that route is
  absent

### Verified — Config creation end to end
Tested against a simulated 3x-ui v3 panel: reading inbounds, discovering routes, reading
the declared field names, creating a config, attaching it to an inbound, reading it back
with the right quota and group, and deleting it. Nine checks, all passing.

### Fixed — Period invoice showed zero
The default period ran from the first of the calendar month, so on the second of a month
everything created a few days earlier fell outside it and the invoice came back empty —
which read as "the rates are not applied". Without an explicit start date the period now
ends today and reaches back, so it always contains recent work.

### Added — Wallet top-up
The wallet could be spent but never filled. Choosing an amount now creates a top-up
order through the same card-transfer flow as a purchase; approving it credits the
balance instead of building a config.

### Added — Both tunnel ends deployed from the panel
A tunnel can now name a foreign node as well as an Iranian one. Both sides are queued on
apply, so a new tunnel needs no manual step on the foreign server. Leaving it as manual
still works for servers without an agent.

### Added
- `xui-trace.py` walks config creation end to end and prints what the panel was asked
  and what it answered — routes read, fields it declares, the create attempt, the
  read-back, and cleanup

### Added — Affiliate management in the panel
The endpoints existed but there was no page for them. Bot > همکاری در فروش now shows
every affiliate with customers brought, orders, sales, commission earned, paid and
outstanding — plus the total owed across all of them at the top.

Add an affiliate with a name and a percentage; the link code is generated unless you
choose one. Give a Telegram ID and they get their own panel inside the bot and a
message on every sale. Affiliates can be edited, deactivated without losing history, or
removed — removing keeps their customers, only the link is cut.

Recording a payout marks the oldest pending commissions as settled, so the outstanding
figure stays honest.

### Fixed — 'client email is required' on 3x-ui 3.7
The request reached the panel but was rejected: the body shape for creating a client
changed between 3.x releases, and the field the panel looks for was not where it
expected. The same discovery approach used for paths now applies to the body — the
client tries each known shape and keeps whichever the panel accepts, then caches it.

A 404 stops the attempts immediately and falls back to the legacy path, since trying
more shapes against a route that does not exist wastes time.

### Fixed — Config creation on 3x-ui v3
Version 3 changed the client model: clients are standalone records attached to inbounds,
not entries inside an inbound'''s JSON. The old `/panel/api/inbounds/addClient` path is
gone, which is why creation returned 404 and order approval silently stalled.

Rather than hardcode paths for each version, the client now reads the panel'''s own
OpenAPI specification from `/panel/api/openapi.json` and uses whatever routes it
actually has. On v3 it creates the client and attaches it to the inbound; on older
panels it falls back to the legacy path. Panels that serve no specification still work
through path probing.

The connection test reports how many routes were read and which architecture was found,
so a future version changing paths again shows up there rather than as a bare 404.

## [1.1.1]

### Added — Affiliate sales
For people who sell on your behalf rather than customers who refer friends. Separate
from the coin-based referral system: this pays a cash percentage, tracked as a debt you
settle outside the bot.

- Each affiliate gets their own link and their own percentage
- **Commission on every purchase that customer ever makes**, not just the first — the
  link is recorded on the user, so it keeps paying
- The affiliate sees their own panel in the bot: customers brought, orders placed, total
  sales, commission earned, paid and outstanding, plus a line-by-line list
- The panel shows what each affiliate is owed; recording a payout marks the oldest
  pending commissions as settled
- A commission is written once per order, so re-approving an order cannot pay twice
- Commission is recorded only after the config is successfully created, since nothing
  was sold until it was delivered

## [1.1.1]

### Added — Accounting filters on the client list
Three filters aimed at the questions that come up when preparing an invoice:

- **Created between two dates** — who was added in a given span, with one-tap shortcuts
  for the last 7 and 30 days
- **New versus older** — split at 30 days, so recent additions are separable from the
  standing base
- **No rate defined** — configs whose plan size is not in the group rate table. These
  bill as zero and are quietly lost revenue, so the count is shown even when the filter
  is off

The CSV export now carries whatever filters are on screen, rather than always dumping
everything and leaving you to filter again in Excel.

### Added — Custom date ranges
Alongside the automatic periods, any two dates can be entered directly to see who was
created and who renewed between them. Useful when a reseller agreement covers a span
that does not line up with the regular cycle. Shortcuts cover the last week, fortnight,
month and quarter.

### Added — Period-based invoicing
The panel used to report one number: total owed since the beginning. That is unusable
once you take payments regularly, because nothing says which months a payment covered.

A new page bills one period at a time:

- **New configs and renewals counted separately**, each priced at the group rate
- **Each reseller has their own period** — weekly, fortnightly, monthly, anchored to a
  start date you choose
- **A settlement date** marks everything before it as already paid, so old configs stop
  reappearing in every invoice
- Payments recorded inside the period are matched against it, leaving a balance that
  means something
- Navigate to earlier or later periods to check what was agreed at the time

Renewal dates are known exactly for renewals Nexora recorded. For older ones the date is
estimated from the create-to-expiry gap and marked as such — necessary for period
assignment, but never presented as fact.

## [1.1.1]

### Fixed
- **The tunnel form had no visible submit button.** The button sat inside the scrolling
  body, so on a long form it fell below the fold with nothing to scroll to. It now sits
  in the modal footer, which stays fixed while the body scrolls, and is disabled until
  the name, address and at least one port are filled in
- Port fields used `type=number`, which shows spinner arrows and makes typing awkward.
  They now accept digits directly

### Changed
- **Invoice table rows are taller and the text larger** — 8.4mm rows at 8pt instead of
  7.2mm at 6.6pt. The space reserved for the totals is only taken from the first page
  when every row fits there; otherwise rows run to the bottom and the totals move to the
  next page, which beats leaving a gap

## [1.1.1]

### Added — Tunnel quality monitoring
Three measurements taken together, because each says something different and only
comparing them tells you where a problem lies:

- **TCP latency** — opens a real connection and closes it, five times. More meaningful
  than ping, since many routes treat ICMP differently from actual traffic. Reports min,
  average, max, jitter and packet loss
- **ICMP ping** — for comparison against the TCP figure
- **HTTP response** — the whole path through to the service behind the tunnel

High ICMP and high TCP means the network route is slow. Good ICMP but high TCP means
the tunnel or destination is slow. Good TCP but high HTTP means the service is slow.

The last 100 samples per tunnel are kept, with a trend chart and a plain quality rating.

### Fixed
- **The bot settings page failed with `no such table: tenants`.** The setup check only
  looked for the database file, so a half-created database — one that exists but has no
  tables — was accepted and every query then failed. It now verifies the schema and
  rebuilds if it is incomplete
- Port fields used `type=number`, which shows spinner arrows and makes typing a value
  awkward. They now take digits directly

### Changed
- The tunnel form explains the three steps and which server each field refers to

## [1.1.1]

### Fixed
- **Nodes stayed offline even though the agent was checking in.** The tunnel module read
  its database path once at import time, but import order under uvicorn is not
  guaranteed — if the environment variable was not set at that moment, the wrong path
  stuck for the life of the process and every write went silently to another file. The
  path is now resolved on each connection

### Changed
- **The agent installer verifies each step and prints in English.** It confirms the
  panel is reachable before installing anything, checks the downloaded file is valid
  Python, performs one manual check-in, and only then installs the service. A failure at
  any step stops with the reason
- All shell and CLI output is now English; comments in the source stay Persian

## [1.1.1]

### Changed
- **Shell and CLI output is now English.** Persian renders as mangled boxes on most
  Linux terminals, so error messages from install and repair scripts were unreadable —
  which meant real failures went unnoticed. All 178 output lines across the scripts,
  tools and agent are now plain ASCII. Comments in the source stay Persian

### Added
- **«چرا آفلاین؟»** on any node the panel shows as offline. It reports whether the agent
  has ever checked in, when it last did, and gives the four commands to run on the
  Iranian server — status, live log, panel reachability and restart
- `rebuild.sh` rebuilds the panel from scratch when it comes up unstyled or shows
  `undefined` — usually a stale `dist`. It verifies the stylesheet before installing it
  and restores the previous build on failure

## [1.1.1]

### Added
- `rebuild.sh` rebuilds the panel from scratch when it comes up unstyled or shows
  `undefined` where data should be — usually a stale `dist` left behind by a build that
  did not finish. It clears the Vite cache, rebuilds, and refuses to install the result
  unless the stylesheet is a sensible size and contains the colour variables and
  component classes. The previous build is restored if anything fails

## [1.1.1]

### Fixed
- **Creating a config failed with HTTP 404 on 3x-ui 3.5.** The client called
  `/panel/api/inbounds/addClient`, which that version no longer serves. Rather than
  guessing the new path, the client now tries the known candidates in order, keeps
  whichever answers, and reuses it. If none work it reports every path it tried instead
  of a bare 404. This also unblocks order approval, which was silently stuck because
  provisioning failed
- **Receipt images never loaded in the panel.** An `<img>` tag cannot send the admin
  password header, so every request came back 401. The endpoint now also accepts the
  password as a query parameter

### Added
- **سفارش‌های من** in the bot — every order with its status, amount, coins spent, and
  the rejection reason when there is one. Previously the only way to ask was support

## [1.1.2]

### Added
- **Per-gigabyte pricing for resellers.** Where the deal is by traffic rather than by
  plan, switch the group to حجمی and set a rate per GB. The amount is calculated from
  actual usage, not the plan ceiling, and the panel shows the arithmetic as you type

### Fixed
- **`nexora update` accepted a broken build.** It only checked that `index.html`
  existed. If Tailwind failed to run, the build still succeeded with a nearly empty
  stylesheet and the panel came up unstyled. The stylesheet size is now verified, and
  the previous build is restored if it is too small
- The tunnel form asked for an address without making clear which server it belonged
  to. It now shows the traffic direction and states plainly that the address is the
  Iranian server, since the foreign server is the one that dials in

## [1.1.1]

### Added
- **Chisel** as a fifth tunnel engine. It carries traffic inside ordinary HTTP, which
  tends to keep working when other protocols get filtered — marked recommended
  alongside Backhaul. It takes command-line arguments rather than a config file, and
  ships a single gzipped binary rather than an archive, so the agent handles both cases

### Changed
- The port list in the tunnel form was a column of full-width fields for four-digit
  numbers. Ports are now compact chips laid out inline, with one-tap shortcuts for 443,
  8443, 2053, 2087 and 80

## [1.1.0]

### Changed
- **IRANSansX replaces Vazirmatn** in the panel. Two `@font-face` declarations and one
  changed line in `body` — nothing else in the stylesheet was touched

### Fixed
- Reverted the stylesheet to its original form. Earlier edits had rewritten sixteen
  utility classes and dropped five others (`fx-search`, `fx-side`, `fx-topbar`,
  `fx-badge`, `fx-card-hl`), which is what broke the layout
- Removed an nginx block containing `types { }`, which clears MIME mappings and made
  the server send stylesheets as `application/octet-stream`. Browsers refuse a
  stylesheet sent under the wrong type. `fix-nginx.sh` repairs servers that already
  have it

## [1.1.0]

### Fixed — The panel served CSS the browser refused to use
A `location /fonts/` block added to the nginx config contained `types { }`, which
clears every MIME mapping for that location. Worse, nginx applied the emptied mapping
more broadly than intended, so stylesheets went out as
`application/octet-stream` — and browsers will not apply a stylesheet sent under the
wrong type. The file itself was perfect, which is why every check on the file passed.

The block is removed, and `fix-nginx.sh` repairs servers that already received it: it
backs up the config, strips the block, verifies `nginx -t` before reloading, rolls back
if anything fails, and then fetches the CSS to confirm the type is right.

### Added
- `tools/test-serve.py` serves the built files over HTTP and makes the same requests a
  browser would — checking status, MIME type and size for the stylesheet, every font it
  references, and the bundle. File-level checks cannot catch a transport problem

## [1.1.0]

### Added — Tunnel management
A fourth workspace for connecting an Iranian server to your foreign one, so the panel
itself never has to live inside Iran.

**Four engines:** Backhaul (recommended), Rathole, GOST and FRP. Each config is
generated for both ends from a single form.

**Agent, not SSH.** The Iranian server runs a small agent that connects out to the
panel. It opens no ports and stores no password — just a token you can revoke per
server. The agent only understands a fixed set of commands, so even a compromised panel
cannot run arbitrary code on it. Installation is one curl command.

**What you get:** live CPU, memory and disk from each server; deploy, restart, stop and
log from the panel; the foreign-side config ready to copy; an event log of what
happened.

The agent depends only on the Python standard library — no pip install on a server that
may have restricted internet.

## [1.1.2]

### Fixed — The panel rendered without any styling
Editing `index.css` to add the font block had removed two things the whole interface
depends on: the `:root` block holding all sixteen colour variables, and sixteen utility
classes including `.fx-input`, `.fx-stepper` and `.fx-table`. Every `var(--...)`
resolved to nothing and inputs fell back to browser defaults.

`npm run build` succeeded both times, which is the whole problem — a nearly empty
stylesheet is still a valid stylesheet.

### Added
- `tools/test-render.cjs` runs the built CSS in a simulated browser and reads real
  computed styles: utility classes resolve to the right values, all sixteen colour
  variables have values, the font reaches `body`, and every `fx-`/`nx-` class used in
  the panel exists. Run it after every build

## [1.1.1]

### Fixed — The panel lost all styling
Adding the font block to the top of `index.css` overwrote the three `@tailwind`
directives that pull in every utility class. The build still succeeded and the CSS file
was still produced, just nearly empty — so the panel rendered as unstyled HTML with
default browser buttons.

`tools/check-api-contract.py` now verifies the Tailwind directives are present and that
the font is not only declared but actually applied to `html`/`body`. Both failures are
silent at build time, which is exactly why they need an explicit check.

## [1.1.0]

### Fixed — The font never applied
Three `@font-face` rules loaded IRANSansX correctly, but nothing ever set it as the
page font: the rule that put the stack on `html`/`body` had been lost. The browser fell
back silently, which is why clearing the cache changed nothing. The stack now sits on
`html`, `body` and `#root`, and form elements inherit it explicitly.

Nginx also gained a `/fonts/` block with correct MIME types and a revalidating cache,
so replacing a font file no longer leaves browsers holding the old one for months.

### Changed — Client list is far more readable
Rows are taller and carry more at a glance: plan volume, device limit, reset count and
Telegram link sit under the email; creation date shows the subscription length beneath
it; days remaining is a large figure that turns amber near expiry and red past it;
renewals are badged and marked when the count is estimated; usage shows the figure, a
coloured bar and the percentage together.

## [1.0.9]

### Added — Every client in one view
A new page under Accounting listing every config on the server, including those in no
group at all. Built to answer questions about a single customer without opening 3x-ui:

- Who renewed and who did not, how many times, and whether that count is certain or
  estimated from the create-to-expiry gap
- Days remaining, with expiring and expired rows coloured
- Traffic used against quota, with a usage bar
- Created and expiry dates in Jalali, subscription length, device limit, reset count,
  Telegram ID, subscription ID and any note left on the config
- Amount owed per client where the group has rates

Filter by group, status or renewal state; search across email, group and notes; sort by
any column. Status counts double as filter buttons. Row click opens full detail.

Also exports to CSV with a BOM so Excel reads Persian correctly.

## [1.0.9]

### Fixed
- **The font declarations were ordered so browsers could skip IRANSansX entirely.**
  The variable font was declared first under the same family name; if a browser
  didn'''t support `woff2-variations` it had nothing to fall back to. Static weights
  now come first under the primary name, with the variable font as a separate family
- **The invoice table left a large gap at the bottom of each page.** Row capacity was
  computed from the first page, which is shorter because of the summary cards, so later
  pages stopped early. Each page now uses its own height, and the space the totals need
  is reserved so they never spill onto a page of their own

## [1.0.8]

### Changed
- **IRANSansX is now the panel and invoice font**, bundled locally rather than fetched
  from Google. The variable web font covers every weight in one file, and the TTFs
  carry the joined Arabic glyphs the PDF needs
- **The PDF invoice was rebuilt on a light, print-ready layout** — navy header rule,
  summary cards with the payable amount set apart, a bordered table with alternating
  rows, highlighted renewal cells, per-group and grand totals, then a closing page for
  the calculation method and rows needing review

### Fixed
- **Rollback did nothing when triggered from the panel.** The service runs with a
  minimal PATH that may not include /usr/local/bin, so calling `nexora` by name failed
  silently. The full path is resolved first, the process is detached properly, and PATH
  is now set in the unit file
- The rollback card sat flush against the card above it

## [1.0.7]

### Added — Full PDF invoices
The invoice now carries everything a reseller might question, so the numbers can be
defended line by line:

- Jalali and Gregorian dates for creation and expiry, converted at Tehran time
- Subscription length in days, months billed, and renewals per config
- Plan volume, real traffic used, and usage percentage
- Device limit per config
- Per-page subtotals and a grand total
- A closing page explaining how months are derived, plus every row that needs a human
  look — estimated durations, configs with no expiry, volumes with no rate

Estimated durations are marked in amber in the table rather than presented as fact.

### Fixed
- Restored the connection diagnosis endpoint, which was removed while rewriting the
  PDF generator. `tools/check-api-contract.py` caught it

## [1.0.6]

### Fixed — The reseller toggle switched itself back off
Saving a group sent `billed`, but the endpoint read `billable`, so the flag was always
stored as off. The rate saved fine; the switch did not. Recording a payment had the
same problem with `group` and `date` against `group_key` and `paid_at`.

Both endpoints now accept either spelling, and the save response echoes the stored
value so the interface can confirm rather than assume.

### Added
- `tools/check-api-contract.py` — walks every URL the panel calls and checks it has a
  matching route, then checks the field names both sides use. This class of mismatch
  fails silently: no error, no log, just a blank page or a button that does nothing

## [1.0.5]

### Fixed — The accounting page called endpoints that did not exist
The panel requested `/api/admin/billing/groups` and `/api/admin/billing/payment`, but
the backend only defined `/overview` and `/payments`. Both returned 404, and since a
404 body carries no `error` field, the page fell back to its generic message about the
database path — pointing at the one thing that was never wrong.

Every diagnostic passed because they used the endpoints that did exist. The request the
page actually made was never tested. Both spellings now resolve, and a check across all
frontend URLs confirms each one has a matching route.

## [1.0.4]

### Fixed — Accounting read the data but showed nothing
The panel was reading the 3x-ui database correctly all along — 202 configs, 9 groups,
every diagnostic green — but the page stayed empty. The two sides used different field
names for the same values, so every lookup came back `undefined` and rendered as blank
rather than raising an error: `key` vs `name`, `billable` vs `billed`, `due` vs
`amount`, `estimated` vs `uncertain`, `lines` vs `items`, `group_key` vs `group_name`.

The backend now sends both names for each value. A mismatch like this fails silently,
which is why four rounds of checking paths, permissions and WAL files found nothing.

### Fixed
- The system page showed the rollback card twice — once interactive, once as a static
  command reference

### Added
- **`billing-trace.py`** — runs the exact code path the panel uses and prints the full
  traceback instead of swallowing it. When accounting fails, this says which line broke
  rather than leaving you to guess

## [1.0.3]

### Fixed — Accounting couldn't reach the 3x-ui database
Three separate problems stacked on top of each other, each hiding the next.

- **The error screen showed a fixed message rather than the real cause.** The backend
  had been reporting the actual problem, but a generic paragraph about `XUI_DB_PATH`
  sat underneath it — and that's what people read. The path itself was pulled from the
  wrong field, so it never appeared at all
- **A manually set path won even when it pointed at nothing.** One typo, or an
  invisible character carried in by copy-paste, disabled accounting for good. The path
  is now checked before use and the other sources are tried as a fallback
- **WAL side files were not accounted for.** When 3x-ui runs in WAL mode, SQLite also
  needs `-wal` and `-shm`; without them it refuses to open the database and blames the
  main file. Nexora now names the exact file that needs fixing
- An earlier fallback used `immutable=1`, which opens a WAL database but hides
  everything written since the last checkpoint — tables looked empty rather than
  erroring. That path is now only taken when no `-wal` file exists

- **Accounting failed with an empty error while diagnosis passed.** The diagnosis and
  the main page read different things: diagnosis only touches the 3x-ui database, while
  the overview also opens Nexora's own billing database. A corrupt billing file made the
  overview return a 500, and the panel — receiving no error field — fell back to a
  message about the 3x-ui path, sending everyone looking in the wrong place. The
  overview now always returns a readable error, and a corrupt billing file is set aside
  and rebuilt rather than taking the whole section down

### Added
- **Connection diagnosis inside the panel.** A button on the error screen walks every
  step — where the path came from, whether the file exists, permissions on all three
  files, which user the panel runs as, opening the database, reading the schema, and
  listing the groups — and shows which step failed along with the command to fix it
- `nexora fix-xui` finds the database, repairs permissions on the side files too, and
  writes the path to both the service and the panel settings
- `billing-doctor.sh` for diagnosing from the shell

### Changed
- `systemctl status nexora` works now; the service is `nexora-panel` and an alias is
  created at install
- Panel font stack falls back through Segoe UI and Noto Sans Arabic, with tabular
  figures so numbers don't jump
- The label inside the usage ring takes the brand colour, and section headings gained
  a coloured marker, so a gold palette no longer leaves grey text beside a gold ring
- Snapshot cards and warning boxes had no breathing room

## [1.0.2]

### Fixed
- **The 3x-ui connection error was always the same generic message.** Every failure
  was swallowed and reported identically, so a permission problem looked the same as
  a missing file. It now reports the actual cause — missing folder, missing file,
  no read permission (with the `chmod` command), a locked database, or a file that
  isn't SQLite at all
- Opening the database now runs a real query, because SQLite accepts a corrupt file
  silently until you touch a table
- Warning boxes sat flush against the buttons above them

### Added
- **PDF invoices** — a landscape summary page plus a full per-config breakdown:
  volume, usage, months, renewals, rate and amount for every client, with a running
  total per page. Persian text is shaped and laid out right-to-left, and the font is
  chosen by testing that it actually contains the joined glyphs rather than trusting
  its name

### Changed
- The label inside the usage ring took the brand colour instead of a flat grey, and
  section headings gained a coloured marker, so a gold palette no longer leaves grey
  text sitting next to a gold ring
- Panel font stack falls back through Segoe UI and Noto Sans Arabic if Vazirmatn
  fails to load, with tabular figures so numbers don't jump

## [1.0.1]

### Fixed
- **`systemctl status nexora` didn't work** — the service is called `nexora-panel`.
  An alias is now created at install, and `nexora doctor` adds it to existing setups
- **Accounting couldn't find the 3x-ui database.** The path came only from an
  environment variable, so installs that predate it had no way to fix it. The path is
  now settable from the panel, falls back to the environment variable, and finally
  probes the common install locations
- **The usage ring ignored the palette.** Its colours were hard-coded teal, amber and
  red, so a gold palette still drew a teal ring. It now uses the brand colour, and only
  switches to a warning colour when the quota is nearly gone

### Added
- **Accounting settings page** — see where the 3x-ui database is, pick from paths found
  on the server, or set one manually
- **Backup and restore for accounting** — rates, payments and the renewal log. A safety
  copy is taken before any restore

## [1.0.0] — First release

### Subscription page
- 4 structures × 8 palettes, plus custom palettes
- One-tap install for Happ, v2rayNG and V2Box; QR codes; copy link
- Usage ring that sweeps from zero on load, with the figure counting up
- Depth built from shadows and gradients — no images, works with every palette
- Text colour on branded surfaces is computed from real contrast, so every
  palette stays readable
- FAQ in Persian, English, Turkish and Arabic
- Tutorial videos hosted on your Telegram channel

### Telegram sales bot
- Plans, card-transfer payment, photo and text receipts
- One-tap approval with automatic provisioning in 3x-ui
- Rejection with a reason, and spent coins are refunded
- Coin and referral system with a discount ladder
- Wallet, renewal, auto-renew, free trial
- Optional phone collection, expiry reminders, support tickets
- Admin panel inside the bot, plus an admin group with topics

### Accounting for resellers
- Groups read straight from `x-ui.db`, read-only, with real usage
- Per-group rate tables: any volume you type, or unlimited
- Payments logged in Nexora, since 3x-ui doesn't record them
- Invoices with a per-config breakdown
- Renewal log — past months are estimated and labelled honestly; from now on
  every renewal made through Nexora is recorded

### Panel
- Three workspace layouts to choose from: accordion, dropdown, icon rail
- Step-by-step 3x-ui connection test that provisions and removes a probe config
- GitHub repository configurable from the panel, verified before saving
- Bot control, backup and restore
- Snapshots, rollback, self-healing update
- `nexora doctor` checks the bot module, billing data and 3x-ui read access
