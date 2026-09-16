/**
 * ربات: کاربران و پرونده‌ی مشتری.
 *
 * از App.jsx جدا شد؛ آن فایل ۱۱۴۰۰ خط بود و پیداکردن یک کامپوننت
 * در آن عملاً ناممکن.
 */
import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import {
  AlertTriangle, Ban, ChevronLeft, Loader2, Package, RefreshCw, Search, Send, Users, Wallet, X,
} from "lucide-react";
import { API_URL } from "../../lib/constants";
import { daysLeft, errText, faNum, fmtBytes, fmtDate } from "../../lib/format";
import { Avatar, EmptyState, InfoBox, Modal, Msg, PageSkeleton, SectionHead, StatTile, StatusPill } from "../../ui/index";

// فیلترهای بخش کاربران — کلیدها باید عیناً با _USER_FILTERS در
// backend/app.py بخوانند.
export const USER_FILTERS = [
  { key: "all", label: "همه" },
  { key: "active", label: "اشتراک فعال" },
  { key: "expired", label: "منقضی‌شده" },
  { key: "never", label: "بدون خرید" },
  { key: "buyers", label: "خریدار" },
  { key: "withPhone", label: "شماره دارد" },
  { key: "noPhone", label: "بدون شماره" },
  { key: "withBalance", label: "کیف پول دار" },
  { key: "withCoins", label: "سکه دار" },
  { key: "referred", label: "با دعوت" },
  { key: "blocked", label: "مسدود" },
];

export const USER_SORTS = [
  { key: "new", label: "تازه‌ترین" },
  { key: "old", label: "قدیمی‌ترین" },
  { key: "spent", label: "بیشترین خرید" },
  { key: "balance", label: "بیشترین موجودی" },
  { key: "coins", label: "بیشترین سکه" },
  { key: "lastSeen", label: "آخرین فعالیت" },
];

export const PAGE = 40;

export function BotUsersSection({ password }) {
  const [d, setD] = useState({ users: [], total: 0, counts: {} });
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("new");
  const [offset, setOffset] = useState(0);
  const [detail, setDetail] = useState(null);
  const [msgTo, setMsgTo] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async (opts = {}) => {
    const query = opts.q !== undefined ? opts.q : q;
    const f = opts.filter || filter;
    const s = opts.sort || sort;
    const off = opts.offset !== undefined ? opts.offset : offset;
    setLoading(true);
    try {
      const p = new URLSearchParams({
        q: query, filter: f, sort: s, offset: off, limit: PAGE,
      });
      const r = await fetch(`${API_URL}/api/admin/bot/users?${p}`,
        { headers: { "X-Admin-Password": password } }).then((x) => x.json());
      setD({ users: r.users || [], total: r.total || 0, counts: r.counts || {} });
    } catch { /* بی‌صدا */ }
    finally { setLoading(false); }
  };
  useEffect(() => { load({ offset: 0 }); }, [password]);

  // جستجوی زنده — بدون این، ادمین باید هر بار Enter بزند
  useEffect(() => {
    const t = setTimeout(() => { setOffset(0); load({ q, offset: 0 }); }, 350);
    return () => clearTimeout(t);
  }, [q]);

  const pick = (key) => { setFilter(key); setOffset(0); load({ filter: key, offset: 0 }); };
  const pickSort = (key) => { setSort(key); setOffset(0); load({ sort: key, offset: 0 }); };
  const go = (off) => { setOffset(off); load({ offset: off }); };

  const users = d.users;
  const pages = Math.ceil(d.total / PAGE) || 1;

  // خلاصه‌ی همین صفحه — بدون درخواست تازه
  const rows = d.users || [];
  const walletSum = rows.reduce((a, u) => a + (Number(u.balance) || 0), 0);
  const withPhone = rows.filter((u) => u.phone).length;
  const blocked = rows.filter((u) => u.is_blocked).length;
  const page = Math.floor(offset / PAGE) + 1;

  return (
    <div className="fx-anim">
      <SectionHead title="کاربران ربات"
        desc="هر کسی که با ربات تعامل داشته — با سابقه‌ی خرید، شماره تماس و امکان پیام مستقیم."
        action={
          <button onClick={() => load()} disabled={loading}
            className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
            <RefreshCw size={13} /> بازخوانی
          </button>
        } />

      {/* خلاصه، از همان داده‌ای که فهرست از آن ساخته شده */}
      {!loading && (d.users || []).length > 0 && (
        <div className="fx-g4 grid grid-cols-3 gap-3">
          <StatTile label="کاربران" icon={Users} tone="var(--accent-2)"
            value={faNum(d.total || 0)}
            hint={`${faNum((d.users || []).length)} مورد در این صفحه`} />
          <StatTile label="کیف پول این صفحه" icon={Wallet} tone="var(--ok)"
            value={faNum(walletSum)} unit="تومان" color="var(--ok)"
            hint={`${faNum(withPhone)} نفر شماره ثبت کرده‌اند`} />
          <StatTile label="بلاک‌شده" icon={Ban}
            tone={blocked ? "var(--danger)" : "var(--muted)"}
            value={faNum(blocked)}
            color={blocked ? "var(--danger)" : "var(--text)"}
            hint={blocked ? "به ربات دسترسی ندارند" : "کسی بلاک نیست"} />
        </div>
      )}

      <div className="fx-card p-4 mb-4">
        <div className="fx-search mb-3" style={{ width: "auto" }}>
          <Search size={14} style={{ color: "var(--muted)" }} />
          <input placeholder="نام، یوزرنیم، آیدی عددی یا شماره تماس..." value={q}
            onChange={(e) => setQ(e.target.value)} />
          {q && (
            <button title="پاک‌کردن جستجو" onClick={() => setQ("")} className="shrink-0">
              <X size={13} style={{ color: "var(--muted)" }} />
            </button>
          )}
        </div>

        <div className="flex flex-wrap gap-1.5 mb-3">
          {USER_FILTERS.map((f) => {
            const on = filter === f.key;
            const n = d.counts[f.key];
            return (
              <button key={f.key} onClick={() => pick(f.key)}
                className="px-2.5 py-1.5 rounded-[9px] text-[13px] transition-all"
                style={on
                  ? { background: "var(--accent-2)", color: "#06090F", fontWeight: 600 }
                  : { color: "var(--dim)", border: "1px solid var(--border-2)" }}>
                {f.label}
                {n !== undefined && (
                  <span className="mr-1" style={{ opacity: 0.65 }}>({faNum(n)})</span>
                )}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[12px]" style={{ color: "var(--muted)" }}>مرتب‌سازی:</span>
          {USER_SORTS.map((s) => (
            <button key={s.key} onClick={() => pickSort(s.key)}
              className="px-2 py-1 rounded-[8px] text-[13px] transition-all"
              style={sort === s.key
                ? { background: "var(--accent-soft)", color: "var(--accent-2)" }
                : { color: "var(--muted)" }}>
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <PageSkeleton />
      ) : users.length === 0 ? (
        <EmptyState icon={Users} text={q ? `چیزی برای «${q}» پیدا نشد` : "در این دسته کاربری نیست"} />
      ) : (
        <>
          <div className="fx-card overflow-hidden mb-3">
            {users.map((u, i) => (
              <div key={u.id}
                className="flex items-center justify-between gap-3 p-4 flex-wrap transition-colors hover:bg-white/[.02]"
                style={{ borderBottom: i < users.length - 1 ? "1px solid var(--border)" : "none" }}>
                <button onClick={() => setDetail(u.tg_id)}
                  className="min-w-0 flex-1 text-right flex items-center gap-3">
                  {/* چهره‌ی کاربر — در فهرستِ بلندِ هم‌شکل، چشم روی
                      رنگ می‌ایستد نه روی شناسه‌ی چهارده‌رقمی */}
                  <Avatar name={u.first_name || u.username} id={u.tg_id} size={38} />
                  <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[14px] font-semibold text-white">
                      {u.first_name || "بدون نام"}
                    </span>
                    {u.username && (
                      <span className="text-[13px]" dir="ltr" style={{ color: "var(--muted)" }}>
                        @{u.username}
                      </span>
                    )}
                    {u.activeSubs > 0 && (
                      <span className="fx-pill" style={{ background: "rgba(52,211,153,.12)", color: "var(--ok)" }}>
                        فعال
                      </span>
                    )}
                    {u.is_blocked === 1 && (
                      <span className="fx-pill" style={{ background: "rgba(248,113,113,.12)", color: "var(--danger)" }}>
                        مسدود
                      </span>
                    )}
                  </div>
                  <div className="text-[12px] mt-1 flex items-center gap-2 flex-wrap"
                    style={{ color: "var(--muted)" }}>
                    <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>{u.tg_id}</span>
                    {u.phone && (
                      <>
                        <span style={{ opacity: 0.4 }}>•</span>
                        <span dir="ltr" style={{ fontFamily: "var(--mono)" }}>{u.phone}</span>
                      </>
                    )}
                    {u.ordersCount > 0 && (
                      <>
                        <span style={{ opacity: 0.4 }}>•</span>
                        <span>{faNum(u.ordersCount)} خرید · {faNum(u.spent)} تومان</span>
                      </>
                    )}
                  </div>
                  </div>
                </button>
                <div className="flex items-center gap-3 text-[13px] shrink-0">
                  {!!u.coins && <span style={{ color: "var(--warn)" }}>{faNum(u.coins)} سکه</span>}
                  {!!u.balance && <span style={{ color: "var(--ok)" }}>{faNum(u.balance)}</span>}
                  <button onClick={() => setMsgTo(u)} className="fx-ico-btn"
                    title="پیام به این کاربر" style={{ width: 30, height: 30 }}>
                    <Send size={13} />
                  </button>
                  <button onClick={() => setDetail(u.tg_id)} className="fx-ico-btn"
                    title="پرونده‌ی کاربر" style={{ width: 30, height: 30 }}>
                    <ChevronLeft size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between gap-3 flex-wrap">
            <span className="text-[13px]" style={{ color: "var(--muted)" }}>
              {faNum(offset + 1)}–{faNum(Math.min(offset + PAGE, d.total))} از {faNum(d.total)}
            </span>
            {pages > 1 && (
              <div className="flex items-center gap-2">
                <button onClick={() => go(Math.max(0, offset - PAGE))} disabled={offset === 0}
                  className="fx-btn-g px-3 py-2 text-[13px]">قبلی</button>
                <span className="text-[13px]" style={{ color: "var(--dim)" }}>
                  {faNum(page)} از {faNum(pages)}
                </span>
                <button onClick={() => go(offset + PAGE)} disabled={offset + PAGE >= d.total}
                  className="fx-btn-g px-3 py-2 text-[13px]">بعدی</button>
              </div>
            )}
          </div>
        </>
      )}

      {detail && (
        <SubscriberModal tgId={detail} password={password} onClose={() => setDetail(null)}
          onMessage={(u) => { setDetail(null); setMsgTo(u); }} />
      )}
      {msgTo && (
        <MessageUserModal user={msgTo} password={password} onClose={() => setMsgTo(null)} />
      )}
    </div>
  );
}

export function MessageUserModal({ user, password, onClose }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const name = user.first_name || user.tg_id;

  const send = async () => {
    if (!text.trim()) return;
    setBusy(true); setMsg(null);
    try {
      const res = await fetch(`${API_URL}/api/admin/bot/message/${user.tg_id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ text }),
      });
      const j = await res.json().catch(() => ({}));
      if (res.ok) {
        setMsg({ t: "ok", m: "پیام فرستاده شد" });
        setText("");
        setTimeout(onClose, 1200);
      } else {
        setMsg({ t: "err", m: errText(j.detail, "ارسال ناموفق بود") });
      }
    } catch {
      setMsg({ t: "err", m: "اتصال برقرار نشد" });
    } finally { setBusy(false); }
  };

  return (
    <Modal title={`پیام به ${name}`} onClose={onClose} width="480px"
      footer={
        <div className="flex items-center justify-between gap-3 w-full">
          <span className="text-[12px]" style={{ color: "var(--muted)" }}>
            از طرف ربات، با عنوان «پیام از پشتیبانی» فرستاده می‌شود
          </span>
          <button onClick={send} disabled={busy || !text.trim()}
            className="fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5 shrink-0">
            {busy ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />} ارسال
          </button>
        </div>
      }>
      <Msg msg={msg} />
      <textarea className="fx-input" rows={6} value={text} autoFocus
        onChange={(e) => setText(e.target.value)}
        placeholder="سلام! درباره‌ی سفارشتان تماس می‌گیرم…"
        style={{ resize: "vertical", lineHeight: 1.8 }} />
      <div className="text-[12px] mt-2 flex items-center justify-between"
        style={{ color: "var(--muted)" }}>
        <span>{faNum(text.length)} از ۳۵۰۰ کاراکتر</span>
        {user.username && <span dir="ltr">@{user.username}</span>}
      </div>
      <InfoBox>
        اگر کاربر ربات را بلاک کرده باشد، پیام نمی‌رسد و همین‌جا به شما گفته می‌شود.
      </InfoBox>
    </Modal>
  );
}

export function SubscriberModal({ tgId, password, onClose, onMessage }) {
  const [d, setD] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/admin/bot/subscriber/${tgId}`, {
          headers: { "X-Admin-Password": password },
        });
        const body = await res.json();
        if (res.ok) setD(body);
        else setErr(errText(body.detail, "دریافت اطلاعات ناموفق بود"));
      } catch { setErr("اتصال به سرور برقرار نشد"); }
      finally { setLoading(false); }
    })();
  }, [tgId, password]);

  const u = d?.user || {};
  const subs = d?.subscriptions || [];
  const live = d?.live || {};

  return createPortal(
    <div className="nx-modal-wrap fx-fade"
      style={{ background: "rgba(3,6,12,.84)", backdropFilter: "blur(6px)" }}
      onClick={onClose}>
      <div className="w-full max-w-2xl rounded-2xl fx-scale nx-modal flex flex-col"
        onClick={(e) => e.stopPropagation()}
        style={{ background: "var(--surface)", border: "1px solid rgba(90,169,230,.3)" }}>

        <div className="p-5 shrink-0 flex items-start justify-between gap-3"
          style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[16px] font-bold text-white">
                {u.first_name || "بدون نام"}
              </span>
              {u.username && (
                <span className="text-[13px]" dir="ltr" style={{ color: "var(--muted)" }}>
                  @{u.username}
                </span>
              )}
              {u.is_blocked === 1 && (
                <span className="fx-pill" style={{ background: "rgba(248,113,113,.12)", color: "var(--danger)" }}>
                  مسدود
                </span>
              )}
            </div>
            <div className="text-[12px] mt-1.5" dir="ltr"
              style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
              {u.tg_id}{u.phone ? ` · ${u.phone}` : ""}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {onMessage && u.tg_id && (
              <button onClick={() => onMessage(u)}
                className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
                <Send size={13} /> پیام
              </button>
            )}
            <button title="بستن" onClick={onClose} className="fx-ico-btn"><X size={16} /></button>
          </div>
        </div>

        <div className="p-5 overflow-y-auto flex-1" style={{ minHeight: 0 }}>
          {loading && (
            <PageSkeleton />
          )}

          {err && (
            <div className="rounded-xl p-3 flex items-center gap-2 text-[13px]"
              style={{ background: "rgba(248,113,113,.1)", border: "1px solid rgba(248,113,113,.3)", color: "var(--danger)" }}>
              <AlertTriangle size={14} /> {err}
            </div>
          )}

          {d && (
            <>
              {/* خلاصه */}
              <div className="fx-g3 grid grid-cols-3 gap-3 mb-5">
                {[
                  ["سکه", u.coins || 0, "var(--warn)"],
                  ["کیف پول", Number(u.balance || 0).toLocaleString("fa-IR"), "var(--ok)"],
                  ["خرید موفق", (d.orders || []).filter((o) => o.status === "approved").length, "var(--accent-2)"],
                ].map(([l, v, c2], i) => (
                  <div key={i} className="rounded-xl p-3 text-center"
                    style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
                    <div className="text-[18px] font-bold" style={{ color: c2, fontFamily: "var(--mono)" }}>{v}</div>
                    <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>{l}</div>
                  </div>
                ))}
              </div>

              {/* اشتراک‌ها */}
              <div className="text-[14px] font-semibold text-white mb-3">
                اشتراک‌ها
                {!d.liveAvailable && subs.length > 0 && (
                  <span className="text-[12px] font-normal mr-2" style={{ color: "var(--warn)" }}>
                    · داده زنده در دسترس نیست
                  </span>
                )}
              </div>

              {subs.length === 0 && (
                <div className="text-center py-6 text-[13px]" style={{ color: "var(--muted)" }}>
                  اشتراکی ندارد
                </div>
              )}

              {subs.map((s) => {
                const lv = live[s.client_email];
                const used = lv ? (lv.up || 0) + (lv.down || 0) : 0;
                const total = lv?.total || 0;
                const pct = total > 0 ? Math.min(100, Math.round(used * 100 / total)) : 0;
                const dl = lv?.expiryTime ? daysLeft(lv.expiryTime) : null;
                const near = dl !== null && dl <= 3;

                return (
                  <div key={s.id} className="fx-card p-4 mb-3" style={{ background: "var(--surface-3)" }}>
                    <div className="flex items-center justify-between gap-2 mb-3 flex-wrap">
                      <div className="flex items-center gap-2">
                        <Package size={14} style={{ color: "var(--accent-2)" }} />
                        <span className="text-[14px] font-semibold text-white">
                          {s.plan_name || "اشتراک"}
                        </span>
                      </div>
                      <span className="fx-pill" style={{
                        background: s.is_active ? "rgba(52,211,153,.12)" : "rgba(255,255,255,.05)",
                        color: s.is_active ? "var(--ok)" : "var(--muted)",
                      }}>
                        {s.is_active ? "فعال" : "غیرفعال"}
                      </span>
                    </div>

                    <div className="text-[12px] mb-3" dir="ltr"
                      style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                      {s.client_email}
                    </div>

                    {lv ? (
                      <>
                        <div className="flex justify-between mb-2">
                          <span className="text-[13px]" style={{ color: "var(--dim)" }}>مصرف حجم</span>
                          <span className="text-[13px] font-bold"
                            style={{ color: "var(--accent-2)", fontFamily: "var(--mono)" }}>
                            {fmtBytes(used)} {total > 0
                              ? `/ ${fmtBytes(total)}`
                              : <span className="fx-fa-sub">· نامحدود</span>}
                          </span>
                        </div>

                        {total > 0 && (
                          <div className="h-[8px] rounded-full overflow-hidden mb-3"
                            style={{ background: "rgba(43,127,214,.12)" }}>
                            <div style={{
                              width: `${pct}%`, height: "100%", borderRadius: 99,
                              background: pct >= 85
                                ? "linear-gradient(90deg,var(--danger),#FCA5A5)"
                                : "linear-gradient(90deg,var(--accent),var(--accent-2))",
                            }} />
                          </div>
                        )}

                        <div className="grid grid-cols-3 gap-2 mb-3">
                          {[
                            ["دانلود", fmtBytes(lv.down), "var(--ok)"],
                            ["آپلود", fmtBytes(lv.up), "var(--warn)"],
                            ["باقی", total > 0 ? fmtBytes(Math.max(0, total - used)) : "∞", "var(--accent-2)"],
                          ].map(([l, v, c2], i) => (
                            <div key={i} className="text-center">
                              <div className="text-[11.5px]" style={{ color: "var(--muted)" }}>{l}</div>
                              <div className="text-[13px] font-bold mt-0.5"
                                style={{ color: c2, fontFamily: "var(--mono)" }}>{v}</div>
                            </div>
                          ))}
                        </div>

                        <div className="flex justify-between text-[13px] pt-2"
                          style={{ borderTop: "1px solid var(--border)" }}>
                          <span style={{ color: "var(--muted)" }}>انقضا</span>
                          <span style={{ color: near ? "var(--warn)" : "var(--dim)" }}>
                            {fmtDate(lv.expiryTime)}
                            {dl !== null && (dl > 0 ? ` · ${dl} روز مانده` : " · منقضی شده")}
                          </span>
                        </div>
                      </>
                    ) : (
                      <div className="text-[13px] py-2" style={{ color: "var(--muted)" }}>
                        داده‌ی زنده از 3x-ui دریافت نشد — اتصال پنل را بررسی کنید
                      </div>
                    )}
                  </div>
                );
              })}

              {/* آخرین سفارش‌ها */}
              {(d.orders || []).length > 0 && (
                <>
                  <div className="text-[14px] font-semibold text-white mt-5 mb-3">آخرین سفارش‌ها</div>
                  {(d.orders || []).slice(0, 6).map((o) => (
                    <div key={o.id} className="flex items-center justify-between gap-2 py-2.5"
                      style={{ borderBottom: "1px solid var(--border)" }}>
                      <div className="min-w-0">
                        <div className="text-[13px]" style={{ color: "var(--dim)" }}>
                          {o.plan_name || "—"}
                        </div>
                        <div className="text-[12px] mt-0.5"
                          style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                          #{o.id} · {String(o.created_at || "").slice(0, 10)}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-[13px]" style={{ color: "var(--dim)" }}>
                          {Number(o.amount || 0).toLocaleString("fa-IR")}
                        </span>
                        <StatusPill s={o.status} />
                      </div>
                    </div>
                  ))}
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}
