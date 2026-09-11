# Changelog

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
