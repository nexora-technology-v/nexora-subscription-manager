# Changelog

## [Unreleased]

_کارهای انجام‌شده که هنوز ریلیز نشده‌اند._

### Changed — Every monitoring refresh cost a second of waiting and an apt run

Both `cpu()` and `network()` measure rates, so each read its counter twice with a
`SAMPLE` wait between. They each took their own wait: 1.2 seconds of pure
sleeping per snapshot, for two numbers that can come from the same window.
`snapshot` now samples once and hands each of them its pair. Called on their own
they still sample themselves, since the agent may use them individually.

`packages()` runs `apt-get -s upgrade` with a 25-second timeout, and it ran on
every refresh. The list of upgradable packages does not change minute to minute;
it is cached for an hour now.

`security()` greps 24 hours of SSH journal on every refresh — the same scan the
intrusion page does. Only that scan is cached, for five minutes.

Caching the whole `security` section was the obvious move and it was wrong: the
existing tests caught that it also froze the firewall and fail2ban status. An
admin who has just switched the firewall on should not be told it is off for the
next five minutes. Same for `xray`, which is left uncached so a stopped service
shows immediately.

### Fixed — The intrusion page said "last 24 hours" and showed weeks

`_auth_lines` asks journald for the window with `--since`, then falls back to
`tail -n 20000 /var/log/auth.log`. `tail` limits how many lines, not how old they
are — so on the fallback path the page counted attempts from as far back as the
file went, while the response still reported `hours: 24`.

An address that hammered the server a month ago appeared as a current attacker,
and every count was inflated.

The fallback also triggered more often than it looks. The check was `if
out.strip()`, so a journald query that ran fine but found nothing — a quiet day —
was treated the same as journald being unavailable, and fell through to the
unbounded file. Success with no output now returns nothing, which is what it
means.

Lines from the file are filtered by timestamp, in both the syslog and ISO
formats, with the year inferred and rolled back when that would put the line in
the future. A line whose timestamp cannot be read is kept: dropping it would be
silent data loss, which is the thing being fixed.

## [1.10.10]

### Fixed — The rollback endpoint built a shell command from its input

`/api/admin/rollback` took the snapshot id from the request body and interpolated
it into a shell string:

    cmd = f"setsid {cli} rollback {snap} --yes --settings={keep}"
    subprocess.Popen(["bash", "-lc", cmd])

Its validation rejected `/` and `..` — a denylist again, which passes anything
nobody thought of, shell metacharacters included. A directory whose name carried
`;` or a backtick would have been accepted and interpreted.

Reaching it requires the admin password, so this is not an open door. But it
turns knowing that password into running arbitrary commands as root, rather than
just using the panel, and it is avoidable in two lines.

The id must now match `\d{8}-\d{6}`, which is the only shape
`date +%Y%m%d-%H%M%S` produces — an allowlist, so an unexpected name is rejected
rather than passed along. And the command runs as an argument list with no shell
at all, so nothing in it can be interpreted. `start_new_session` does what
`setsid` did: closing the panel mid-rollback does not kill it.

### Fixed — A missing log file no longer blocks a rollback

Writing output to the log is now best-effort. The log exists to be watched; the
rollback is the part that has to happen. Its path is also configurable, which is
what let the test exercise this at all.

## [1.10.9]

### Fixed — An expense could be recorded at last week's exchange rate

When tgju cannot be reached, `live()` falls back to the last successful rate and
marks it `stale`. For displaying a number that is reasonable. For recording an
expense it is not — the whole reason the toman amount is stored on the row is to
preserve the rate *at the time of purchase*.

The cache never expired, so if the rate site stayed down the fallback kept
returning the same figure indefinitely. And the expense endpoint never looked at
`stale` at all: the row went in with `fx_source: tgju` and nothing to say the
rate was hours or days old.

Two changes. Past a day old, a cached rate is no longer returned as usable — the
number is still there for display, but `ok` is cleared so nothing calculates with
it, and the hint says to enter the rate by hand. Below that, the expense is still
accepted — the site may be down for a few minutes and the work should not stop —
but the response carries the rate's age, and the panel shows it as a warning that
stays on screen instead of disappearing after four seconds.

The age now travels from `live` through `to_toman` to the endpoint, so the
warning can say how old: "the exchange rate from 3 hours ago was used".

A manual rate still wins over everything and is never marked stale.

## [1.10.8]

Agent 1.5.2.

### Fixed — A half-finished download stayed cached until the panel changed version

The agent fetches `monitor.py` and `firewall.py` from the panel and caches them
next to itself, re-fetching only when the panel's version changes. `download`
wrote straight to the destination file, so a connection that dropped mid-copy
left a truncated Python file in place.

From then on the file existed and the version matched, so it was never fetched
again. Every monitoring job on that node failed with a `SyntaxError` until the
panel happened to be updated.

Downloads are atomic now — written to a temporary file and moved into place — so
a failed transfer leaves the previous working copy untouched and no partial file
behind.

### Fixed — A cached module that will not load is now thrown away

The same stuck state could arrive any other way: a truncated file from an older
version, a disk problem, a bad write. Whatever the cause, the agent kept loading
the same broken file and reporting the same error.

If a cached module fails to load, it is deleted along with its version stamp and
fetched once more. A module that loads fine is still not re-downloaded — a fetch
on every check-in would be pointless traffic.

### Added — The agent's module cache is tested

`tools/test-agent.py` now drives `remote_module` directly: a healthy fetch, a
transfer that dies mid-copy, a syntactically broken cached file, and the two
cases that must *not* re-download. The real `download` is tested separately
against a stream that fails halfway, checking that the previous file survives and
no `.part` file is left.

Confirmed against the previous agent, where four of these fail.

## [1.10.7]

### Fixed — Rolling back could destroy the bot database

`nexora-cli` takes a snapshot in two places: before an update, and before a
rollback. Each had its own hand-written list of what to copy, and the rollback
one was missing eight items — `VERSION`, `.github`, `nexora-cli.sh`, the whole
`bot/` directory, `frontend/.env`, and all three databases.

The comment above it says the current state is saved "so rollback itself is
reversible". It was not.

The damage: rolling back asks whether to restore settings from the snapshot. Say
yes, and it copies that snapshot's `bot.db` over the live one — while the live
one was never saved anywhere. Every user, order, subscription and wallet balance
created since the last update is gone, with no copy to recover from and nothing
on screen to suggest anything was lost.

Rolling back also could not be undone for the bot: its code was not in the
snapshot either, so the bot stayed on the rolled-back version permanently.

Both call sites now use one `snapshot_to` function. Two lists cannot drift when
there is only one.

### Fixed — A flaky test of my own, and the reason it stayed hidden

`bot/test_xui.py` failed about one run in ten, but only on Windows. It blocked
the release gate twice today while passing every CI run on Linux.

The cause was the expired-session branch I added to the fake panel in 1.10.5. It
answered with a login page without first reading the request body. The server
then closed a socket with unread bytes still buffered, the OS sent RST, and the
client saw `ConnectionAborted`. Every other POST path in that handler drains the
body; that one did not. One line.

It stayed hidden because the gate printed `p.stdout or p.stderr` — and stdout was
never empty, so the traceback was never shown. All it displayed was output that
stopped mid-section. The gate prints stderr first now, and eight lines instead of
four.

Verified over 30 consecutive runs with no failures, against a measured 2–4 in 20
before.

### Added — `tools/test-snapshot.py`

Runs the function for real against a fake install tree rather than reading the
script. 13 checks: that both paths call the shared function, that all seventeen
files land in the snapshot, that `bot.db` arrives with its contents intact, that
`venv` and `__pycache__` stay out, and that a partial install — no bot, no
databases — neither errors nor creates empty placeholder files, since a zero-byte
`bot.db` restored later would wipe the database just as thoroughly.

## [1.10.6]

### Fixed — The intrusion page went black (React #310)

My own regression, introduced with the pagination work in 1.9.7.

`usePager` was called *after* the component's `if (!d) return <spinner/>` guard.
On the first render, before the data arrives, that guard returns early and the
hook never runs. On the next render the data exists, the guard is skipped, and
the hook runs — so React sees more hooks than the render before and tears the
whole tree down. Not a broken section: a black page.

All the derived values and the hook moved above the guard, which is where hooks
have to be.

### Added — `tools/test-hooks.cjs`

The component render test did not catch this, and could not: it mounts each
component once with data, so the empty-to-loaded transition that triggers the
error never happens.

This one reads the source instead. For every component it finds the early-return
guards and flags any hook called after one. No browser needed.

It was written wrong the first time — the pattern stopped at `=`, so it missed
`const { shown, pager } = usePager(...)`, which is exactly the line that caused
the bug. Verified now by running it against the broken file and watching it fail
with the file, line, component and code, then against the fix and watching it
pass.

## [1.10.5]

### Fixed — When the panel session expired, renewals silently did nothing

3x-ui redirects to its login page when a session expires. `requests` follows the
redirect, so the response arrives as HTTP 200 with an HTML body — not a 401.

`_req` treated any non-JSON body with a 2xx status as "succeeded, no content" and
returned `None`. That rule exists for endpoints like delete, which legitimately
answer with an empty body. But the login page is not empty, and it was being
counted as success.

So `update_client` returned normally, `extend_subscription` reported the new
expiry date, and the panel had changed nothing. The customer was told their
subscription was renewed. It was not. Blocking a client failed the same way.

The bot holds one panel connection for as long as it runs, so this is not a rare
state — it is what happens every time the session ages out.

Empty body with 2xx still means success. A non-empty body that is not JSON now
triggers one re-login and a retry; if it happens again, it raises with the reason
rather than pretending.

### Added — Session expiry is covered by the simulated panel

`bot/test_xui.py` can now make the fake panel answer with a login page, once or
every time. 30 checks, including that a single expiry heals itself and completes
the renewal, that a persistent one raises instead of reporting success, that the
expiry date is left untouched when it raises, and that it never tries logging in
more than once.

## [1.10.4]

### Fixed — The SSL certificate check never ran on any server

`check_cert` returns immediately unless it is given a domain. The domain came
from `advanced.panelDomain` — a config key that no UI writes, no installer step
sets, and no default provides. It is read in two places and written in none.

So the check existed, was written correctly, and never executed. Nobody was ever
warned that a certificate was about to expire. When it does expire, the panel and
the subscription page stop answering for every customer at once, with no prior
signal.

It finds the certificate itself now. certbot names each directory after its
domain, so `/etc/letsencrypt/live/<domain>/fullchain.pem` supplies both the file
and the name — nothing to configure. With several certificates, the one expiring
soonest is reported.

### Fixed — The expiry date was parsed in a locale-dependent way

`strptime` with `%b` matches month names in the system locale. OpenSSL always
prints English ones, so on a server whose `LC_TIME` is not English the parse
raised, the function returned `None`, and the check disappeared without a word.
Parsed with an explicit month table and compared in UTC now.

### Changed — A certificate that cannot be read is a warning, not silence

Any failure used to return `None`, which removes the row from the health list
entirely. No certificate at all still returns `None` — an HTTP-only server should
not be nagged. But when a certificate file is present and its date cannot be
read, that is now a warning with the command to run: not knowing when your
certificate expires is itself worth saying.

### Added — `tools/test-health.py`

The health checks had no test, and one of them had already shipped broken
(`check_time` in 1.9.7). 18 checks covering certificate discovery, the expiry
thresholds, OpenSSL's two-space day format, the unreadable-certificate case,
picking the soonest of several, and the timedatectl parsing that was wrong before.

## [1.10.3]

### Fixed — The public config endpoint leaked keys nobody added to the filter

`/api/public/config` is served without authentication — every customer's browser
fetches it each time the subscription page opens.

Its filter was a denylist: strip `resellers` and `bot`, publish everything else.
So any key added to the config later became public automatically, because nobody
remembered to add it to the list. `maintenance` went out that way: the server's
scheduled reboot time, the busy threshold, and the text of its last error.

That is the wrong shape for a filter that guards secrets. Forgetting a key in a
denylist leaks it; forgetting one in an allowlist only hides a feature. The
direction you fail in should be the safe one.

It is an allowlist now — the twelve keys the subscription page actually reads.
A future config key stays private until someone adds it deliberately.

Reseller `overrides` were merged *after* the filter, so an override could put a
stripped key back. The merge result goes through the same filter now. These are
written by the admin rather than an attacker, but a filter with a hole in it is
not a filter.

### Added — `tools/test-public-config.py`

23 checks. Among them: a config carrying a bot token, a reseller list, the
maintenance schedule and an invented `smsGateway.apiKey`, asserting none of it
reaches the response — including a plain string search of the whole payload for
the secret values.

## [1.10.2]

### Fixed — Backups were missing four tables, including every affiliate record

The list of tables to back up was written by hand. Each time a feature added a
table, that list was not updated, and nothing ever complained. The backup
downloaded with "ok" and simply did not contain them.

Missing from the bot backup:

    affiliates              the partners themselves
    affiliate_commissions   what they earned
    affiliate_payouts       what has been paid out
    events                  the history log

Missing from the accounting backup: `expenses` — the whole expenses section —
and `client_seen`, which accounting uses as the floor for "how long have we known
this config".

Worse than missing: restoring a bot backup ran `DELETE FROM` on its own table
list, then re-inserted from the file. Affiliate data was not on that list, so it
was left alone on the same machine — but restoring onto a fresh server produced a
panel with no affiliates, no commission history, and no payout records. Money
owed to real people, with nothing to reconstruct it from.

Table lists are read from the schema now. A table cannot be forgotten because
nobody has to remember it.

### Fixed — A half-finished restore reported success

Every row that failed to insert was swallowed by a bare `except: pass`, and the
response was `{"ok": true}` regardless. A restore that dropped half the users
looked exactly like one that worked.

Skipped rows are counted per table and returned, and the panel shows that as an
error rather than a success.

### Fixed — Restoring an older backup wiped tables it did not contain

Accounting restore deleted `group_config`, `payments` and `renewals`
unconditionally, whether or not the file had them. A backup taken before the
expenses feature would now also have cleared expenses. Only tables actually
present in the file are touched.

### Added — `tools/test-backup.py`

Backup and restore had no test at all. 24 checks: a full round trip through every
table, the partial-restore warning, and an old backup restored onto a newer
schema.

## [1.10.1]

Three of the five tunnel engines generated configs that could not carry traffic.
Backhaul and Chisel — the two marked recommended, and the two actually in use —
were correct.

The rule, stated in Backhaul's own docstring: `local` is the port opened on the
Iran server that customers connect to, `remote` is the real service port on the
foreign server. "Mixing these up means the tunnel comes up and no traffic
passes."

None of this was visible from the panel, because the port editor writes one value
into both fields. It surfaces the moment anyone maps 8080 to 80, or calls the API
directly — `validate_ports` has always accepted `{local, remote}` pairs.

### Fixed — Rathole had both sides inverted

The Iran server opened the *foreign* service port and waited for customers there.
The foreign server connected to the *Iran* port, which does not exist on that
machine. Service names were also derived from `remote`; they come from `local` now
so both ends agree.

### Fixed — FRP had localPort and remotePort swapped

In frpc, `localPort` is the service on the machine frpc runs on — the foreign
server — and `remotePort` is what frps publishes on the Iran side. They were the
other way round.

### Fixed — GOST opened no port for customers at all

The foreign side used `handler: tcp` with a chain: a *forward* proxy, opening the
port on the foreign server itself, with no destination to send traffic to. The
Iran config only accepted the relay and never listened for customers, despite its
docstring claiming it did.

Rewritten to use `rtcp`, which is how GOST does reverse forwarding: the foreign
side asks the relay to open the customer port on Iran and forwards arriving
connections to its own service.

### Added — Engine configs are tested

`build_config` had no test. There is one per engine now, asserting the exact
output that carries the port mapping, plus a parse check — TOML for Backhaul,
Rathole and FRP, YAML for GOST — because a malformed config fails on the remote
server where only journalctl would show it.

## [1.10.0]

### Fixed — A job the agent took but never answered was stuck forever

When the agent picks up a job its status becomes `taken`. There was no way out
of that state. If the agent restarted mid-job, lost the network, or was killed,
the job stayed `taken` permanently.

The panel detected this — both `nexora check` and the node diagnose page said
"the agent picked it up and never reported back" — and then did nothing about it.
The admin pressed the button, nothing happened, and the only recourse was to
press it again and hope.

Jobs taken more than five minutes ago are requeued on the agent's next check-in.
Every allowed action is idempotent (`apply`, `restart`, `sysmon`, `update_agent`
and the rest), so retrying is safe. After three attempts the job is marked failed
with the reason and the journalctl command to look at, so one broken job cannot
fill the queue forever.

Five minutes is deliberately longer than the slowest job: `sysmon` on a loaded
server takes a minute or two, and requeueing sooner would run two copies at once.

### Changed — Ports dropped from a tunnel say so

`validate_ports` discarded invalid rows with a bare `continue`. An admin entering
three ports got a tunnel with two, and nothing anywhere said where the third
went. When that port later did not work there was no trail to follow.

Dropped ports are now recorded as a warning event on the tunnel, with the reason
— out of range, not a number, or port 22, which is refused so nobody locks
themselves out by accident. When *every* port is rejected, the error says which
ones and why instead of "at least one valid port is required".

### Added — `tools/test-jobs.py`

The job queue had no functional test; `test-nodes.py` checks the source text
rather than running anything. 28 checks covering the normal lifecycle, recovery,
the attempt ceiling, node isolation, and port validation.

## [1.9.9]

### Fixed — A config on an exact half-month boundary billed unpredictably

The new text-vs-numeric test from 1.9.8 failed on Python 3.10 and passed on 3.12,
which turned out not to be a version difference at all. Month counts came from
`round(days / 30)`, and Python's `round` is banker's rounding:

    round(9.5)  == 10
    round(10.5) == 10      <- this one
    round(11.5) == 12

Half goes to the nearest *even* number. So two configs each sitting exactly half
a month over billed differently depending on whether their month count was odd or
even. 285 days is exactly 9.5 months, and one second either side of it flipped
the answer by a whole month.

`_months_from_days` rounds half up, with a tolerance so sub-second differences in
a creation date cannot change the result. The only bills that change are the ones
that landed exactly on a boundary with an even month count — those now round up,
like the odd ones always did.

### Fixed — The 1.9.8 test compared two different instants

It stored the text timestamp truncated to seconds and the numeric one with
milliseconds, so the two sides were up to a second apart. Both are built from the
same whole second now, which is what makes the comparison meaningful.

## [1.9.8]

### Fixed — Subscription length was blank for every client

`_duration_days` was the third function carrying the assumption fixed in 1.9.7:
`float(created)` raises `ValueError` on a text date, so it returned `None` for
every client whose `created_at` is stored as text. The length column in the group
invoice and in the clients list was empty as a result.

It goes through `_epoch_ms` now, like the rest.

### Added — The numbers no longer depend on how x-ui stores dates

The 1.9.7 bugs all had one shape: code that assumed `created_at` was a number.
The tests never caught them because the fixture left `created_at` as `NULL`,
which takes a different branch entirely.

There is now a test that builds the same five clients twice — once with text
timestamps, once with numeric — and asserts that config count, months, group
balance, invoice line counts, renewal count, invoice total, and period start all
come out identical. With the old code the text side reported zero renewals while
the numeric side reported 49, so this fails loudly on any regression of the same
kind.

### Added — `nexora check` reports how x-ui stores `created_at`

One line in the accounting section, giving the SQLite type and a sample value.
Which storage format a server uses decides which code path the accounting takes,
and there was no way to see it without opening the database by hand.

## [1.9.7]

### Fixed — Every invoice was roughly ten times too small

`_to_jalali` accepted epoch milliseconds only. x-ui stores `created_at` as text
in most versions, and the period invoice passed that value straight through, so
on those installs the page raised `TypeError`.

`_renewal_dates` had the same assumption in a quieter form: `float(created)`
raised `ValueError` on a text date and the function returned an empty list. No
exception surfaced — the invoice simply showed **zero renewals**. A config
created two years ago and renewed every month since counted as one sale.

On the sample data in the tests, the same 30-day invoice goes from 150,000 to
1,500,000 once renewals are counted.

All timestamp parsing now goes through one `_epoch_ms` helper that accepts
seconds, milliseconds, and text, so the numbers no longer depend on which x-ui
version wrote the row.

### Added — An invoice that covers everything, not just this month

The period invoice defaults to the last 30 days. For a reseller two years into a
relationship that shows only configs created this month — the complaint that
accounting "doesn't count anything from before, only the new ones".

There is an "از ابتدا تا امروز" button now. It starts from the creation date of
the group's oldest config, or from `settled_until` when a settlement is
recorded, so settled work does not reappear.

### Fixed — `strftime("%s")` is a glibc extension

Used to convert a renewal date to epoch. It raises `ValueError` outside glibc.
It never ran before because the renewal list was always empty, so no test caught
it. Replaced with `_date_ms`, which is explicit about UTC.

### Fixed — The subscription name was the panel's, not the customer's

`sub_label` appended the inbound's name *instead of* the config number when the
inbound had one. Every config on a shared inbound got an identical label:

    یک‌ماهه · پنل جدید
    یک‌ماهه · پنل جدید

So the renew screen could not say which subscription it was renewing, and the
name shown belonged to the panel rather than to anything the customer bought.
The config number comes first now; the inbound name is added only when there is
more than one inbound, where it actually distinguishes something.

### Fixed — Time sync always reported "not synchronized"

`timedatectl show -p NTPSynchronized,Timezone --value` prints properties in
systemd's own order, which puts Timezone first. The first line was read as the
sync flag, so it was never "yes". Running the suggested command changed nothing
because there was nothing wrong. Parsed as `KEY=value` pairs now, and the check
is skipped entirely when systemd does not report the property.

### Fixed — "Database not readable" flashed on every visit

The period section rendered its error card while `data` was still `null` from
the first fetch. It waits for the load now, like the users section already did.

### Changed — Numbered pagination where the lists were long

Firewall suggestions, blackholed addresses, firewall rules, the intrusion table,
and the active-connections list all rendered in full. "Show more" made the page
longer, which was the problem. They paginate now.

### Fixed — IPv6 addresses overflowed the connections card

The address column was a fixed 130px. An IPv6 address is about three times an
IPv4 one and ran outside the card.

### Changed — Custom billing range uses the Jalali picker

It was two text inputs with Gregorian placeholders, typed by hand.

## [1.9.6]

### Fixed — Coins spent on an unpaid order were lost for good

Coins are reserved when the order is created. `spend_coins` documents the
contract: they come back on rejection, expiry, or cancellation. Three paths
honoured it — the cancel button, opening a lapsed order, and admin rejection.

The automatic sweeper did not. It ran a bare UPDATE:

    UPDATE orders SET status='expired' WHERE ...

and left the reservation open. That sweeper runs every two minutes, so it
reaches a lapsed order long before the customer touches it — which made it the
path that actually handles expiry almost every time. The three correct paths were
effectively unreachable.

So a customer who applied coins to an order and then did not pay in time lost
those coins permanently. Silently, with no error, having received nothing.

The release logic moved to `TenantDB.release_coins` because the sweeper holds no
bot and cannot build a `Ctx` — which is why the logic was out of its reach in the
first place. `handlers._release_coins` now delegates to it, so there is one
implementation. The customer also gets a message saying the deadline passed and
their coins are back; otherwise the balance changes with no explanation.

Orders that are already approved are untouched, as before: that sale happened.

## [1.9.5]

Everything here came out of one `nexora check` run on the production server.

### Fixed — The doctor hid every TCP port

`nexora check` capped the port list at 40 lines. `ss` prints UDP before TCP, and
xray keeps about 40 ephemeral UDP sockets open for its own outbound traffic — so
the cap was reached before a single TCP port was printed. SSH, nginx, the panel
and every tunnel listener were missing from the report, which is exactly the list
you run the report to see.

TCP is printed first now, in full, and the ephemeral xray sockets are collapsed
into one line.

### Fixed — 40 phantom xray ports in the firewall

Those same ephemeral sockets reached the firewall page. The process is named
`xray-linux-amd6`, which matches the known-service list, so all 40 were filed
under "must stay open". Applying the plan would have written 40 permanent ufw
rules for ports that get new random numbers the next time xray restarts.

They are now recognised by checking the port against x-ui's own `inbounds`
table — the only authoritative source for which ports xray actually serves. A
real inbound on a high UDP port (Hysteria, for example) is kept; an ephemeral
socket is dropped and counted. If x-ui's database cannot be read, nothing is
filtered: a wrong guess here closes a customer-facing port.

### Fixed — Agent updates were rejected as "outside the panel"

Three `update_agent` jobs in a row failed with "the update address is not
allowed". The agent refuses any URL that does not start with its own
`PANEL_URL`, which is correct — it should not fetch its own executable from an
arbitrary host.

The mistake was on the panel side: it guessed its external address from nginx
headers and sent a domain, while the agent had been installed pointing at an
address of its own. The panel does not know that value and cannot know it.

The panel now sends no URL at all. The agent builds one from the address it
already check-ins with every minute, so the guard passes and stays intact. This
takes effect on the running 1.5.0 agent without reinstalling it.

### Changed — The doctor names the group missing a start date

With eleven groups, "1 billable group has no start date" meant opening all
eleven to find it. It prints the name now.

## [1.9.4]

### Fixed — The same expiry reminder went out three times

The hourly scheduler checked three thresholds in order and stopped at the first
open one:

    for day, flag in ((7, "notified_7d"), (3, ...), (1, ...)):
        if left <= day and not s[flag]: send(...); set(flag); break

That works for a subscription that enters the window at 30 days. It does not
work for one that enters at 1 day left — a short plan, reminders switched on
after the fact, or a bot that was down for a few hours. Such a subscription sits
inside all three thresholds at once:

    hour 1: the 7-day flag is open  ->  "only one day left"
    hour 2: the 3-day flag is open  ->  "only one day left"
    hour 3: the 1-day flag is open  ->  "only one day left"

Three identical messages in three hours, because all three are built from the
same `left`. Now one message closes every threshold the subscription has already
passed, and later thresholds still fire on their own as the date approaches.

### Added — The traffic warning that was never sent

`notified_80p` has been in the subscriptions table from the start, and both
renewal paths reset it. Nothing ever set it, and nothing ever read it — the
"you're running out of data" warning did not exist.

Unlike expiry, data has no date: a customer can burn a month's quota in one
night. They got no warning at all; the first news was the connection dropping,
with days still left on the subscription.

At 80% used, the customer now gets one message with what is left and a renew
button for that specific subscription. Usage comes from a single panel request
for all clients rather than one per client, and the warning resets with each
renewal, so it fires once per period.

## [1.9.3]

### Fixed — Affiliates were only paid on card purchases

`record_commission` was called from one place: the card-payment approval path.
Wallet purchases and auto-renewals both provision a config and deliver it, and
neither recorded a commission.

So an affiliate who brought a customer earned nothing from that customer's
wallet purchases and nothing from their automatic renewals — every month, for as
long as the subscription lasted. The money simply never appeared, with no error
to notice.

All three sale paths share one helper now. The existing uniqueness constraint on
(tenant, order) still prevents a double payment if an approval runs twice, and a
failure while recording the commission cannot block delivery — the sale already
happened and the customer is waiting.

## [1.9.2]

### Changed — Only configs that were actually used get charged

Every config in a group was billed, including ones created and never switched
on. Accounting now skips those — and only those.

The rule has to hold two things at once, because expiry is where a naive version
goes wrong. 3x-ui disables a config when its term ends, so billing on `enable`
alone would drop every config from the invoice the moment it expired — which is
backwards: expiry means the config **ran its term**. The customer used that
month and the reseller owes for it.

So a config is billed when it is enabled, or has traffic, or has expired. It is
skipped only when all three are false: disabled, no traffic, never expired — a
config that was created and never went into service.

Each group shows how many were skipped and why, so a due figure lower than the
config count explains itself instead of looking like a miscalculation.

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
