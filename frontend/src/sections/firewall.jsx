/**
 * فایروال.
 *
 * از App.jsx جدا شد؛ آن فایل ۱۱۴۰۰ خط بود و پیداکردن یک کامپوننت
 * در آن عملاً ناممکن.
 */
import React, { useState, useEffect, useCallback } from "react";
import {
  AlertTriangle, ChevronDown, Loader2, Plus, Search, ShieldCheck, Sparkles, Trash2, XCircle,
} from "lucide-react";
import { API_URL } from "../lib/constants";
import { errText, esc0, faNum } from "../lib/format";
import { ConfirmModal, EmptyState, Field, InfoBox, Msg, SectionHead } from "../ui/index";

export const FW_ACTIONS = [
  ["allow", "اجازه", "var(--ok)"],
  ["deny", "مسدود", "var(--danger)"],
  ["limit", "محدود", "var(--warn)"],
];

export function useFirewall(password) {
  const [d, setD] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API_URL}/api/admin/firewall`, {
        headers: { "X-Admin-Password": password },
      }).then((x) => x.json());
      setD(r);
    } catch { setD({ ready: false, error: "اتصال به سرور برقرار نشد", rules: [] }); }
  }, [password]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (msg) { const t = setTimeout(() => setMsg(null), 5000); return () => clearTimeout(t); } }, [msg]);

  const call = async (path, opts = {}) => {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}${path}`, {
        ...opts,
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Password": password, ...(opts.headers || {}),
        },
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) { setMsg({ t: "err", m: errText(j.detail, "عملیات ناموفق") }); return null; }
      setMsg({ t: "ok", m: j.note || "انجام شد" });
      if (j.rules) setD(j); else await load();
      return j;
    } catch {
      setMsg({ t: "err", m: "اتصال برقرار نشد" });
      return null;
    } finally { setBusy(false); }
  };

  return { d, busy, msg, setMsg, load, call };
}

/**
 * پیشنهاد قواعد بر اساس چیزی که واقعاً روی سرور گوش می‌دهد.
 *
 * مدیر نباید از حفظ بداند کدام پورت لازم است. این بخش سرویس‌های در
 * حال اجرا را می‌خواند و برای هرکدام می‌گوید باید باز بماند یا بسته
 * شود — و چرا. هیچ‌چیز بدون تیک‌زدن و تایید اعمال نمی‌شود.
 */
export function FirewallSuggest({ password, onApplied }) {
  const [d, setD] = useState(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [picked, setPicked] = useState({});
  const [open, setOpen] = useState(false);

  const load = async () => {
    setBusy(true);
    try {
      const j = await fetch(`${API_URL}/api/admin/firewall/suggest`, {
        headers: { "X-Admin-Password": password },
      }).then((r) => r.json());
      setD(j);
      // پیش‌فرض: همه‌ی پیشنهادهای «ببند» تیک می‌خورند، چون همان‌ها
      // دلیل وجود این بخش‌اند. «باز بماند» تیک نمی‌خورد تا کسی
      // ناخواسته دری را که بسته بوده باز نکند.
      const p = {};
      (j.close || []).forEach((x) => { p[`${x.port}/${x.proto}`] = true; });
      setPicked(p);
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setBusy(false); }
  };

  useEffect(() => { if (open && !d) load(); }, [open]);
  useEffect(() => { if (msg) { const t = setTimeout(() => setMsg(null), 5000); return () => clearTimeout(t); } }, [msg]);

  const all = [...((d && d.close) || []), ...((d && d.keep) || [])];
  const chosen = all.filter((x) => picked[`${x.port}/${x.proto}`]);

  const apply = async () => {
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/firewall/apply-plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Password": password },
        body: JSON.stringify({ confirm: true, rules: chosen }),
      });
      const j = await res.json().catch(() => ({}));
      if (res.ok) {
        setMsg({ t: "ok", m: j.note || "اعمال شد" });
        await load();
        onApplied && onApplied();
      } else setMsg({ t: "err", m: errText(j.detail, "اعمال ناموفق") });
    } catch { setMsg({ t: "err", m: "اتصال برقرار نشد" }); }
    finally { setBusy(false); }
  };

  const Row = ({ x, tone }) => {
    const key = `${x.port}/${x.proto}`;
    const on = !!picked[key];
    const col = tone === "close" ? "var(--danger)" : "var(--ok)";
    return (
      <label className="flex items-start gap-3 p-3 rounded-xl mb-2 cursor-pointer"
        style={{
          background: on ? "var(--accent-soft)" : "var(--surface-3)",
          border: `1px solid ${on ? "var(--accent-2)" : "var(--border)"}`,
        }}>
        <input type="checkbox" checked={on} style={{ accentColor: "var(--accent)", marginTop: 3 }}
          onChange={(e) => setPicked({ ...picked, [key]: e.target.checked })} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span style={{ fontFamily: "var(--mono)", fontWeight: 600 }}>{x.port}</span>
            <span className="text-[12px]" style={{ color: "var(--muted)" }}>{x.proto}</span>
            {x.process && (
              <span dir="ltr" className="text-[12px]" style={{ color: "var(--dim)" }}>{esc0(x.process)}</span>
            )}
            <span className="fx-pill" style={{ background: "rgba(255,255,255,.04)", color: col }}>
              {tone === "close" ? "ببند" : "باز بماند"}
            </span>
          </div>
          <div className="text-[12px] mt-1 leading-relaxed" style={{ color: "var(--muted)" }}>
            {esc0(x.why)}
          </div>
        </div>
      </label>
    );
  };

  return (
    <div className="fx-card p-5 mb-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="text-[14px] font-semibold text-white flex items-center gap-2">
          <Sparkles size={15} style={{ color: "var(--accent-2)" }} /> پیشنهاد قواعد
        </div>
        <button onClick={() => setOpen(!open)} disabled={busy}
          className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5">
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Search size={13} />}
          {open ? "بستن" : "سرور را بررسی کن"}
          <ChevronDown size={13} style={open ? { transform: "rotate(180deg)" } : undefined} />
        </button>
      </div>
      <p className="text-[13px] mt-1" style={{ color: "var(--muted)" }}>
        می‌بیند چه سرویس‌هایی روی سرور گوش می‌دهند و می‌گوید کدام باید باز
        بماند و کدام مشکوک است — با دلیل هرکدام.
      </p>

      {open && (
        <>
          <Msg msg={msg} />

          {!d ? (
            <div className="flex justify-center py-8">
              <Loader2 className="animate-spin" style={{ color: "var(--muted)" }} />
            </div>
          ) : (
            <div className="mt-3">
              {d.close?.length > 0 && (
                <>
                  <div className="text-[13px] mb-2" style={{ color: "var(--danger)" }}>
                    رو به اینترنت باز است و به سرویس شما ربطی ندارد
                  </div>
                  {d.close.map((x) => <Row key={`c${x.port}${x.proto}`} x={x} tone="close" />)}
                </>
              )}

              {d.keep?.length > 0 && (
                <>
                  <div className="text-[13px] mt-4 mb-2" style={{ color: "var(--ok)" }}>
                    باید باز بماند
                  </div>
                  {d.keep.map((x) => <Row key={`k${x.port}${x.proto}`} x={x} tone="keep" />)}
                </>
              )}

              {d.already?.length > 0 && (
                <div className="mt-4 pt-3" style={{ borderTop: "1px solid var(--border)" }}>
                  <div className="text-[13px] mb-2" style={{ color: "var(--muted)" }}>
                    از قبل قاعده دارند
                  </div>
                  <div className="flex gap-1.5 flex-wrap">
                    {d.already.map((a) => (
                      <span key={`a${a.port}`} className="fx-pill"
                        style={{ background: "var(--surface-3)", color: "var(--dim)" }}>
                        <span style={{ fontFamily: "var(--mono)" }}>{a.port}</span>
                        {" · "}{esc0(a.action)}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {!d.close?.length && !d.keep?.length && (
                <EmptyState icon={ShieldCheck}
                  text="هر پورتِ رو به اینترنت از قبل قاعده دارد — چیزی برای پیشنهاد نیست" />
              )}

              {all.length > 0 && (
                <>
                  <InfoBox tone={chosen.some((x) => x.action === "deny") ? "warn" : "info"}>
                    {chosen.length === 0
                      ? "چیزی انتخاب نشده."
                      : <>‌<b>{faNum(chosen.length)}</b> قاعده اعمال می‌شود. قبل از تایید
                         مطمئن شوید پورتی که استفاده می‌کنید در فهرست «ببند» نیست.</>}
                  </InfoBox>
                  <button onClick={apply} disabled={busy || chosen.length === 0}
                    className="fx-btn w-full mt-3 py-2.5 text-[13px] flex items-center justify-center gap-1.5">
                    {busy ? <Loader2 size={14} className="animate-spin" /> : <ShieldCheck size={14} />}
                    اعمال {faNum(chosen.length)} قاعده
                  </button>
                </>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function FirewallRules({ password }) {
  const { d, busy, msg, call, load } = useFirewall(password);
  const [form, setForm] = useState({ port: "", proto: "tcp", action: "allow", comment: "" });
  const [confirmSsh, setConfirmSsh] = useState(false);
  const [q, setQ] = useState("");
  const [act, setAct] = useState("all");
  const [only, setOnly] = useState("all");
  const [confirmDel, setConfirmDel] = useState(null);

  if (!d) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  if (!d.installed) {
    return (
      <div className="fx-anim">
        <SectionHead title="فایروال" desc="کنترل اینکه چه کسی از بیرون به سرور دسترسی دارد." />
        <div className="fx-card p-5">
          <div className="text-[14px] font-semibold text-white mb-2 flex items-center gap-2">
            <AlertTriangle size={15} style={{ color: "var(--warn)" }} /> ufw نصب نیست
          </div>
          <p className="text-[13px] leading-relaxed" style={{ color: "var(--dim)" }}>
            این صفحه با <b>ufw</b> کار می‌کند که روی اوبونتو و دبیان استاندارد است.
            روی سرور اجرا کنید و صفحه را تازه کنید:
          </p>
          <div className="mt-3 rounded-xl p-3.5" style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
            <code dir="ltr" className="text-[13px]" style={{ fontFamily: "var(--mono)", color: "var(--accent-2)" }}>
              apt update &amp;&amp; apt install -y ufw
            </code>
          </div>
          <InfoBox tone="warn">
            بعد از نصب، <b>قبل از روشن‌کردن فایروال</b> حتماً قاعده‌ی SSH را اضافه کنید،
            وگرنه دسترسی خودتان به سرور قطع می‌شود.
          </InfoBox>
        </div>
      </div>
    );
  }

  // ufw هر قاعده را دو بار می‌آورد: یک‌بار IPv4 و یک‌بار (v6). نمایش
  // هر دو یعنی فهرست دو برابر بدون یک ذره اطلاعات بیشتر — و همین
  // اصلی‌ترین دلیل شلوغیِ این صفحه بود. ادغامشان می‌کنیم و در ستون
  // مبدأ می‌نویسیم که قاعده هر دو نسخه را می‌گیرد.
  const merged = [];
  const seen = new Map();
  for (const r of (d.rules || [])) {
    const key = `${r.target}|${r.action}|${(r.source || "").replace(" (v6)", "")}`;
    const prev = seen.get(key);
    if (prev) {
      prev.both = true;
      prev.nums.push(r.num);
      continue;
    }
    const copy = { ...r, nums: [r.num], both: false,
                   source: (r.source || "").replace(" (v6)", "") };
    seen.set(key, copy);
    merged.push(copy);
  }

  const rules = merged.filter((r) => {
    if (act !== "all" && r.action.toLowerCase() !== act) return false;
    if (only === "critical" && !r.critical) return false;
    if (only === "open" && r.action.toLowerCase() !== "allow") return false;
    if (!q.trim()) return true;
    const s = q.trim().toLowerCase();
    return `${r.target} ${r.source} ${r.action} ${r.note || ""}`
      .toLowerCase().includes(s);
  });

  const hidden = merged.length - rules.length;
  const dupes = (d.rules || []).length - merged.length;

  const add = () => {
    if (!form.port) return;
    call("/api/admin/firewall/rule", {
      method: "POST", body: JSON.stringify(form),
    }).then((j) => { if (j) setForm({ ...form, port: "", comment: "" }); });
  };

  return (
    <div className="fx-anim">
      <SectionHead title="قواعد فایروال"
        desc="هر قاعده یک در است که باز یا بسته می‌گذارید. چیزی که لازم ندارید را ببندید."
        action={
          <div className="flex items-center gap-2">
            <span className="fx-pill" style={{
              background: d.active ? "rgba(52,211,153,.14)" : "rgba(248,113,113,.14)",
              color: d.active ? "var(--ok)" : "var(--danger)",
            }}>
              {d.active ? "روشن" : "خاموش"}
            </span>
            <button
              onClick={() => call("/api/admin/firewall/toggle", {
                method: "POST",
                body: JSON.stringify({ enable: !d.active, confirmSsh }),
              })}
              disabled={busy}
              className={d.active ? "fx-btn-g px-4 py-2.5 text-[13px]" : "fx-btn px-4 py-2.5 text-[13px]"}>
              {busy ? <Loader2 size={14} className="animate-spin" /> : (d.active ? "خاموش کن" : "روشن کن")}
            </button>
          </div>
        } />

      <Msg msg={msg} />

      <FirewallSuggest password={password} onApplied={load} />

      {!d.active && (
        <div className="fx-card p-5 mb-4" style={{ borderColor: "rgba(251,191,36,.3)" }}>
          <div className="text-[14px] font-semibold mb-2 flex items-center gap-2" style={{ color: "var(--warn)" }}>
            <AlertTriangle size={15} /> فایروال خاموش است
          </div>
          <p className="text-[13px] leading-relaxed" style={{ color: "var(--dim)" }}>
            یعنی همه‌ی پورت‌های باز سرور از تمام اینترنت در دسترس‌اند.
          </p>
          {!d.sshProtected && (
            <>
              <InfoBox tone="warn">
                <b>هیچ قاعده‌ای پورت ۲۲ (SSH) را باز نگذاشته.</b> اگر همین حالا
                فایروال را روشن کنید، دسترسی خودتان به سرور قطع می‌شود و فقط از
                کنسول ارائه‌دهنده می‌توانید برگردید. اول قاعده‌ی SSH را اضافه کنید.
              </InfoBox>
              <label className="flex items-center gap-2 text-[13px] cursor-pointer mt-3" style={{ color: "var(--dim)" }}>
                <input type="checkbox" checked={confirmSsh}
                  onChange={(e) => setConfirmSsh(e.target.checked)}
                  style={{ accentColor: "var(--warn)" }} />
                می‌دانم و با همین وضع روشن کن
              </label>
            </>
          )}
        </div>
      )}

      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-3 flex items-center gap-2">
          <Plus size={15} style={{ color: "var(--accent-2)" }} /> قاعده‌ی جدید
        </div>
        <div className="fx-g4 grid grid-cols-4 gap-3">
          <Field label="پورت">
            <input className="fx-input" dir="ltr" type="number" min="1" max="65535"
              value={form.port} placeholder="۴۴۳"
              onChange={(e) => setForm({ ...form, port: e.target.value })}
              style={{ fontFamily: "var(--mono)" }} />
          </Field>
          <Field label="پروتکل">
            <select className="fx-input" value={form.proto}
              onChange={(e) => setForm({ ...form, proto: e.target.value })}>
              <option value="tcp">TCP</option>
              <option value="udp">UDP</option>
              <option value="any">هر دو</option>
            </select>
          </Field>
          <Field label="عمل">
            <select className="fx-input" value={form.action}
              onChange={(e) => setForm({ ...form, action: e.target.value })}>
              {FW_ACTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </Field>
          <Field label="توضیح" hint="اختیاری">
            <input className="fx-input" value={form.comment} placeholder="پنل"
              onChange={(e) => setForm({ ...form, comment: e.target.value })} />
          </Field>
        </div>
        <button onClick={add} disabled={busy || !form.port}
          className="fx-btn px-4 py-2.5 text-[13px] flex items-center gap-1.5 mt-3">
          <Plus size={14} /> افزودن قاعده
        </button>
      </div>

      <div className="fx-card p-5">
        <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
          <div className="text-[14px] font-semibold text-white flex items-center gap-2">
            <ShieldCheck size={15} style={{ color: "var(--accent-2)" }} /> قواعد فعلی
            <span className="text-[13px] font-normal" style={{ color: "var(--muted)" }}>
              ({faNum(rules.length)})
            </span>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <select className="fx-input" value={act} style={{ width: 120 }}
              onChange={(e) => setAct(e.target.value)}>
              <option value="all">همه‌ی عمل‌ها</option>
              {FW_ACTIONS.map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
            <select className="fx-input" value={only} style={{ width: 140 }}
              onChange={(e) => setOnly(e.target.value)}>
              <option value="all">همه‌ی قواعد</option>
              <option value="open">فقط درهای باز</option>
              <option value="critical">فقط حیاتی</option>
            </select>
            <div className="fx-search" style={{ width: 180 }}>
              <Search size={14} style={{ color: "var(--muted)" }} />
              <input value={q} onChange={(e) => setQ(e.target.value)}
                placeholder="جستجو..." />
            </div>
          </div>
        </div>

        {(dupes > 0 || hidden > 0) && (
          <div className="text-[12px] mb-3 flex items-center gap-3 flex-wrap"
            style={{ color: "var(--muted)" }}>
            {dupes > 0 && (
              <span>{faNum(dupes)} قاعده‌ی تکراری IPv6 با نسخه‌ی IPv4 ادغام شد</span>
            )}
            {hidden > 0 && (
              <button onClick={() => { setAct("all"); setOnly("all"); setQ(""); }}
                style={{ color: "var(--accent-2)" }}>
                {faNum(hidden)} قاعده با فیلتر پنهان است — نمایش همه
              </button>
            )}
          </div>
        )}

        {!rules.length ? (
          <EmptyState icon={ShieldCheck}
            text={q || act !== "all" || only !== "all"
              ? "با این فیلتر چیزی نیست" : "هنوز قاعده‌ای ثبت نشده"} />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="fx-table">
              <thead>
                <tr><th>#</th><th>مقصد</th><th>عمل</th><th>مبدأ</th><th></th></tr>
              </thead>
              <tbody>
                {rules.map((r) => {
                  const meta = FW_ACTIONS.find(([v]) => v === r.action.toLowerCase());
                  return (
                    <tr key={r.num}>
                      <td style={{ fontFamily: "var(--mono)", color: "var(--muted)" }}>{faNum(r.num)}</td>
                      <td dir="ltr" style={{ fontFamily: "var(--mono)" }}>
                        {r.target}
                        {r.critical && (
                          <span className="fx-pill mr-2" style={{ background: "rgba(251,191,36,.14)", color: "var(--warn)" }}>
                            حیاتی
                          </span>
                        )}
                      </td>
                      <td style={{ color: meta ? meta[2] : "var(--dim)" }}>
                        {meta ? meta[1] : r.action}
                      </td>
                      <td dir="ltr" style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                        {r.source}
                        {r.both && (
                          <span className="fx-pill mr-2" style={{
                            background: "var(--surface-3)", color: "var(--muted)",
                          }}>IPv4 + IPv6</span>
                        )}
                      </td>
                      <td>
                        <button onClick={() => setConfirmDel(r)} disabled={busy}
                          className="fx-ico-btn" aria-label={`حذف قاعده ${r.num}`}
                          style={{ width: 30, height: 30 }}>
                          <Trash2 size={13} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {r_note(d)}
      </div>

      {confirmDel && (
        <ConfirmModal
          title={`حذف قاعده #${faNum(confirmDel.num)}؟`}
          desc={confirmDel.critical
            ? `${confirmDel.note} — حذفش می‌تواند دسترسی شما به سرور را قطع کند.`
            : `قاعده‌ی ${confirmDel.target} (${confirmDel.action}) حذف می‌شود.`}
          confirmLabel="حذف کن"
          onCancel={() => setConfirmDel(null)}
          onConfirm={() => {
            call(`/api/admin/firewall/rule/${confirmDel.num}?confirm=1`,
                 { method: "DELETE" });
            setConfirmDel(null);
          }} />
      )}
    </div>
  );
}

/** یادداشت پایین جدول قواعد — وضعیت پیش‌فرض ورودی. */
export function r_note(d) {
  if (!d?.defaultIncoming || d.defaultIncoming === "?") return null;
  const deny = d.defaultIncoming === "deny";
  return (
    <div className="text-[13px] mt-3 pt-3 leading-relaxed"
      style={{ borderTop: "1px solid var(--border)", color: "var(--muted)" }}>
      سیاست پیش‌فرض ورودی: <b style={{ color: deny ? "var(--ok)" : "var(--warn)" }}>
        {deny ? "مسدود" : "باز"}
      </b>
      {deny
        ? " — یعنی هرچه در فهرست بالا نیست، بسته است. این حالت درست است."
        : " — یعنی هر پورتی که قاعده‌ی مسدود ندارد، باز است."}
    </div>
  );
}

export function FirewallBlocked({ password }) {
  const { d, busy, msg, call } = useFirewall(password);
  const [ip, setIp] = useState("");

  if (!d) return <div className="flex justify-center py-16"><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  const blocked = (d.rules || []).filter(
    (r) => r.action === "DENY" && r.source && r.source !== "Anywhere");

  return (
    <div className="fx-anim">
      <SectionHead title="آی‌پی‌های بسته‌شده"
        desc="آی‌پی‌هایی که کامل از سرور کنار گذاشته شده‌اند." />

      <Msg msg={msg} />

      <div className="fx-card p-5 mb-4">
        <div className="text-[14px] font-semibold text-white mb-3 flex items-center gap-2">
          <XCircle size={15} style={{ color: "var(--danger)" }} /> بستن یک آی‌پی
        </div>
        <div className="flex gap-2 flex-wrap items-end">
          <div className="flex-1" style={{ minWidth: 200 }}>
            <Field label="آدرس آی‌پی" hint="مثلاً ۹۱٫۹۹٫۱۲٫۴ یا یک رنج مثل 91.99.12.0/24">
              <input className="fx-input" dir="ltr" value={ip}
                onChange={(e) => setIp(e.target.value)} placeholder="91.99.12.4"
                style={{ fontFamily: "var(--mono)" }} />
            </Field>
          </div>
          <button
            onClick={() => call("/api/admin/firewall/block-ip", {
              method: "POST", body: JSON.stringify({ ip }),
            }).then((j) => { if (j) setIp(""); })}
            disabled={busy || !ip.trim()}
            className="fx-btn px-4 py-2.5 text-[13px] flex items-center gap-1.5">
            <XCircle size={14} /> ببند
          </button>
        </div>
        {!d.active && (
          <InfoBox tone="warn">
            فایروال خاموش است، پس این قاعده‌ها فعلاً اثری ندارند. از صفحه‌ی
            «قواعد فایروال» روشنش کنید.
          </InfoBox>
        )}
      </div>

      <div className="fx-card p-5">
        <div className="text-[14px] font-semibold text-white mb-3 flex items-center gap-2">
          <XCircle size={15} style={{ color: "var(--muted)" }} /> فهرست بسته‌شده‌ها
          <span className="text-[13px] font-normal" style={{ color: "var(--muted)" }}>
            ({faNum(blocked.length)})
          </span>
        </div>
        {!blocked.length ? (
          <EmptyState icon={ShieldCheck} text="هیچ آی‌پی‌ای بسته نشده" />
        ) : blocked.map((r) => (
          <div key={r.num} className="flex items-center justify-between gap-3 p-3 rounded-xl mb-2"
            style={{ background: "var(--surface-3)", border: "1px solid var(--border)" }}>
            <span dir="ltr" className="text-[13px]" style={{ fontFamily: "var(--mono)", color: "var(--dim)" }}>
              {r.source}
            </span>
            <button
              onClick={() => call("/api/admin/firewall/block-ip", {
                method: "POST",
                body: JSON.stringify({ ip: r.source, unblock: true }),
              })}
              disabled={busy}
              className="fx-btn-g px-3 py-2 text-[13px]">
              باز کن
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
