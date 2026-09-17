/**
 * صندوق پیام — سمتِ مالک.
 *
 * چرا این‌جا و نه در «کاربران ربات»: آن صفحه برای *دیدنِ* کاربر است،
 * این‌جا برای *جواب‌دادن*. قاطی‌کردنشان یعنی مالک باید هر بار از میان
 * صد کاربر دنبال کسی بگردد که پیام داده.
 *
 * و همان جدولی را می‌خواند که مینی‌اپ می‌نویسد؛ خبرهای خودکار
 * (تایید/ردِ رسید) هم با `sender='system'` در همین گفتگو می‌نشینند،
 * پس مالک دقیقاً همان چیزی را می‌بیند که مشتری دیده.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertTriangle, Loader2, MessageCircle, RefreshCw, Send, Shield,
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

export function BotInboxSection({ password }) {
  const [threads, setThreads] = useState(null);
  const [open, setOpen] = useState(null);      // userId
  const [msgs, setMsgs] = useState(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const endRef = useRef(null);

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
  useEffect(() => { if (open) loadThread(open); }, [open, loadThread]);
  useEffect(() => { endRef.current?.scrollIntoView({ block: "end" }); }, [msgs]);

  // گفتگوی باز باید زنده بماند — مشتری ممکن است همین حالا بنویسد
  useEffect(() => {
    if (!open) return undefined;
    const id = setInterval(() => {
      if (document.visibilityState === "visible") loadThread(open);
    }, 15000);
    return () => clearInterval(id);
  }, [open, loadThread]);

  const send = async () => {
    const body = text.trim();
    if (!body || busy || !open) return;
    setBusy(true); setErr("");
    try {
      await call("/api/admin/bot/inbox/send", password,
                 { method: "POST", body: { userId: open, body } });
      setText("");
      await loadThread(open);
      loadThreads();
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  const cur = (threads || []).find((t) => t.userId === open);

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
        <div className="fx-g2 grid grid-cols-3 gap-3">
          {/* فهرست گفتگوها */}
          <div className="fx-card overflow-hidden" style={{ alignSelf: "start" }}>
            {threads.map((t, i) => (
              <button key={t.userId} onClick={() => setOpen(t.userId)}
                className="w-full text-right p-3 flex items-center gap-2.5 transition-colors hover:bg-white/[.02]"
                style={{
                  borderBottom: i < threads.length - 1 ? "1px solid var(--border)" : "none",
                  background: open === t.userId ? "var(--accent-wash)" : "transparent",
                }}>
                <Avatar name={t.name || t.username} id={t.tgId} size={32} />
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-1.5">
                    <b className="text-[13px] text-white truncate">
                      {t.name || "بدون نام"}
                    </b>
                    {t.unread > 0 && (
                      <i className="fx-unread">{faNum(t.unread)}</i>
                    )}
                  </span>
                  <span className="block text-[11.5px] truncate mt-0.5"
                    style={{ color: "var(--muted)" }}>
                    {t.lastBody || "—"}
                  </span>
                </span>
              </button>
            ))}
          </div>

          {/* گفتگوی باز */}
          <div className="fx-card p-4 col-span-2 flex flex-col"
            style={{ minHeight: 380 }}>
            {!open ? (
              <EmptyState icon={MessageCircle} text="یک گفتگو را باز کنید"
                hint="از فهرست کنار، مشتری‌ای را انتخاب کنید." />
            ) : (
              <>
                <div className="flex items-center gap-2 mb-3 pb-3"
                  style={{ borderBottom: "1px solid var(--border)" }}>
                  <Avatar name={cur?.name || cur?.username} id={cur?.tgId} size={30} />
                  <div className="min-w-0">
                    <div className="text-[13.5px] font-semibold text-white truncate">
                      {cur?.name || "بدون نام"}
                    </div>
                    <div className="text-[11.5px]" dir="ltr"
                      style={{ color: "var(--muted)", fontFamily: "var(--mono)" }}>
                      {cur?.tgId ? toFaDigits(cur.tgId) : ""}
                    </div>
                  </div>
                </div>

                <div className="flex-1 flex flex-col gap-2 overflow-y-auto"
                  style={{ maxHeight: 420 }}>
                  {(msgs || []).map((m) => (
                    <div key={m.id} className={`fx-msg ${m.from}`}>
                      {m.from === "system" && <Shield size={12} className="shrink-0 mt-1" />}
                      <span className="whitespace-pre-wrap break-words">{m.body}</span>
                    </div>
                  ))}
                  <div ref={endRef} />
                </div>

                <div className="flex items-end gap-2 mt-3 pt-3"
                  style={{ borderTop: "1px solid var(--border)" }}>
                  <textarea rows={2} dir="auto" value={text}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
                    }}
                    placeholder="پاسخ شما… (Enter برای فرستادن)"
                    className="fx-input flex-1 text-[13px]"
                    style={{ resize: "none" }} />
                  <button onClick={send} disabled={busy || !text.trim()}
                    className="fx-btn px-4 py-2.5 text-[13px] flex items-center gap-1.5">
                    {busy ? <Loader2 size={13} className="animate-spin" />
                          : <Send size={13} />} فرستادن
                  </button>
                </div>
                <p className="text-[11.5px] mt-2" style={{ color: "var(--muted)" }}>
                  پاسخ شما هم در مینی‌اپ و هم در خود ربات به مشتری می‌رسد.
                </p>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
}
