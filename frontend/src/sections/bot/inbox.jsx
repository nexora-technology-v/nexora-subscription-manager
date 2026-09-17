/**
 * صندوق پیام — سمتِ مالک، به شکلِ یک پیام‌رسان.
 *
 * چرا این شکل و نه یک فهرستِ ساده: این صفحه جایی است که مالک با
 * مشتریِ عصبانی حرف می‌زند. هر چیزی که در تلگرام عادت دارد و این‌جا
 * نباشد، یک لحظه مکث می‌سازد — و مکثِ آن لحظه یعنی جوابِ دیرتر.
 *
 * پس: دو ستونِ تمام‌قد، جست‌وجو در گفتگوها، جداکننده‌ی تاریخ،
 * گروه‌شدنِ پیام‌های پشت‌سرهم، ساعت روی هر پیام، و نشانِ خوانده‌شدن.
 *
 * خبرهای خودکار (تایید/ردِ رسید) با `sender='system'` در همین
 * گفتگو می‌نشینند، پس مالک دقیقاً همان چیزی را می‌بیند که مشتری
 * دیده — نه یک روایتِ جدا.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle, ArrowDown, Check, CheckCheck, Loader2, MessageCircle,
  RefreshCw, Search, Send, Shield,
} from "lucide-react";

import { API_URL } from "../../lib/constants";
import { errText, faNum, toFaDigits } from "../../lib/format";
import { Avatar, EmptyState, PageSkeleton, SectionHead } from "../../ui/index";

async function call(path, password, opt = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    method: opt.method || "GET",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Password": password || "",
    },
    ...(opt.body ? { body: JSON.stringify(opt.body) } : {}),
  });
  const j = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(errText(j.detail, "درخواست ناموفق بود"));
  return j;
}

/* ── زمان ──
   ساعت روی پیام، و روزِ آن بالای گروه. تاریخِ کامل روی هر پیام،
   ستونِ باریکی می‌سازد که چشم مجبور است از رویش رد شود. */

const clock = (at) => {
  const s = String(at || "");
  const hm = s.slice(11, 16);
  return hm ? toFaDigits(hm) : "";
};

const dayKey = (at) => String(at || "").slice(0, 10);

function dayLabel(key) {
  if (!key) return "";
  const today = new Date().toISOString().slice(0, 10);
  const y = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
  if (key === today) return "امروز";
  if (key === y) return "دیروز";
  try {
    return new Date(key + "T00:00:00").toLocaleDateString("fa-IR");
  } catch { return toFaDigits(key); }
}

export function BotInboxSection({ password }) {
  const [threads, setThreads] = useState(null);
  const [open, setOpen] = useState(null);
  const [msgs, setMsgs] = useState(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [q, setQ] = useState("");
  const [atEnd, setAtEnd] = useState(true);

  const logRef = useRef(null);
  const endRef = useRef(null);
  const boxRef = useRef(null);

  const loadThreads = useCallback(async () => {
    setErr("");
    try {
      const j = await call("/api/admin/bot/inbox", password);
      setThreads(j.threads || []);
    } catch (e) { setErr(e.message); setThreads([]); }
  }, [password]);

  const loadThread = useCallback(async (uid) => {
    if (!uid) return;
    try {
      const j = await call(`/api/admin/bot/inbox?user_id=${uid}`, password);
      setMsgs(j.messages || []);
    } catch (e) { setErr(e.message); }
  }, [password]);

  useEffect(() => { loadThreads(); }, [loadThreads]);
  useEffect(() => { if (open) { setMsgs(null); loadThread(open); } }, [open, loadThread]);

  /* پایین‌ماندن — ولی فقط وقتی کاربر خودش پایین است.
     اگر وسطِ تاریخچه باشد و پیام تازه بیاید، پرتاب‌شدن به انتها
     آزاردهنده است؛ به‌جایش دکمه‌ی «برو پایین» می‌آید. */
  useEffect(() => {
    if (atEnd) endRef.current?.scrollIntoView({ block: "end" });
  }, [msgs, atEnd]);

  const onScroll = () => {
    const el = logRef.current;
    if (!el) return;
    setAtEnd(el.scrollHeight - el.scrollTop - el.clientHeight < 60);
  };

  /* گفتگوی باز زنده می‌ماند — مشتری ممکن است همین حالا بنویسد.
   *
   * پانزده ثانیه برای یک گفتگو خیلی زیاد بود: مشتری می‌نوشت و
   * مالک تا ربع دقیقه بعد نمی‌دید. حالا سه ثانیه — ولی فقط تا دو
   * دقیقه بعد از آخرین حرکت. گفتگویی که رها شده نباید تا ابد هر
   * سه ثانیه به سرور بزند.
   */
  const lastMove = useRef(Date.now());
  useEffect(() => { lastMove.current = Date.now(); }, [open, msgs]);

  useEffect(() => {
    if (!open) return undefined;
    const id = setInterval(() => {
      if (document.visibilityState !== "visible") return;
      const idle = Date.now() - lastMove.current > 120000;
      // وقتی گفتگو سرد شده، هر پنجمین تیک کافی است
      if (idle && Math.floor(Date.now() / 3000) % 5 !== 0) return;
      loadThread(open);
      loadThreads();
    }, 3000);
    return () => clearInterval(id);
  }, [open, loadThread, loadThreads]);

  // برگشت به تب باید فوری تازه کند، نه اینکه تا تیکِ بعدی صبر کند
  useEffect(() => {
    if (!open) return undefined;
    const wake = () => {
      if (document.visibilityState !== "visible") return;
      lastMove.current = Date.now();
      loadThread(open);
      loadThreads();
    };
    document.addEventListener("visibilitychange", wake);
    window.addEventListener("focus", wake);
    return () => {
      document.removeEventListener("visibilitychange", wake);
      window.removeEventListener("focus", wake);
    };
  }, [open, loadThread, loadThreads]);

  /**
   * فرستادن — با حبابِ فوری.
   *
   * قبلاً متن تا وقتی *دو* رفت‌وبرگشت تمام نمی‌شد (POST، بعد
   * خواندنِ دوباره‌ی گفتگو) روی صفحه نمی‌آمد. روی اینترنتِ کند یعنی
   * یکی دو ثانیه که انگار هیچ اتفاقی نیفتاده — و مالک دوباره
   * می‌زد.
   *
   * حالا حباب همان لحظه می‌نشیند با نشانِ «در حال رفتن»، و اگر
   * نرسید همان‌جا قرمز می‌شود. جعبه هم فوری خالی می‌شود.
   */
  const send = async () => {
    const body = text.trim();
    if (!body || busy || !open) return;
    const temp = `tmp-${Date.now()}`;
    setBusy(true); setErr("");
    setText("");
    setAtEnd(true);
    setMsgs((prev) => [...(prev || []), {
      id: temp, from: "admin", body,
      at: new Date().toISOString().slice(0, 19).replace("T", " "),
      pending: true,
    }]);
    boxRef.current?.focus();
    try {
      await call("/api/admin/bot/inbox/send", password,
                 { method: "POST", body: { userId: open, body } });
      lastMove.current = Date.now();
      await loadThread(open);
      loadThreads();
    } catch (e) {
      setErr(e.message);
      // حبابِ ناموفق نباید شبیه پیامِ رفته بماند
      setMsgs((prev) => (prev || []).map(
        (m) => (m.id === temp ? { ...m, pending: false, failed: true } : m)));
    } finally { setBusy(false); }
  };

  const cur = (threads || []).find((t) => t.userId === open);

  const shown = useMemo(() => {
    const needle = q.trim();
    if (!needle) return threads || [];
    return (threads || []).filter((t) =>
      `${t.name} ${t.username} ${t.tgId} ${t.lastBody}`.includes(needle));
  }, [threads, q]);

  /* پیام‌های پشت‌سرهمِ یک نفر یک گروه می‌شوند: فقط اولی چهره و
     نامش را می‌گیرد. بدون این، ده پیامِ پشت‌سرهم ده تا آواتار
     می‌شوند و صفحه شلوغ می‌شود. */
  const grouped = useMemo(() => {
    const out = [];
    let lastDay = null;
    let lastFrom = null;
    (msgs || []).forEach((m) => {
      const d = dayKey(m.at);
      if (d && d !== lastDay) {
        out.push({ kind: "day", key: `d${d}`, label: dayLabel(d) });
        lastDay = d;
        lastFrom = null;
      }
      out.push({ kind: "msg", key: m.id, m, head: m.from !== lastFrom });
      lastFrom = m.from;
    });
    return out;
  }, [msgs]);

  return (
    <>
      <SectionHead icon={MessageCircle} title="پیام‌ها"
        desc="گفتگو با مشتری‌ها. خبرهای خودکار — مثل تایید یا رد رسید — هم در همین گفتگو ثبت می‌شوند، پس دقیقاً همان چیزی را می‌بینید که مشتری دیده."
        action={
          <button onClick={() => { loadThreads(); if (open) loadThread(open); }}
            className="fx-btn-g px-3 py-2 text-[13px] flex items-center gap-1.5">
            <RefreshCw size={13} /> تازه‌سازی
          </button>
        } />

      {err && (
        <p className="text-[13px] mb-3 flex items-start gap-1.5"
          style={{ color: "var(--danger)" }}>
          <AlertTriangle size={13} className="shrink-0 mt-0.5" />{err}
        </p>
      )}

      {!threads ? (
        <PageSkeleton />
      ) : !threads.length ? (
        <EmptyState icon={MessageCircle} text="هنوز پیامی نیامده"
          hint="هر پیامی که مشتری از مینی‌اپ بفرستد همین‌جا می‌آید — و خبر تایید و رد رسیدها هم." />
      ) : (
        <div className="fx-chat">
          {/* ── ستونِ گفتگوها ── */}
          <aside className="fx-chat-list">
            <div className="fx-chat-search">
              <Search size={13} />
              <input value={q} onChange={(e) => setQ(e.target.value)}
                placeholder="جست‌وجوی نام یا شناسه" />
            </div>

            <div className="fx-chat-rows">
              {!shown.length ? (
                <p className="text-[12.5px] text-center py-6" style={{ color: "var(--muted)" }}>
                  چیزی پیدا نشد
                </p>
              ) : shown.map((t) => (
                <button key={t.userId} onClick={() => setOpen(t.userId)}
                  className={`fx-chat-row ${open === t.userId ? "on" : ""}`}>
                  <Avatar name={t.name || t.username} id={t.tgId} size={38}
                    src={t.avatar} />
                  <span className="fx-chat-row-body">
                    <span className="fx-chat-row-top">
                      <b>{t.name || "بدون نام"}</b>
                      <i>{clock(t.lastAt) || toFaDigits(String(t.lastAt || "").slice(5, 10))}</i>
                    </span>
                    <span className="fx-chat-row-bot">
                      <span>{t.lastBody || "—"}</span>
                      {t.unread > 0 && <em>{faNum(t.unread)}</em>}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          </aside>

          {/* ── گفتگو ── */}
          <section className="fx-chat-pane">
            {!open ? (
              <div className="fx-chat-blank">
                <EmptyState icon={MessageCircle} text="یک گفتگو را باز کنید"
                  hint="از فهرست، مشتری‌ای را انتخاب کنید." />
              </div>
            ) : (
              <>
                <header className="fx-chat-head">
                  <Avatar name={cur?.name || cur?.username} id={cur?.tgId} size={34}
                    src={cur?.avatar} />
                  <div className="min-w-0">
                    <b>{cur?.name || "بدون نام"}</b>
                    <span dir="ltr">
                      {cur?.username ? `@${cur.username} · ` : ""}
                      {cur?.tgId ? toFaDigits(cur.tgId) : ""}
                    </span>
                  </div>
                </header>

                <div className="fx-chat-log" ref={logRef} onScroll={onScroll}>
                  {!msgs ? (
                    <div className="p-4"><PageSkeleton /></div>
                  ) : !msgs.length ? (
                    <p className="text-[12.5px] text-center py-8"
                      style={{ color: "var(--muted)" }}>
                      هنوز پیامی رد و بدل نشده
                    </p>
                  ) : grouped.map((g) => (
                    g.kind === "day" ? (
                      <div key={g.key} className="fx-chat-day"><span>{g.label}</span></div>
                    ) : (
                      <div key={g.key}
                        className={`fx-bub ${g.m.from} ${g.head ? "head" : ""}`
                          + `${g.m.pending ? " pending" : ""}${g.m.failed ? " failed" : ""}`}>
                        {g.m.from === "system" && <Shield size={12} className="fx-bub-ico" />}
                        <span className="fx-bub-text">{g.m.body}</span>
                        <span className="fx-bub-meta">
                          {clock(g.m.at)}
                          {/* حبابِ خوش‌بینانه باید بگوید هنوز نرفته —
                              وگرنه پیامی که نرسیده شبیه پیامِ رفته است */}
                          {g.m.from === "admin" && (
                            g.m.failed ? <AlertTriangle size={12} />
                              : g.m.pending ? <Loader2 size={12} className="animate-spin" />
                                : g.m.read ? <CheckCheck size={12} /> : <Check size={12} />
                          )}
                        </span>
                      </div>
                    )
                  ))}
                  <div ref={endRef} />
                </div>

                {!atEnd && (
                  <button className="fx-chat-down" title="برو به آخرین پیام"
                    onClick={() => { setAtEnd(true); endRef.current?.scrollIntoView({ block: "end" }); }}>
                    <ArrowDown size={15} />
                  </button>
                )}

                <footer className="fx-chat-bar">
                  <textarea ref={boxRef} rows={1} dir="auto" value={text}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
                    }}
                    placeholder="پیام بنویسید…  (Enter می‌فرستد، Shift+Enter خط تازه)" />
                  <button onClick={send} disabled={busy || !text.trim()}
                    aria-label="فرستادن" title="فرستادن">
                    {busy ? <Loader2 size={16} className="animate-spin" />
                          : <Send size={16} />}
                  </button>
                </footer>
                <p className="fx-chat-note">
                  پاسخ شما هم در مینی‌اپ و هم در خودِ ربات به مشتری می‌رسد.
                </p>
              </>
            )}
          </section>
        </div>
      )}
    </>
  );
}
