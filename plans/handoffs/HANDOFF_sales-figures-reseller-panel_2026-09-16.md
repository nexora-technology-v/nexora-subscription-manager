# Nexora: sales figures that lied, and the reseller panel that had no way to add a reseller

**Date:** 2026-09-16
**Status:** COMPLETED (v1.42.0 released; two owner-side data repairs still unrun)
**Bead(s):** none — beads not installed on this machine
**Epic:** none
**Chain:** `standalone-eb5967a1` seq `1`
**Parent:** `none — first in chain`
**Prior chain:** `none — first in chain`

---

## Reference Documents

- `CLAUDE.md` — project conventions. **Read this first.** It grew by six rules during this session and now encodes most of what was learned here.
- `docs/spec-reseller-panel.md` — written before the reseller feature was built, per CLAUDE.md's own rule.
- `docs/spec-template.md` — the spec format.

## The Goal

Nexora is a 3x-ui (Xray) subscription manager for a Persian-speaking VPN reseller: admin panel (FastAPI + React), Telegram sales bot, reseller billing/accounting, and tunnels. The owner's standing priority is **accounting correctness** — every number shown to a reseller must be defensible.

This session ran a self-paced audit loop: each round picks one area, reads it, finds a real bug, fixes it, writes a test, **deliberately breaks the new test to confirm it goes red**, then releases. Mid-session the owner redirected twice — first to build out the reseller panel as a feature, then to audit the panel's UI visually by actually opening it.

Ten releases shipped: **v1.33.1 → v1.42.0**. The through-line of almost every bug: *the same rule written in two places and corrected in only one.*

## Where We Are

- Repo clean, on `main`, HEAD `d46a936`, tagged `v1.42.0`, both CI builds green. Working tree has no uncommitted changes.
- `VERSION` = `1.42.0`, matching `frontend/package.json`. Release gate (`tools/release-check.py`) passes.
- Test suites: 8 bot suites + 21 panel/tool suites + 3 seam suites + 1 throughput + 7 frontend checks. All green.
- `tools/test-admin-api.py` grew from ~90 to **161 passing checks** this session.
- `tools/test-ui-safety.py` grew from 34 to **48 passing checks**.
- `bot/test_flow.py` grew from 113 to **134 passing checks**.
- `tools/test-jobs.py` at **121**, `tools/test-agent.py` at **127**, `tools/test-health.py` at **46**.
- Two new tools created and wired into `nexora-cli.sh`: `repair-orders`, `repair-referrals`. Each has its own test suite registered in the release gate.
- `backend/app.py` is ~10.5k lines. `SQL_REAL_BUY` / `SQL_PLAN_JOIN` are now module-level constants read by three separate screens.
- Local dev loop established and proven: seed a temp bot.db, run `uvicorn app:app` on 8100, `preview_start` the Vite panel on 5174, drive it with the browser tools. Used this to find four defects no test caught.
- `fastapi` + `uvicorn` were pip-installed into the user Python (3.14.7) this session — they were not present before.
- The `claude-handoff` skill (handoff + handoffplan + PreCompact hook) was installed at user scope at the very end.
- **Not done:** the owner has still not run `nexora repair-orders --apply` or `nexora repair-referrals`, so historical data on the live server is still uncorrected. Asked five times across releases.
- **Not done:** 7 billing groups still have no rate configured (94 configs total), so the invoice remains incomplete. This is the longest-outstanding item, predating this session.

## What We Tried (Chronological)

### prior context — before this session's compaction (v1.26.0 → v1.33.1)

Carried forward from the pre-compaction summary. Not re-verified this session, but the pattern is the reason every later round looked for the same shape.

- Seven separate instances of *one rule, two places, fixed in one*: the "billable config" rule, the reseller open/closed flag (three truth tests), the root-tenant filter, agent module caching, service-stop before restore, build validation (JS on update, CSS on rollback), and `TUNNEL_PROCS` in monitor's fallback.
- `_period_share` established as the single money rule for billing; `_line_amount` for amounts (never `months × price`, which ignores the extra-device rate).
- `tools/import-topups.py` added — brought prepaid `credit_tx` top-ups into `payments` so they appear in accounting. The owner ran it; it reported "Nothing to import."
- `nexora import-topups` initially rejected its own arguments — missing `shift` in the `case` branch. Both tools added this session copy that `shift` and have a test asserting it.
- Three tests once passed *with the bug present* because the string being scanned appeared in the test's own comment. Every source-scanning assertion since strips comments first.
- Two self-inflicted flaky tests: fixtures sitting exactly on the 45/75-day month-rounding boundary, and a `"555" not in sub_id` check with a 1-in-304 collision chance. Both passed locally and failed on CI.

### early — audit rounds 1.34.0 through 1.38.0

1. **Duplicate-shape detector on money functions** (carried in from before compaction). Compared `spend_coins` vs `spend_balance` and `add_coins` vs `add_balance` by token shape at 99% similarity. Result: the twins were *consistent* — difference was only the table name. Not a bug. But the docstring pointed at the real risk (coins reserved at order time, returned on reject/expire/cancel), which led to reading the order-status paths.

2. **Order status vs money — the biggest find of the session.** Probed `wallet_pay` and `auto_renew_subscription` against real handlers with FakeBot/FakeXUI. Two bugs in *opposite directions*:
   - A wallet purchase was never marked `approved`. Config built and delivered, order stayed `pending`, sweeper marked it `expired` 30 min later. A real sale, in no figure, shown to the customer as "expired".
   - A failed auto-renewal was marked `approved` *before* provisioning, so when the panel call failed the money went back but the order stayed approved.
   - **The panel reported 200,000 — the right number for entirely the wrong reason.** The real sale was invisible; a refunded renewal was counted in its place. Two errors cancelling out is the worst failure mode because nothing looks wrong.
   - Fixed with `db.close_order()`: atomic status claim, refund only if the claim was won, amount computed from the ledger (spent minus already-returned).

3. **`reject_reason` column does not exist.** Both wallet paths' "balance ran out at the last moment" branches wrote `UPDATE orders SET status='rejected', reject_reason=...`. Proved by PRAGMA: the column has never existed and there is no migration for it. Those branches raised `OperationalError` instead of handling the race. The panel already uses `admin_note` for this; switched to it.

4. **Expiry sweeper kept wallet money.** It released held coins but not wallet balance, so a bot restart between taking payment and building the config left the customer out of pocket. Routed through `close_order`.

5. **`tools/repair-orders.py`** written because the code fix only helps new orders. Keyed on `sub_id`, which is set only after the panel call succeeds. Dry-run default, idempotent. Reports (never changes) orders that took money, delivered nothing, and refunded nothing — that is the owner's call, not a script's.

6. **Affiliate debt.** `bot_affiliates()` summed every affiliate's balance including resellers' own affiliates; `_affiliate_money_out()` (the ledger) correctly restricted to root tenants and said so in its own docstring. Reproduced: **page 700,000 vs ledger 200,000**. Fixed by making the page use the ledger's exact predicate. Deliberately did *not* hide reseller affiliates — the reseller portal has no affiliates section, so nobody else could see them; they stay, tagged, with their total counted separately.

7. **`requeue_stale` race.** `SELECT` then `UPDATE` with no status condition, across two connections. A result arriving in that gap could be overwritten: a finished job set back to `queued` and re-run, or worse, a job that *succeeded* after several attempts marked `failed` with "the agent took this N times and never answered" written over its result. Added `AND status='taken'` to both branches and took counts from `rowcount`. Test recreates the moment deterministically by wrapping the connection so the result lands right after the SELECT.

8. **Tunnel engine catalogue parity.** The catalogue lives once in the panel (`ENGINES`) and *four* more times in the agent (`repos`, `wanted_first`, `wanted`, `write_service`'s `ext` map). The agent downloads separately to the node, so the copies live on different machines. **Checked: they agreed.** Added a parity test anyway, because this exact shape had already drifted once (monitor's fallback was missing three tunnel engines). Also found `ENGINES["frp"]["binary"] = "frps"` — incomplete (FRP needs frps *and* frpc) but dead, since nothing read the field. Turned it into `binaries: ["frps","frpc"]` and made the parity test read it.

9. **Free trial counted as a purchase.** `bot_funnel`'s "خرید موفق" was `COUNT(DISTINCT user_id) WHERE status='approved'`, and taking the trial writes an approved order for zero. So everyone who pressed the trial button was a buyer, and the "trial only" segment was **structurally incapable of being non-zero**. With 5 seeded users of whom 2 really bought: reported 4. One of those 4 had a trial that *failed to build*. Also the third site of the approve-before-provision pattern — `give_trial` — which 1.34.0 had missed.

10. **Referral reward paid on one path of three.** `_pay_commission` had 3 call sites; `_reward_referrer` had 1 (card only). A friend who paid from wallet earned their inviter nothing, while the bot's own text promises coins when a friend "buys". Wrote the test *first* and watched it fail (0 coins instead of 10), then fixed. Added `tools/repair-referrals.py` — but defaulted to report-only because coins are a discount, i.e. real value, and that decision belongs to the owner.

### mid — workflow change, health checks, reseller feature

11. **Owner changed the release workflow** mid-loop: *"تا وقتی تست ها به صورت کامل به اتمام نرسیده ریلیز نساز فقط push کن"*. Switched to commit+push+green CI each round, holding tag/release until asked. Version parked at the next unreleased number while CHANGELOG entries accumulated under it.

12. **Wallet purchase was silent in the admin group.** Top-up, auto-renewal and card purchases all announce themselves (the card one arrives as a receipt the admin acts on). A wallet purchase needs no review, so an entire payment method produced no trace in the group at all. Found by the same call-set comparison that found the referral bug.

13. **Health checks that reported OK when they could not measure.** `check_disk`/`check_load` already did this right ("خوانده نشد"). Three did not:
    - **IPv6 was the worst** — when `ip` failed, `has_v6` stayed False and the result was "not configured — nothing wrong", i.e. the exact condition the check exists to find, reported as healthy.
    - `check_listening` returned `[]` when `ss` failed, so the check vanished from the page.
    - `check_uptime` returned `None`, which `run_all` drops.
    - Inside `run_all`, three groups were wrapped in `except: pass` while the loop directly above them correctly recorded a warning.
    - First break-sweep **missed one case** (ss succeeding with unparseable output); added that test, then all five went red.

14. **Owner interrupted mid-turn with a feature request**: reseller panel as its own section, more than one reseller, and per-reseller inbound selection. Investigated before asking anything and found all three rested on something broken:
    - **`create_tenant` is called only from tests in the whole repo.** There was no API, no UI, no CLI path to create a reseller. The portal page said "create a tenant from the bot section"; no such place exists. The owner was genuinely stuck with one tenant.
    - `UPDATE tenants SET inbound_mode=?, inbound_ids=?` **with no WHERE** — saving the owner's own inbound selection silently overwrote every reseller's.
    - The panel was one item inside the billing workspace.
    - Wrote `docs/spec-reseller-panel.md` first, as CLAUDE.md requires — that file's own note says the reseller panel once cost five rounds of requirements for want of one spec.

15. **Seam test caught a dead endpoint.** After adding `POST /api/admin/tenant`, `tools/test-seams.py` failed with "مسیر بی‌صداکننده‌ی تازه‌ای اضافه نشده". The test was right: an endpoint no frontend calls is dead. Forced building the UI in the same change rather than deferring it.

### late — portal features, conversion split, visual audit

16. **Reseller portal gained sales figures, filters, pagination.** The reseller runs their own bot but saw no sales numbers. Added this month's sales, total, card received, and pending — applying the two rules established earlier (trials excluded; "received" is card-only). The config table had a name search and rendered *every* row; added status filters and `usePager`. The orders list was also unpaginated **and capped at 50 server-side with the client sending no limit**, so a reseller saw only their newest 50 with nothing saying more existed.

17. **Portal ignored its own inbound selection.** Caught *after* shipping per-reseller inbounds: the bot read `inbound_mode`, but `_portal_inbound` returned a single `default_inbound` and `add_client` was called with no inbound list. So the owner could set "inbounds 41 and 45" and a config made from the reseller's own panel would land on the default. Same shape as everything else, in code written an hour earlier. Fixed before releasing 1.39.0.

18. **Two conversion rates on two screens.** 1.37.0 fixed the funnel; `bot_users_report` kept its own copy of the rule. With 10 users of whom 2 bought: **report said 80% conversion, funnel said 20%**. Average order value was **62,500 instead of 250,000** because zero-value trial orders dragged it down. Fixed by extracting `SQL_REAL_BUY` to one definition read by all three screens, plus a test asserting no hand-written copy of the condition survives anywhere.

19. **Owner: *"خودت از صفحه اسکرین بگیر متوجه کارت بشو"*.** Ran the panel locally and looked. Four defects no test caught:
    - The **owner themselves was listed as a reseller**, with a slug field, group picker, "open portal" button and the "before they can log in…" checklist. Could have opened a reseller portal for the root tenant by accident.
    - The inbound page **rendered twice** — self-inflicted: the patch script looped over `("App.jsx","app.jsx")` and Windows is case-insensitive, so both names were the same file and the route line was added twice.
    - A reseller's **configured group did not appear in the picker** — the group list comes from x-ui, and when the saved group was not in it the `<select>` fell back to the placeholder. With x-ui briefly unreachable, *every* reseller looked unconfigured.
    - And the reason was silent: the error from `_read_xui_clients` was discarded.
    - Separately, Persian placeholders on `dir="ltr"` monospace fields. **Tried `dir="auto"` first and measured it — it does not work**: on an input the direction comes from the *value*, not the placeholder, and an empty value means ltr. Moved the Persian into labels instead, matching what the same file already did two lines above.

20. **Owner pasted rendered HTML** and said info boxes stick to what is below them, in many places, and the new-reseller form is too empty. Measured the DOM instead of eyeballing: **`InfoBox` had `mt-4` and no bottom margin — exactly 0 pixels to the next element** — and it is used over a hundred times across nineteen sections. The form was rendering inside a `flex justify-between` row meant for buttons, so it took one column and left a large empty one. Fixed both; re-walked all eighteen sections and measured again: no flush pairs, no oversized gaps.

## Checked and Found Healthy (do not re-investigate)

These cost real time to verify. Each was a plausible bug that turned out fine — recorded so the next session does not spend the same hours.

- **Version comparison is safe past 1.39.** `check_update` parses versions into integer tuples, so `1.39.0 > 1.4.0` holds. `nexora-cli.sh` compares the release tag for *equality* ("am I on the latest tag?"), which has no ordering to get wrong. Reaching 1.40+ changes nothing.
- **Endpoint authentication is complete.** Swept all **151 routes**: every `/api/admin/*` calls `check_auth`, every `/api/portal/*` resolves through `Depends(portal_tenant)`. `tools/test-seams.py` already enforces both. The `/api/agent/*` module endpoints (`agent.py`, `health.py`, `firewall.py`) are unauthenticated but serve only public-repo source; `agent_checkin` verifies token + timestamp + signature.
- **The bot dashboard's lack of tenant scoping is by design.** `bot_stats`, the charts and the user counts deliberately span all tenants (server-wide view). The root filter belongs only where the question is "my money" — `_bot_money_in`, `_affiliate_money_out`, and now the funnel/report. Do not "fix" the dashboard.
- **The five tunnel config builders are correct.** Read `_cfg_backhaul`, `_cfg_rathole`, `_cfg_gost`, `_cfg_frp`, `_cfg_chisel` in full: traffic direction (Iran side opens ports, foreign side has the service) and local/remote port mapping are right in all five. The `[server]`/`[client]` inversion relative to the names is intentional and commented.
- **`record_commission` and `reward_referral` are properly guarded.** `UNIQUE(tenant_id, order_id)` plus an `IntegrityError` catch; the referral is an atomic conditional INSERT with rollback if the referrer vanished. Safe to call from any number of paths — which is why adding two more call sites was safe.
- **The top-up branch of `approve_order` cannot double-credit.** `claim_order` runs before any work.
- **Affiliate payout balance is computed from the payouts table**, not from commission statuses, so partial payments cannot corrupt the balance. The "mark commissions paid up to the amount" loop leaving a remainder is cosmetic, not a money bug.
- **The bot's `db` double-import is harmless at runtime.** `handlers.py` does `import db as DB`, `run.py` does `from bot import db` — two module objects in one process. Checked: `bot/db.py` has no module-level mutable state, only a shared SQLite file. It only matters for test patching (now in CLAUDE.md).
- **The 203 silently-swallowed exceptions found by sweep are mostly deliberate.** Best-effort Telegram sends, logging fallbacks, and the billing helpers that return 0/None feed a real "needs review / unpriced" surface. Only `health.py`'s four were genuine violations. Do not mass-"fix" the rest.

## Detectors written this session (reusable)

Each of these found something the previous rounds of reading had missed. Worth re-running when looking for a new class of bug rather than a specific one.

| Detector | What it does | What it found |
|---|---|---|
| Token-shape duplicate finder | Compares every function pair by token stream with names/literals erased; reports 72–99% matches | `monitor._Fallback` vs `netid` drift (1.33.1); confirmed the coin/wallet twins were consistent |
| Call-set comparison | For sibling functions (the three purchase paths), diffs which functions each one calls | The missing referral reward; the missing wallet-purchase notification |
| Silent-failure sweep | AST walk for `except` handlers with no logging that `pass` / `return None` / `return []` | 203 hits; 4 real ones in `health.py` |
| Coverage-by-name sweep | Lists functions whose name appears in no test file | Pointed at `tunnels.py` (`requeue_stale`, the `_cfg_*` builders) and `health.py` |
| Route-auth sweep | Every `@app.<verb>` decorator, matched against guard calls and `Depends` | Confirmed 151/151 guarded |
| DOM gap measurement | Walks rendered siblings, reports pairs with <8px gap and >36px gap, across every nav section | The 0px `InfoBox` gap; confirmed 18 sections clean afterwards |
| Persian-placeholder scan | `dir="ltr"` / mono fields whose placeholder contains Persian letters | 3 real, 1 false positive, 1 digits-only (fine) |

**Caveat learned:** the first placeholder scan used `<input[^>]*>` and broke on `=>` inside arrow-function props — a false negative on the very case being fixed. Widening it then produced a false positive on a `<span>`. Verify detector output before acting on it.

## Key Decisions

- **`close_order()` is one function, not two.** Status and money change together under one atomic claim, because every time they were written separately they drifted in opposite directions. `approved` is deliberately excluded from `REFUND_ON` — refunding a delivered sale would be gifting a subscription.
- **Refund amount comes from the ledger, not the order.** Spent minus already-returned, so a partial refund cannot be double-paid.
- **Repair tools default to report-only.** `repair-orders` corrects reporting; `repair-referrals` hands out coins, which is real value, so the owner decides. Rejected auto-applying either.
- **`repair-orders` does not touch "paid, undelivered, unrefunded" orders.** It reports them. The customer lost money there and a script should not decide.
- **Deleting a reseller was deliberately not built.** The tables cascade — it would take the reseller's users, orders, subscriptions and wallet. "Close portal" already exists and is reversible.
- **A new reseller is always a child of root.** Without `parent_id` it counts as an owner in the accounting and its revenue mixes with the owner's — the rule CLAUDE.md already encodes for `FROM tenants LIMIT 1`.
- **Reseller affiliates stay visible, counted separately.** Hiding them was simpler but nobody else can see them — the reseller portal has no affiliates section.
- **`usePager` imported from the shared UI library into the portal**, not copied. The portal is deliberately isolated from admin *code*, but pagination is a shared primitive and `ui/jalali` was already imported.
- **`SQL_REAL_BUY` as a module constant** rather than fixing each screen. Three releases went by fixing one copy at a time; the test now asserts no hand-written copy remains.
- **Handoff written to `plans/handoffs/`** per the skill, not `.claude/handoffs/`. Flagged to the owner because `.claude/` is gitignored and this path is not, and the repo is public.

## Evidence & Data

### Releases this session

| Tag | What it fixed |
|---|---|
| v1.33.1 | monitor's fallback out of step with netid (3 tunnel engines missing) |
| v1.34.0 | order status told the truth about the money; `reject_reason` column never existed |
| v1.35.0 | resellers' affiliate debt counted as the owner's |
| v1.36.0 | `requeue_stale` overwrote a result that just arrived; engine catalogue guarded |
| v1.37.0 | free trial counted as a purchase in the funnel |
| v1.38.0 | referral reward paid on every purchase path, not just card |
| v1.39.0 | reseller panel feature + wallet-purchase notification + health checks + portal sales/filters/pagination |
| v1.40.0 | one definition of a real purchase, read by all three screens |
| v1.41.0 | four reseller-panel defects found by opening the page |
| v1.42.0 | info-box spacing; new-reseller form width |

### The 1.34.0 reproduction — two errors cancelling out

| | Before fix | Truth |
|---|---|---|
| Wallet purchase (delivered) | `pending` → swept to `expired` | approved sale |
| Failed auto-renew (refunded) | `approved` | rejected |
| Panel "total sales" | **200,000** | **200,000** |

The number matched. The composition was entirely wrong.

### The 1.35.0 affiliate split

| Screen | Figure |
|---|---|
| Affiliates page "مجموع بدهی به همکاران" | 700,000 |
| Ledger `_affiliate_money_out` | 200,000 |
| Difference | 500,000 = one reseller's debt to their own affiliate |

### The 1.37.0 funnel — 5 users, 2 real buyers

| Metric | Reported | Truth |
|---|---|---|
| خرید موفق | 4 | 2 |
| trialOnly | 0 (structurally impossible to exceed) | 1 |

One of the 4 had a trial that failed to build.

### The 1.40.0 conversion split — 10 users, 6 trial-only, 2 buyers

| Metric | Sales report | Funnel | Truth |
|---|---|---|---|
| Conversion | **80%** | 20% | 20% |
| Orders | 8 | — | 2 |
| Average order | **62,500** | — | **250,000** |
| Buyers | 8 | 2 | 2 |

### The 1.42.0 spacing measurement

| | Value |
|---|---|
| Gap from `InfoBox` to next element | **0 px** |
| `InfoBox` call sites | 100+ across 19 section files |
| Sections re-measured after fix | 18, zero flush pairs, zero oversized gaps |

### Break-the-test sweeps (every fix was verified red)

| Area | Reintroductions | Caught first pass |
|---|---|---|
| Order status / `close_order` | 6 | 6 |
| `repair-orders` tool | 6 | 5 → added STRANDED rows, then 6 |
| Affiliate debt | 4 | 4 |
| Jobs race + engine parity | 8 | 7 → added failed-branch case, then 8 |
| Funnel / trial | 6 | 6 |
| Referral reward | 3 | 3 |
| Health checks | 5 | 4 → added empty-`ss` case, then 5 |
| Reseller backend | 6 | 5 (sixth is double-guarded by `rowcount`; outcome unchanged) |
| Portal sales/filters/pagination | 7 | 7 |
| Portal inbound parity | 4 | 4 |
| Sales report | 6 | 6 |
| Reseller UI defects | 6 | 5 → added picker guard, then 6 |
| Spacing / layout | 3 | 3 |

Three sweeps found a gap in my own tests on the first pass. That is the sweep earning its keep.

### Test suite growth

| Suite | End of session |
|---|---|
| `tools/test-admin-api.py` | 161 |
| `bot/test_flow.py` | 134 |
| `tools/test-jobs.py` | 121 |
| `tools/test-agent.py` | 127 |
| `tools/test-ui-safety.py` | 48 |
| `tools/test-health.py` | 46 |
| `tools/test-repair-orders.py` | 28 (new) |
| `tools/test-repair-referrals.py` | 27 (new) |

### The engine catalogue — five copies, one machine apart

| Location | Holds |
|---|---|
| `backend/tunnels.py :: ENGINES` | name, repo, binaries, config format, transports |
| `agent :: repos` (inside `install_engine`) | repo per engine |
| `agent :: wanted_first` | single binary name |
| `agent :: wanted` (inside `install_engine`) | binary list |
| `agent :: write_service` `ext` map + if/elif | config extension, which binary per side |

Checked: consistent. Now guarded by a parity test covering all five plus the per-engine branch.

## The two repair tools — exact semantics

This is the top next action, so here is precisely what they do. Both print English (terminal RTL rule), default to report-only, and are idempotent.

### `nexora repair-orders`

Corrects order *statuses* written before 1.34.0. Changes no money.

| Query | Matches | Action |
|---|---|---|
| `SOLD` | `paid_from='wallet'`, status `pending`/`expired`, **`sub_id IS NOT NULL`**, a negative wallet_tx exists, no positive one | → `approved` |
| `FAILED` | `paid_from='wallet'`, status `approved`, **`kind='renew'`**, `sub_id IS NULL` | → `rejected` |
| `STRANDED` | `paid_from='wallet'`, status `pending`/`expired`, `sub_id IS NULL`, money taken, nothing returned | **reported only, never changed** |

It prints `reported sales change: +N` so the owner sees how the figures move before applying. `STRANDED` rows are where a customer paid and got nothing — the tool refuses to decide.

### `nexora repair-referrals`

Pays referral coins that wallet purchases never paid. **Hands out real value**, hence report-only by default.

- Finds users with `referred_by` set, at least one approved **non-trial** order, and no existing `coin_tx` with `kind='referral'` and `ref_user_id = user`.
- Pays through the bot's own `reward_referral`, so the once-per-friend rule applies and a second run finds nothing.
- If a tenant's referral rate is 0 it pays nothing **and says why** — silence there would let the owner think accounts were settled.

### Test case matrices

`tools/test-repair-orders.py` — 11 orders, 4 must change, 7 must not:

| # | Case | Expected |
|---|---|---|
| 1 | wallet buy delivered, sweeper marked it expired | → approved |
| 2 | wallet buy delivered, still pending | → approved |
| 3 | failed renewal, refunded, left approved | → rejected |
| 4 | same, with an old refund carrying no `order_id` | → rejected |
| 5 | genuinely successful renewal | untouched |
| 6 | card sale | untouched |
| 7 | genuinely expired unpaid order | untouched |
| 8 | purchase that errored and was refunded | untouched |
| 9 | money taken, no config, no refund | untouched (reported) |
| 10 | config built but later refunded | untouched |
| 11 | approved `new` order with no config | untouched (rule is about renewals) |

Cases 9–11 were added after the first break-sweep: three loosened conditions went undetected without them.

`tools/test-repair-referrals.py` — 5 referred users, 1 owed:

| Person | Situation | Owed? |
|---|---|---|
| الف | bought by wallet, inviter never paid | **yes** |
| ب | only took the free trial | no |
| ج | bought, inviter already paid | no |
| د | no inviter | no |
| ه | order was rejected | no |

## Where the evidence lives

**No raw result files survive.** Every probe, detector and break-sweep script ran from the session scratchpad (`%TEMP%/claude/.../scratchpad/`) and that directory is not persistent. This is deliberate — CLAUDE.md forbids stray files, and a probe that proves a bug is worthless once the bug is fixed and a test guards it.

What *is* persistent, and where to look instead:

| Evidence | Lives in |
|---|---|
| Every bug's reproduction, as an assertion | the test suites — each fix's test names the old wrong number in its `detail` string |
| The 1.34.0 / 1.37.0 / 1.40.0 reproductions | `tools/test-admin-api.py`, `bot/test_flow.py` — the fixtures ARE the probes, promoted |
| What each release fixed and why | `CHANGELOG.md` — written as "what was broken and why", not a commit list |
| The reseller design and its rejected options | `docs/spec-reseller-panel.md` |
| Lessons compressed into rules | `CLAUDE.md` |

If a number in this handoff needs re-deriving, the matching test fixture reproduces it — that is why the fixtures were written with the wrong values recorded in their failure messages.

## Code Analysis

- `db.close_order(order_id, status, note=None, from_status="pending")` → `(claim_won, refunded_amount)`. The `UPDATE` is both the claim and the write-lock, so the reads that follow inside the same transaction are safe. `REFUND_ON = ("rejected","expired","cancelled")`.
- `_portal_inbound_ids(t, inbound)` mirrors `bot/handlers.py`'s logic: mode `all` → `None` (x-ui decides), `custom` → tenant's ids, `default` → `[default_inbound]`. **An empty custom list must return `None`, not `[]`** — an empty list tells x-ui to attach the config to no inbound at all.
- `SQL_PLAN_JOIN = "LEFT JOIN plans p ON p.id = o.plan_id"`, `SQL_REAL_BUY = "o.status='approved' AND COALESCE(p.is_trial,0)=0"`. Read by `bot_funnel`, `bot_users_report`, `_portal_sales`.
- `sub_id` is set only after a successful panel call — the reliable signal for "was this actually delivered", used by `repair-orders`.
- `reward_referral` is an atomic conditional INSERT guarded by `NOT EXISTS (... kind='referral' AND ref_user_id=?)`, with the coin row deleted again if the referrer no longer exists. Safe to call from any number of paths.
- `InfoBox` now `my-4 last:mb-0`. Tailwind 3.4.17 generates `.last\:mb-0:last-child` — verified in the built CSS.
- `usePager(items, perPage)` is the table-safe pagination hook (`LongList` puts content in a `div`, which is invalid inside `<table>`).
- The portal is a separate Vite entry (`frontend/src/portal/index.jsx`, ~1.5k lines) and deliberately cannot reach admin routes or components.

## Files Changed

### Backend
- `backend/app.py` — `SQL_REAL_BUY`/`SQL_PLAN_JOIN` constants; `bot_funnel`, `bot_users_report`, `_portal_sales` unified; `tenant_create` endpoint (new); `tenant_portal_list` filtered to children + `groupsError`; `bot_inbounds` get/set made per-tenant with a real `WHERE`; `_portal_inbound_ids` (new); `portal_orders` limit raised with `truncated` flag.
- `backend/health.py` — `check_ipv6`, `check_listening`, `check_uptime` report failure instead of silence; `run_all`'s three `except: pass` groups replaced with a keyed `_group` helper.
- `backend/tunnels.py` — `requeue_stale` claims with `AND status='taken'` and counts from `rowcount`; `ENGINES[*].binary` → `binaries` list.
- `bot/db.py` — `close_order()` (new, with `REFUND_ON`).
- `bot/handlers.py` — `wallet_pay`, `auto_renew_subscription`, `give_trial` all approve only after provisioning and close through `close_order`; `_reward_referrer` added to wallet and auto-renew paths; wallet purchase announced to the admin group.
- `bot/run.py` — expiry sweeper refunds wallet money under the claim and tells the customer.

### Frontend
- `frontend/src/lib/constants.js` — `reseller` workspace added, `bill-portal` moved out of billing, `WS_COLOR` gained `reseller` and `firewall`.
- `frontend/src/App.jsx` — `ResellerInbounds` route (and the duplicate line removed).
- `frontend/src/sections/portal-admin.jsx` — `NewReseller` form, `ResellerInbounds` page, group picker keeps its own value, `groupsError` surfaced, form lifted out of the button row.
- `frontend/src/sections/bot/inbounds.jsx` — accepts a `tenant` prop.
- `frontend/src/portal/index.jsx` — sales stat cards, status filters, `usePager` on both the config table and the orders list, truncation notice.
- `frontend/src/ui/index.jsx` — `InfoBox` spacing.
- `frontend/src/sections/billing.jsx`, `frontend/src/sections/bot/connection.jsx` — Persian placeholders moved out of ltr/mono fields.

### Tools & tests
- `tools/repair-orders.py` + `tools/test-repair-orders.py` — new.
- `tools/repair-referrals.py` + `tools/test-repair-referrals.py` — new.
- `tools/release-check.py` — both new suites registered.
- `tools/test-admin-api.py`, `tools/test-ui-safety.py`, `tools/test-seams.py` consumers, `bot/test_flow.py`, `tools/test-jobs.py`, `tools/test-agent.py`, `tools/test-health.py` — extended.
- `nexora-cli.sh` — `repair-orders` and `repair-referrals` branches (both with the `shift`), plus help lines.

### Docs
- `CLAUDE.md` — six new rules (see below).
- `docs/spec-reseller-panel.md` — new.
- `CHANGELOG.md` — ten sections.

## The reseller feature — what was built

Built from `docs/spec-reseller-panel.md`, which was written first.

### New API surface

| Endpoint | Purpose |
|---|---|
| `POST /api/admin/tenant` | Create a reseller. Requires name, slug (sanitised, unique), password ≥8 chars. Optional group, credit mode. Always sets `parent_id` = root. Always creates with `portal_enabled=0`. |
| `GET /api/admin/bot/inbounds?tenant=N` | Inbound *selection* for that tenant; the inbound *list* still comes from the owner's x-ui. |
| `PUT /api/admin/bot/inbounds` (+ `tenant` in body) | Writes with `WHERE id=?`. Without `tenant`, targets the root tenant — so the existing bot page behaves exactly as before. |
| `GET /api/admin/tenant/portal-list` | Now children only, plus `groupsError`. |
| `GET /api/portal/stats` | Now carries a `sales` block (`hasBot`, `orders`, `sold`, `received`, `monthOrders`, `monthSold`, `pending`). |
| `GET /api/portal/orders` | Limit 200 (cap 500) with a `truncated` flag. |

### New UI

- `WORKSPACES.reseller` — its own workspace beside firewall and tunnel, colour `#38BDF8`. (`WS_COLOR` was also missing a `firewall` entry; added.)
- Two items: «نماینده‌ها و دسترسی» (the moved `bill-portal`) and «اینباند نماینده‌ها» (`res-inbounds`).
- `NewReseller` form — name, link slug (guessed from the name until the admin types their own), x-ui group, generated password, prepaid checkbox.
- `ResellerInbounds` — a reseller picker feeding the existing `BotInboundsSection` via a new `tenant` prop (component reused, not copied).
- Reseller portal — 4 sales stat cards, 7 status filters with an "N of M" counter, numbered pagination on both the config table and the orders list.

### Deliberately not built

- **Reseller deletion.** `ON DELETE CASCADE` would take the reseller's users, orders, subscriptions, coin and wallet history. "Close portal" is reversible and already exists.
- **Auto-creating the x-ui group.** The group is just a label on clients; the owner types it.
- **A bot token at creation time.** The reseller sets their own via `/api/portal/bot`.

## User Feedback & Preferences (REQUIRED)

- **"فقط لطفا هر چیزی که میخوای برای چک کردن استفاده کنی حتما انگلیسی باشه که داخل لینوکس بهم نریزه"** — diagnostic tool output must be English; RTL mixes badly with LTR terminals. UI and code comments stay Persian. Both new tools follow this.
- **"ببین من نرخ رو خودم داخل سیستم تعریف میکنم تو فقط باید درست محاسبه کنی همین"** — the owner sets rates; the system only calculates. Do not guess rates.
- **"بهت گفتم ریلیز نساز همه مسائل رو حل کن وقتی مسئله تا آخر به اتمام رسید منتشر کن"** — do not release mid-work.
- **"هر وقت تست کامل به اتمام رسید و نیاز به ادامه دادن نبود ریلیز رو بساز و هر قسمت رو که به اتمام رسوندی ۱ دقیقه بعد خودت شروع کن به فعالیت بعدی"** — self-start the next round 60s after finishing one.
- **"تا وقتی تست ها به صورت کامل به اتمام نرسیده ریلیز نساز فقط push کن اخرین مرحله ریلیز رو بساز"** — later refinement: push each round, tag/release only when told. This is the current standing workflow.
- **"قسمت پنل نمایندگی رو جدا مثل فایروال و اینا در نظر بگیر … من فقط میتونم یک نماینده در نظر بگیرم و این مشکل هستش"** — the reseller feature request.
- **"قسمت نمایندگی به صورت کامل هم از لحاظ بکند و از لحاظ ui دارای مشکل است خودت از صفحه اسکرین بگیر متوجه کارت بشو"** — look at the running page yourself. This produced four defects no test caught, and the local-panel workflow is now proven and fast.
- **"این المنت ها بیشتر چسبیده هستن به دایو های پایینی … تقریبا در خیلی جاها از پنل که الان حضور ذهن ندارم"** — the owner was right that it was everywhere; the cause was one shared component.
- **"ضمنا من دوست ندارم پنل فضای خالی زیادی داشته باشه"** — no excessive empty space. This is why `InfoBox` got `last:mb-0` rather than a plain bottom margin.
- **The repo is public.** No tokens, passwords, server IPs, or customer data may be committed. Held to throughout.
- Answers in Persian; releases and CHANGELOG in Persian; commit messages and diagnostic output in English.
- **"اگر برای ادامه دادن موضوعی داری ادامه بده وگرنه ریلیز رو بساز"** — the owner will ask whether there is more worth doing before releasing. Answering honestly paid off: saying "yes, and it is in the feature I just built" caught the portal-inbound gap before it shipped half-working.
- **"این اسکیل رو به صورت کامل برای خودت نصب کن"** — "completely" means making it actually work, not following the README literally. The README's install steps omit registering the PreCompact hook in `settings.json`, without which the hook never runs.
- The owner reads release notes carefully and acts on them — but has *not* run the two repair tools despite five reminders. Worth asking directly rather than repeating the reminder.
- The owner pastes rendered HTML or terminal output when something is wrong, and is accurate about *where* the problem is even when unsure of the cause ("تقریبا در خیلی جاها ... حضور ذهن ندارم" — and it was indeed everywhere, from one shared component). Take the report seriously and look for a shared cause rather than the one instance shown.

## Tooling installed at user scope (not in this repo)

Done at the very end of the session, at the owner's request, from `https://github.com/REMvisual/claude-handoff`:

| Path | What |
|---|---|
| `~/.claude/skills/handoff/` | this skill + 4 reference files |
| `~/.claude/skills/handoffplan/` | handoff + phased plan variant |
| `~/.claude/hooks/precompact-handoff.sh` | pre-compaction safety net |
| `~/.claude/settings.json` | **created** — registers the `PreCompact` hook (the README omits this step, so a copy-only install never fires) |
| `~/.claude/CLAUDE.md` | **created** — the repo's recommended anti-shadowing rule, placed at user scope rather than in this public repo |

All three executables were read before installing. The hook is benign: reads `git log/status/diff` plus beads, writes one markdown file, no network. In this repo its output lands in `.claude/handoffs/`, which is already gitignored — so it cannot break the release gate's "nothing uncommitted" check. Verified.

`fastapi` and `uvicorn` were also pip-installed (user site) to run the panel locally; they were not previously present.

## Where We're Going

1. **Ask the owner to run `nexora repair-orders`** (report-only) and read the output together. Until this runs, the bot's historical sales figures on the live server stay wrong — every code fix since 1.34.0 only affects new orders. Five reminders have not moved it; a direct question about what is blocking them will.
2. **Then `nexora repair-referrals`** (report-only). It hands out coins, so the owner decides; showing them the list is the useful step.
3. **The 7 unconfigured billing groups** — `ali` 31, `(بدون گروه)` 28, `sajjad` 14, `Ali kottah` 9, `yaser` 5, `dastani` 4, `Pelleaval` 3 = 94 configs. The invoice is incomplete until these have rates. This predates the session and is the oldest open item.
4. **"به‌روزرسانی ایجنت"** from the tunnel page, so the Iran node picks up the agent-side changes from 1.36.0.
5. **Resume the audit loop** if asked — but see Risks: the yield has dropped sharply.
6. If continuing the UI work, **use the local-panel workflow** (below). Measuring the DOM beats reading screenshots; a 0px gap is invisible in a scaled-down image.

## Risks & Blockers

- **Audit yield is falling.** Every high-risk area (accounting, wallet, commissions, referrals, portal, tunnels, firewall, health, jobs) has now had at least one deep pass. Later rounds needed detectors rather than reading. An owner-supplied lead ("this number looks wrong", "a customer complained") is now worth more than blind searching — this was said to the owner and is still true.
- **Local panel has no real x-ui.** The visual audit ran against a seeded DB with the panel unreachable, which is *why* the "group not in list" bug was visible — but it also means defects that only appear with live data or a reachable panel were not exercised.
- **The PreCompact hook is newly registered** and may not fire until Claude Code restarts. The skills themselves work now.
- **`plans/handoffs/` is a tracked path** in a public repo (`.claude/` is gitignored, `plans/` is not). This handoff contains no secrets, but the owner may prefer it moved.

## Open Questions

- Why hasn't the owner run the repair tools? Unclear whether it is caution about `--apply`, the reminders being buried in long release notes, or simply not having been at the server. Ask plainly.
- Should the discount-code feature be finished? The `discounts` table, `validate_discount`, and the `discount_code`/`discount_pct` columns all exist but nothing calls them. Recorded in CLAUDE.md as unwired. The owner has not commented.
- Does any reseller actually run their own Telegram bot yet? The per-reseller sales block and inbound selection assume they might; if none do, some of that surface is untested in the real world.

## CLAUDE.md rules added this session

These now govern future work and are the compressed form of everything above:

- وضعیتِ سفارش و پولِ سفارش یک چیزند — go through `db.close_order()`, never a raw `UPDATE orders`.
- سفارش تا وقتی کانفیگش ساخته نشده `approved` نمی‌شود — found at four separate sites; `test_flow` now scans for a fifth.
- هر سه مسیرِ خرید باید هر سه پرداخت را انجام دهند — commission *and* referral, checked by ast.
- تست رایگان خرید نیست — `COALESCE(p.is_trial,0)=0`; amount alone is not enough.
- کد تخفیف وصل نیست — do not build on it.
- ماژول `db` در ربات دو نسخه دارد — `handlers.py` uses `import db as DB`, tests use `from bot import db`; patch `H.DB.TenantDB`, not `db.TenantDB`.

## Environment traps hit this session

- **Git Bash heredocs eat backslashes** — hit twice more despite being documented. Use the Write tool for patch scripts containing escapes.
- **Windows is case-insensitive** — a patch script looping over `("App.jsx","app.jsx")` wrote the same file twice and duplicated a route. Now guarded by a ui-safety test.
- Python 3.14.7 is native Windows; Git Bash `$HOME` is `/c/Users/FrsCo`. Passing a Git Bash path to Python fails — use the Windows path.
- `jq` is **not installed**; validate JSON with Python.
- `PYTHONIOENCODING=utf-8` required for every Python test (Persian output).
- A browser sweep that clicks every button **will click "خروج"** and log the session out. Exclude destructive labels.
- `gh run list` needs `-R nexora-technology-v/nexora-subscription-manager`; the default repo resolves wrongly. Two runs can race on one push — GitHub cancels the duplicate, so filter on `conclusion != "cancelled"`.

## Quick Start for Next Session

```bash
# Reference docs — read CLAUDE.md first, it encodes this session's lessons
cat CLAUDE.md
cat docs/spec-reseller-panel.md

# Verify current state
git log --oneline -5
cat VERSION                       # expect 1.42.0
PYTHONIOENCODING=utf-8 python tools/release-check.py --fast

# Key files if continuing accounting work
#   bot/db.py              :: close_order, reward_referral
#   bot/handlers.py        :: wallet_pay, auto_renew_subscription, give_trial
#   backend/app.py         :: SQL_REAL_BUY, bot_funnel, bot_users_report, _portal_sales

# Key files if continuing reseller/UI work
#   frontend/src/sections/portal-admin.jsx
#   frontend/src/portal/index.jsx
#   frontend/src/ui/index.jsx

# Run the panel locally (this found 4 defects no test caught)
#
# 1. Seed data/bot.db: botdb.init_db(), then a root tenant (parent_id NULL,
#    panel_url/panel_user/panel_pass/default_inbound set) plus 2-3 children
#    with portal_slug / portal_pass / portal_group / portal_enabled.
#    Vary them: one prepaid (credit=0), one postpaid (credit=-1), one
#    incomplete (no group, closed) — the incomplete one exposes the most.
# 2. Backend:
cd backend && NEXORA_SUBPAGE_ADMIN_PASSWORD=testpw CONFIG_PATH=../data/config.json \
  BOT_DB_PATH=../data/bot.db python -m uvicorn app:app --host 127.0.0.1 --port 8100 &
# 3. .claude/launch.json with name "panel", runtimeExecutable npm,
#    runtimeArgs ["run","dev","--prefix","frontend"], port 5174
# 4. preview_start "panel", log in with testpw (use form_input by ref —
#    clicking by coordinate on a scaled screenshot misses)
#
# MEASURE the DOM — do not judge spacing from scaled screenshots.
# Do NOT click every button in a sweep: one of them is "خروج".
#
# CLEAN UP afterwards:
#   netstat -ano | grep :8100 | grep LISTENING   → taskkill //F //PID <pid>
#   rm -f data/bot.db data/bot.db-wal data/bot.db-shm data/usage-history.json
#   rm -f .claude/launch.json
#   git checkout -- data/config.json    # it is tracked; rm -rf data/ deletes it

# Next action
#   Ask the owner directly what is blocking `nexora repair-orders` —
#   five release notes have asked and it still has not run, so the live
#   server's sales history is still wrong.
```

---

## Session Closed

**Closed at:** 2026-09-16
**Commit:** cfefdc4
**Session status:** Handed off to next session
