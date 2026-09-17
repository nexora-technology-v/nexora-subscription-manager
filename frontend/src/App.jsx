import React, { useState, useEffect, useCallback, useRef } from "react";
import { NexoraMark } from "./lib/mark.jsx";
import { createPortal } from "react-dom";
import {
  Activity, AlertTriangle, Apple, ArrowUpRight, Bell, Bot, Check, CheckCircle2, ChevronLeft,
  ChevronDown, Circle, Clock, Coins, Copy, CreditCard, Database, DollarSign, Download, ExternalLink, Eye, Gift, Github, Globe,
  HardDrive, HelpCircle, History, Info, Key, Layers, LayoutGrid, Link2, Loader2, LogOut, Menu, Network, UploadCloud, EyeOff,
  MessageCircle, MessageSquare, Minus, Monitor, Package, Palette, PlayCircle, Plus, Power,
  Radio, RefreshCw, Save, Search, Send, Server, Settings, ShieldCheck, Sliders, Smartphone,
  Star, Terminal, Trash2, TrendingUp, FileText, Wallet, Type, Upload, UserPlus, Users, Video, X, XCircle, Zap,
  Palette as PaletteIcon, Plus as PlusIcon, Sparkles,
} from "lucide-react";

import { API_URL, WORKSPACES, WS_MODES } from "./lib/constants";

import { BillingClients, BillingDash, BillingGroups, BillingInvoice, BillingPayments, BillingPeriod, BillingSettings } from "./sections/billing";
import { BotAffiliates } from "./sections/bot/affiliates";
import { BotBackupSection } from "./sections/bot/backup";
import { BotCoinsSection } from "./sections/bot/coins";
import { BotSection } from "./sections/bot/connection";
import { BotInboundsSection } from "./sections/bot/inbounds";
import { BotOrdersSection } from "./sections/bot/orders";
import { BotInboxSection } from "./sections/bot/inbox";
import { BotPlansSection } from "./sections/bot/plans";
import { BotReportSection, BotStatsSection } from "./sections/bot/stats";
import { BotPreviewSection, BotTextsSection } from "./sections/bot/texts";
import { ThemesSection } from "./sections/bot/themes";
import { BotUsersSection } from "./sections/bot/users";
import { FirewallBlocked, FirewallRules } from "./sections/firewall";
import { FirewallEnable } from "./sections/firewall-enable";
import { FirewallIntrusion } from "./sections/intrusion";
import { BillingExpenses, BillingLedger } from "./sections/expenses";
import { NodesMonitor } from "./sections/nodes-monitor";
import { PortalAdmin, ResellerInbounds } from "./sections/portal-admin";
import { MonitorSection } from "./sections/monitoring";
import { AppsSection, BannersSection, FaqSection, LinksSection, OverviewSection, PopupSection, ReferralSection, ResellersSection, SettingsSection, VideosSection } from "./sections/subpage";
import { LivePreview, SystemSection } from "./sections/system";
import { SystemHealth, TunnelEvents, TunnelList, TunnelNodes, TunnelOverview } from "./sections/tunnel";
import { WorkspaceSwitch } from "./shell/workspace";
import { CommandPalette, ConfirmModal, ErrorBoundary, LoginScreen, NavAlert, NavIndicator, StatusChip, Toast } from "./ui/index";
import { AlertBell } from "./shell/alertbell";
import { errText } from "./lib/format";


const ALL_NAV = Object.values(WORKSPACES).flatMap((w) => w.groups.flatMap((g) => g.items));

export default function App() {
  const [password, setPassword] = useState(() => localStorage.getItem("nexora_subpage_admin_pw") || "");
  /* نسخه‌ی تنظیماتی که گرفته‌ایم.

     موقع ذخیره همین پس فرستاده می‌شود. اگر کسِ دیگری — یا تبِ
     دیگرِ خودمان — زودتر ذخیره کرده باشد، سرور رد می‌کند؛ وگرنه
     هر کدام که دیرتر ذخیره کند کارِ دیگری را بی‌صدا پاک می‌کند. */
  const [cfgVersion, setCfgVersion] = useState(null);
  const [authed, setAuthed] = useState(false);
  const [config, setConfigRaw] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [alerts, setAlerts] = useState({ receipts: 0, messages: 0 });
  const [active, setActive] = useState("overview");
  const [workspace, setWorkspace] = useState(() => {
    const w = localStorage.getItem("nexora_workspace");
    return WORKSPACES[w] ? w : "sub";
  });

  // حالت نمایش سوییچ فضای کاری — سلیقه‌ای است، پس در مرورگر می‌ماند
  const [wsMode, setWsMode] = useState(() => {
    try {
      const m = localStorage.getItem("nexora-ws-mode");
      return WS_MODES[m] ? m : "accordion";
    } catch {
      return "accordion";
    }
  });

  /* هشدارها — چیزهایی که همین حالا کارِ مالک را می‌خواهند.
   *
   * رسید می‌آمد و کسی نمی‌فهمید تا اتفاقی صفحه‌ی سفارش‌ها باز شود.
   * یعنی مشتری پول داده و منتظر مانده، و مالک خبر نداشت.
   *
   * سبک است (فقط دو شمارنده) و وقتی تب پنهان است نمی‌دود — پنلِ
   * بازِ فراموش‌شده نباید تا ابد به سرور بزند.
   */
  useEffect(() => {
    if (!password) return undefined;
    let alive = true;
    const beat = async () => {
      if (!alive || document.visibilityState !== "visible") return;
      try {
        const r = await fetch(`${API_URL}/api/admin/bot/alerts`,
          { headers: { "X-Admin-Password": password } });
        if (!r.ok) return;
        const j = await r.json();
        // کلِ پاسخ نگه داشته می‌شود: نشانِ کنارِ منو فقط شمار
        // می‌خواهد، ولی زنگ به نام و ساعت هم نیاز دارد
        if (alive) setAlerts({
          receipts: j.receipts || 0, messages: j.messages || 0,
          items: j.items || [], oldestMin: j.oldestMin || 0,
        });
      } catch { /* شبکه قطع بود — دفعه‌ی بعد */ }
    };
    const id = setInterval(beat, 25000);
    beat();

    // برگشتن به تب باید فوری تازه کند، نه اینکه تا تیکِ بعدی صبر
    // کند. مالک تب را عوض می‌کند، رسیدی می‌آید، برمی‌گردد — و تا
    // ۲۵ ثانیه پنل هنوز می‌گوید چیزی نیست.
    const wake = () => { if (document.visibilityState === "visible") beat(); };
    document.addEventListener("visibilitychange", wake);
    window.addEventListener("focus", wake);
    return () => {
      alive = false;
      clearInterval(id);
      document.removeEventListener("visibilitychange", wake);
      window.removeEventListener("focus", wake);
    };
  }, [password]);


  useEffect(() => {
    try { localStorage.setItem("nexora-ws-mode", wsMode); } catch { /* بی‌صدا */ }
  }, [wsMode]);
  const [confirmTarget, setConfirmTarget] = useState(null);
  const [toast, setToast] = useState(null);
  const [open, setOpen] = useState(false);
  const [palOpen, setPalOpen] = useState(false);

  // جمع‌شدن سایدبار و کم‌کردن حرکت، هر دو سلیقه‌اند: در مرورگر
  // می‌مانند تا هر بار دوباره تنظیم نشوند. روی <body> می‌نشینند
  // چون CSSشان به کل صفحه مربوط است، نه به یک کامپوننت.
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem("nexora-collapsed") === "1"; } catch { return false; }
  });
  const [calm, setCalm] = useState(() => {
    try { return localStorage.getItem("nexora-calm") === "1"; } catch { return false; }
  });
  useEffect(() => {
    document.body.classList.toggle("fx-collapsed", collapsed);
    try { localStorage.setItem("nexora-collapsed", collapsed ? "1" : "0"); } catch { /* بی‌صدا */ }
  }, [collapsed]);
  useEffect(() => {
    document.body.classList.toggle("fx-calm", calm);
    try { localStorage.setItem("nexora-calm", calm ? "1" : "0"); } catch { /* بی‌صدا */ }
  }, [calm]);

  // Ctrl+K — تنها راهِ رسیدن به ۴۵ صفحه بدون سه کلیک
  useEffect(() => {
    const k = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPalOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, []);

  // نسخه‌ی آخرین حالت ذخیره‌شده — مرجع برای لغو تغییرات
  const [savedConfig, setSavedConfig] = useState(null);

  const setConfig = (next) => { setConfigRaw(next); setDirty(true); };

  // بازگرداندن همه‌ی تغییرات ذخیره‌نشده به آخرین حالت ذخیره‌شده
  const discardChanges = () => {
    if (!savedConfig) return;
    setConfigRaw(JSON.parse(JSON.stringify(savedConfig)));
    setDirty(false);
    setToast({ message: "تغییرات لغو شد", type: "ok" });
  };

  const fetchAll = useCallback(async (pw) => {
    setLoading(true);
    try {
      const [cRes, sRes] = await Promise.all([
        fetch(`${API_URL}/api/admin/config`, { headers: { "X-Admin-Password": pw } }),
        fetch(`${API_URL}/api/admin/stats`, { headers: { "X-Admin-Password": pw } }),
      ]);
      if (!cRes.ok) throw new Error();
      const loaded = await cRes.json();
      /* هدرِ نسخه اختیاری است و *هرگز* نباید بارگذاری را بشکند.
         یک‌بار همین کار را کرد: روی پاسخی که headers نداشت خطا
         داد، خطا داخل catchِ بیرونی افتاد، و نتیجه‌اش بیرون‌انداختنِ
         مالک از پنل بود — برای نبودِ یک هدر. */
      try { setCfgVersion(cRes.headers?.get?.("X-Config-Version") || null); }
      catch { setCfgVersion(null); }
      setConfigRaw(loaded);
      setSavedConfig(JSON.parse(JSON.stringify(loaded)));
      if (sRes.ok) setStats(await sRes.json());
      setAuthed(true);
    } catch { setAuthed(false); localStorage.removeItem("nexora_subpage_admin_pw"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { if (password) fetchAll(password); else setLoading(false); }, [password, fetchAll]);
  useEffect(() => { if (toast) { const t = setTimeout(() => setToast(null), 3000); return () => clearTimeout(t); } }, [toast]);
  useEffect(() => {
    const h = (e) => { if (dirty) { e.preventDefault(); e.returnValue = ""; } };
    window.addEventListener("beforeunload", h);
    return () => window.removeEventListener("beforeunload", h);
  }, [dirty]);
  // هنگام باز بودن کشو: بستن با Escape.
  // نکته: اسکرول body را قفل نمی‌کنیم چون خود سایدبار اسکرول داخلی دارد
  // و قفل‌کردن body در بعضی مرورگرهای موبایل باعث گیرکردن کل صفحه می‌شود.
  useEffect(() => {
    if (!open) return;
    const k = (e) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [open]);

  const navigate = (k) => { setActive(k); setOpen(false); };

  // اگر صفحه‌ی فعال در حالت کاری جاری وجود نداشت (مثلاً بعد از رفرش)،
  // خودکار به اولین صفحه‌ی همان حالت می‌رویم تا صفحه‌ی خالی نبینیم.
  useEffect(() => {
    const keys = WORKSPACES[workspace].groups.flatMap((g) => g.items).map((i) => i.key);
    if (!keys.includes(active)) {
      const first = WORKSPACES[workspace].groups.flatMap((g) => g.items).find((i) => !i.badge);
      if (first) setActive(first.key);
    }
  }, [workspace, active]);

  // تعویض حالت کاری — به اولین آیتم فعال همان حالت می‌رود
  const switchWorkspace = (wsKey) => {
    setWorkspace(wsKey);
    localStorage.setItem("nexora_workspace", wsKey);
    const first = WORKSPACES[wsKey].groups
      .flatMap((g) => g.items)
      .find((i) => !i.badge);
    if (first) setActive(first.key);
    setOpen(false);
  };
  const login = (pw) => { localStorage.setItem("nexora_subpage_admin_pw", pw); setPassword(pw); };
  const logout = () => { localStorage.removeItem("nexora_subpage_admin_pw"); setPassword(""); setAuthed(false); };

  // بعد از تغییر موفق رمز، رمز جدید را جایگزین می‌کنیم تا کاربر
  // بدون نیاز به ورود مجدد بتواند به کارش ادامه دهد.
  const handlePasswordChanged = (newPw) => {
    localStorage.setItem("nexora_subpage_admin_pw", newPw);
    setPassword(newPw);
    setToast({ message: "رمز عبور تغییر کرد — نیازی به ورود مجدد نیست", type: "ok" });
  };

  const save = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/api/admin/config`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Password": password,
          ...(cfgVersion ? { "X-Config-Version": String(cfgVersion) } : {}),
        },
        body: JSON.stringify(config),
      });
      if (res.ok) {
        const j = await res.json().catch(() => ({}));
        if (j.version) setCfgVersion(String(j.version));
        setDirty(false);
        setSavedConfig(JSON.parse(JSON.stringify(config)));
        setToast({ message: "تغییرات با موفقیت ذخیره شد", type: "ok" });
        const sRes = await fetch(`${API_URL}/api/admin/stats`, { headers: { "X-Admin-Password": password } });
        if (sRes.ok) setStats(await sRes.json());
      } else {
        /* دلیلِ سرور را نشان بده، نه یک «ناموفق بود» خشک.
           مهم‌ترین حالتش ۴۰۹ است: یعنی جای دیگری عوض شده و اگر
           به زور ذخیره کنیم، کارِ آن‌جا پاک می‌شود. */
        const j = await res.json().catch(() => ({}));
        setToast({
          message: errText(j.detail, res.status === 409
            ? "این تنظیمات را جای دیگری عوض کرده‌اید — صفحه را تازه کنید"
            : "ذخیره‌سازی ناموفق بود"),
          type: "error",
        });
      }
    } catch { setToast({ message: "اتصال به سرور برقرار نشد", type: "error" }); }
    finally { setSaving(false); }
  };

  const confirmDelete = () => {
    const t = confirmTarget;
    if (t.type === "app") setConfig({ ...config, downloadApps: { ...(config.downloadApps || {}), [t.os]: (config.downloadApps?.[t.os] || []).filter((_, i) => i !== t.idx) } });
    else if (t.type === "faq") setConfig({ ...config, faq: { ...config.faq, [t.lang]: (config.faq?.[t.lang] || []).filter((_, i) => i !== t.idx) } });
    else if (t.type === "video") setConfig({ ...config, videos: config.videos.filter((_, i) => i !== t.idx) });
    else if (t.type === "reseller") setConfig({ ...config, resellers: config.resellers.filter((_, i) => i !== t.idx) });
    setConfirmTarget(null);
  };

  if (!password || !authed) {
    if (loading && password) return <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg)" }}><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;
    return <LoginScreen onLogin={login} />;
  }
  if (loading || !config) return <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg)" }}><Loader2 className="animate-spin" style={{ color: "var(--muted)" }} /></div>;

  const currentNav = ALL_NAV.find((n) => n.key === active);

  return (
    <div className="min-h-screen w-full flex fx-shell" dir="rtl">
      {/* نور محیطی — زیر همه چیز، فقط برای عمق */}
      <div className="fx-amb" aria-hidden="true"><i /></div>
      {open && <div className="fx-backdrop fx-fade" onClick={() => setOpen(false)} />}

      <aside className={`fx-side ${open ? "open" : ""}`} style={{ zIndex: 60 }}>
        <div className="flex items-center justify-between gap-2 px-2 mb-2">
          <div className="flex items-center gap-2.5 min-w-0">
            {/* همان نشانِ صفحه‌ی ورود، نه یک مربعِ «N» دیگر — دو شکلِ
                متفاوت برای یک برند، یعنی هیچ‌کدام شناخته نمی‌شوند */}
            <NexoraMark size={36} className="shrink-0" />
            <div className="min-w-0 fx-hide-c">
              <div className="text-[16px] font-bold text-white leading-none">NEXORA</div>
              <div className="text-[12px] mt-1" style={{ color: "var(--muted)" }}>پنل مدیریت</div>
            </div>
          </div>
          <button title="بستن منو" className="lg:hidden shrink-0" onClick={() => setOpen(false)} style={{ color: "var(--dim)" }}><X size={18} /></button>
        </div>

        <WorkspaceSwitch mode={wsMode} workspace={workspace} onSwitch={switchWorkspace}
          alerts={alerts}
          active={active} setActive={setActive} />

        {/* در حالت تاشو، منو داخل خود آکاردئون است — اینجا تکرارش نمی‌کنیم */}
        {wsMode !== "accordion" && WORKSPACES[workspace].groups.map((group) => {
          const items = group.items;
          if (items.length === 0) return null;
          return (
            <div key={group.title}>
              <div className="fx-side-label">{group.title}</div>
              <nav className="flex flex-col gap-1 relative">
                <NavIndicator activeKey={active} />
                {items.map((n) => (
                  <button key={n.key} data-navkey={n.key}
                    className={`fx-nav-item ${active === n.key ? "on" : ""}`}
                    onClick={() => navigate(n.key)} disabled={!!n.badge}
                    style={n.badge ? { opacity: 0.55, cursor: "not-allowed" } : {}}>
                    <n.icon size={16} />
                    <span className="flex-1 text-right fx-lbl">{n.label}</span>
                    {n.badge && (
                      <span className="text-[11px] px-1.5 py-0.5 rounded-full shrink-0 fx-hide-c"
                        style={{ background: "var(--warn-soft)", color: "var(--warn)" }}>
                        {n.badge}
                      </span>
                    )}
                    {/* چیزی که همین حالا کار می‌خواهد.
                        رسید می‌آمد و کسی نمی‌فهمید تا اتفاقی صفحه‌ی
                        سفارش‌ها باز شود — یعنی مشتری پول داده و
                        منتظر مانده بدون اینکه کسی خبر داشته باشد. */}
                    {!n.badge && n.alert && <NavAlert count={alerts[n.alert]} />}
                    {/* در حالت جمع، نامِ آیتم فقط روی تولتیپ می‌ماند */}
                    <span className="fx-tip-nav">{n.label}</span>
                  </button>
                ))}
              </nav>
            </div>
          );
        })}

        <div className="mt-6 pt-4" style={{ borderTop: "1px solid var(--border)" }}>
          <div className="fx-card p-3 mb-3" style={{ background: "var(--surface-2)" }}>
            <div className="flex items-center gap-2 mb-1.5">
              <Circle size={7} fill="var(--ok)" strokeWidth={0} />
              <span className="text-[13px] font-semibold" style={{ color: "var(--ok)" }}>سرویس فعال</span>
            </div>
            <div className="text-[12px]" style={{ color: "var(--muted)" }} dir="ltr">t.me/{config.links?.channelUsername}</div>
          </div>
          <button onClick={logout} className="fx-nav-item"><LogOut size={15} /> خروج</button>
        </div>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="fx-topbar">
          <div className="flex items-center gap-3 min-w-0">
            <button className="fx-burger" onClick={() => setOpen(true)} aria-label="منو"><Menu size={19} /></button>
            {/* جمع‌کردن منو — روی دسکتاپ، تا وقتی جدول پهن است جا باز شود */}
            <button className="fx-btn-g w-9 h-9 hidden lg:grid place-items-center shrink-0"
              onClick={() => setCollapsed((v) => !v)}
              title={collapsed ? "باز کردن منو" : "جمع کردن منو"}
              aria-label={collapsed ? "باز کردن منو" : "جمع کردن منو"}>
              <Layers size={16} />
            </button>
            <div className="min-w-0">
              <h1 className="text-[18px] font-bold text-white truncate">{currentNav?.label}</h1>
              <p className="text-[13px] mt-0.5 fx-hide-m" style={{ color: "var(--muted)" }}>{WORKSPACES[workspace].label}</p>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            {/* دکمه‌ی پالت — جستجوی سایدبار فقط همین فضای کاری را
                فیلتر می‌کند؛ این، هر ۴۵ صفحه را یک‌جا می‌گردد */}
            <button className="fx-search" onClick={() => setPalOpen(true)}
              title="جستجو در همه‌ی صفحه‌ها" aria-label="جستجو در همه‌ی صفحه‌ها"
              style={{ cursor: "pointer" }}>
              <Search size={14} style={{ color: "var(--muted)" }} />
              <span className="text-[13px] flex-1 text-right fx-hide-m"
                style={{ color: "var(--muted)" }}>جستجو یا فرمان…</span>
              <kbd className="text-[10px] px-1.5 py-0.5 rounded shrink-0 fx-hide-m"
                style={{ background: "var(--hair-2)", border: "1px solid var(--border-2)",
                         color: "var(--dim)", fontFamily: "var(--mono)" }} dir="ltr">Ctrl K</kbd>
            </button>
            {/* پریدن به همان صفحه — و حالتِ کاری هم باید عوض شود،
                وگرنه افکتِ نگهبان فوراً برمی‌گرداندش به صفحه‌ی اولِ
                حالتِ فعلی و دکمه «کار نمی‌کند» */}
            <AlertBell data={alerts} onGo={(key) => {
              const ws = Object.keys(WORKSPACES).find((w) =>
                WORKSPACES[w].groups.some((g) => g.items.some((i) => i.key === key)));
              if (ws && ws !== workspace) setWorkspace(ws);
              setActive(key);
              setOpen(false);
            }} />
            <button className="fx-btn-g w-9 h-9 grid place-items-center shrink-0 fx-hide-m"
              onClick={() => setCalm((v) => !v)}
              title={calm ? "حرکت: کم — برای روشن‌کردن بزنید" : "حرکت: روشن — برای کم‌کردن بزنید"}
              aria-label="کم‌کردن حرکت" aria-pressed={calm}>
              <Activity size={16} style={calm ? { color: "var(--muted)" } : {}} />
            </button>
            <div className="fx-hide-m"><StatusChip dirty={dirty} /></div>
            {dirty && (
              <button onClick={discardChanges} title="بازگرداندن به آخرین حالت ذخیره‌شده"
                className="fx-btn-g px-3 py-2.5 text-[13px] flex items-center gap-1.5 shrink-0">
                <RefreshCw size={13} className="scale-x-[-1]" />
                <span className="fx-hide-m">لغو تغییرات</span>
              </button>
            )}
            <button title="ذخیره تغییرات" onClick={save} disabled={saving || !dirty} className="fx-desktop-save fx-btn px-4 py-2.5 text-[14px] flex items-center gap-1.5 shrink-0">
              {saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />}
              <span className="fx-hide-m">{saving ? "در حال ذخیره..." : "ذخیره تغییرات"}</span>
            </button>
          </div>
        </header>

        {/* ورودِ صفحه با هر بار عوض‌شدن بخش دوباره پخش می‌شود:
            key که عوض شود، React درخت را از نو می‌سازد. «فوری ولی
            زنده» — نه جایگزینیِ ناگهانی، نه انتظارِ نمایشی. */}
        <main className="fx-main flex-1 p-7 overflow-y-auto w-full mx-auto">
          <div key={active} className="fx-stg">
          <ErrorBoundary key={active}>
          {active === "overview" && <OverviewSection config={config} stats={stats} navigate={navigate} dirty={dirty} password={password} />}
          {active === "preview" && <LivePreview dirty={dirty} onSave={save} saving={saving} />}
          {active === "apps" && <AppsSection config={config} setConfig={setConfig} requestDelete={setConfirmTarget} />}
          {active === "videos" && <VideosSection config={config} setConfig={setConfig} requestDelete={setConfirmTarget} />}
          {active === "faq" && <FaqSection config={config} setConfig={setConfig} requestDelete={setConfirmTarget} />}
          {active === "resellers" && <ResellersSection config={config} setConfig={setConfig} requestDelete={setConfirmTarget} password={password} />}
          {active === "bot" && <BotSection password={password} dirty={dirty} />}
          {active === "bot-inbounds" && <BotInboundsSection password={password} />}
          {active === "bot-plans" && <BotPlansSection password={password} />}
          {active === "bot-orders" && <BotOrdersSection password={password} />}
          {active === "bot-inbox" && <BotInboxSection password={password} />}
          {active === "bot-users" && <BotUsersSection password={password} />}
          {active === "bot-report" && <BotReportSection password={password} />}
          {active === "bot-coins" && <BotCoinsSection password={password} />}
          {active === "bot-affiliates" && <BotAffiliates password={password} />}
          {active === "bill-dash" && <BillingDash password={password} />}
          {active === "bill-groups" && <BillingGroups password={password} />}
          {active === "bill-portal" && <PortalAdmin password={password} />}
          {active === "res-inbounds" && <ResellerInbounds password={password} />}
          {active === "bill-invoice" && <BillingInvoice password={password} />}
          {active === "bill-pay" && <BillingPayments password={password} />}
          {active === "bill-period" && <BillingPeriod password={password} />}
          {active === "bill-clients" && <BillingClients password={password} />}
          {active === "tun-overview" && <TunnelOverview password={password} />}
          {active === "tun-nodes" && <TunnelNodes password={password} />}
          {active === "tun-list" && <TunnelList password={password} />}
          {active === "monitor" && <MonitorSection password={password} />}
          {active === "fw-enable" && <FirewallEnable password={password} />}
          {active === "fw-rules" && <FirewallRules password={password} />}
          {active === "nodes-monitor" && <NodesMonitor password={password} />}
          {active === "bill-ledger" && <BillingLedger password={password} />}
          {active === "bill-expenses" && <BillingExpenses password={password} />}
          {active === "fw-intrusion" && <FirewallIntrusion password={password} />}
          {active === "fw-blocked" && <FirewallBlocked password={password} />}
          {active === "tun-health" && <SystemHealth password={password} />}
          {active === "tun-events" && <TunnelEvents password={password} />}
          {active === "bill-settings" && <BillingSettings password={password} />}
          {active === "bot-texts" && <BotTextsSection password={password} />}
          {active === "bot-preview" && <BotPreviewSection />}
          {active === "bot-stats" && <BotStatsSection password={password} />}
          {active === "bot-backup" && <BotBackupSection password={password} />}
          {active === "popup" && <PopupSection config={config} setConfig={setConfig} />}
          {active === "banners" && <BannersSection config={config} setConfig={setConfig} />}
          {active === "referral" && <ReferralSection config={config} setConfig={setConfig} />}
          {active === "links" && <LinksSection config={config} setConfig={setConfig} />}
          {active === "settings" && <SettingsSection config={config} setConfig={setConfig} password={password} wsMode={wsMode} setWsMode={setWsMode} onPasswordChanged={handlePasswordChanged} onRestored={() => fetchAll(password)} />}
          {active === "themes" && <ThemesSection config={config} setConfig={setConfig} password={password} />}
          {active === "system" && <SystemSection password={password} />}
          </ErrorBoundary>
          </div>
        </main>
      </div>

      <div className="fx-mobile-save">
        <div className="shrink-0"><StatusChip dirty={dirty} /></div>
        <button title="ذخیره تغییرات" onClick={save} disabled={saving || !dirty} className="fx-btn flex-1 flex items-center justify-center gap-2 py-3 text-[14px]">
          {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
          {saving ? "در حال ذخیره..." : "ذخیره تغییرات"}
        </button>
      </div>

      {confirmTarget && (
        <ConfirmModal title="حذف این مورد؟"
          desc={`آیا مطمئن هستید می‌خواهید «${confirmTarget.name}» را حذف کنید؟ این عمل بعد از ذخیره‌ی تغییرات، از صفحه‌ی اشتراک هم حذف می‌شود.`}
          onConfirm={confirmDelete} onCancel={() => setConfirmTarget(null)} />
      )}
      {toast && <Toast message={toast.message} type={toast.type} />}

      {/* پالت فرمان — هم می‌برد، هم کار می‌کند */}
      <CommandPalette
        open={palOpen} onClose={() => setPalOpen(false)} workspaces={WORKSPACES}
        onPick={(ws, key) => {
          if (ws !== workspace) { setWorkspace(ws); localStorage.setItem("nexora_workspace", ws); }
          setActive(key);
          setOpen(false);
        }}
        extra={[
          { label: dirty ? "ذخیره‌ی تغییرات" : "ذخیره (چیزی عوض نشده)",
            group: "کارها", icon: Save, run: () => dirty && save() },
          { label: collapsed ? "باز کردن منو" : "جمع کردن منو",
            group: "کارها", icon: Layers, run: () => setCollapsed((v) => !v) },
          { label: calm ? "روشن‌کردن حرکت" : "کم‌کردن حرکت",
            group: "کارها", icon: Activity, run: () => setCalm((v) => !v) },
          { label: "خروج از حساب", group: "کارها", icon: LogOut, run: logout },
        ]} />
    </div>
  );
}
