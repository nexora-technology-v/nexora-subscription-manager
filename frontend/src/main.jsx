import React, { Suspense, lazy } from "react";
import ReactDOM from "react-dom/client";
import { isMini, portalSlug } from "./lib/route.js";
import "./index.css";

// آدرس تعیین می‌کند کدام اپ بالا بیاید.
//
// /r/<نشانی> پنل نماینده است و /app مینی‌اپ مشتری. هیچ‌کدام ربطی به
// پنل مدیر ندارند — نه کدشان، نه مسیرهایشان. این شرط تنها جایی است
// که این سه به هم می‌رسند، و عمداً همین‌قدر کوچک نگه داشته شده.
//
// و با lazy بارگذاری می‌شوند، نه با import مستقیم: وگرنه هر سه در
// یک فایل می‌نشینند و مشتریِ مینی‌اپ کلِ پنل مدیر را هم دانلود
// می‌کند. شرط از `lib/route.js` می‌آید که هیچ وابستگی‌ای ندارد، پس
// خودِ تصمیم چیزی را بار نمی‌کند.
const Mini = lazy(() => import("./mini/index.jsx"));
const Portal = lazy(() => import("./portal/index.jsx"));
const Admin = lazy(() => import("./App.jsx"));

const Root = isMini() ? Mini : portalSlug() ? Portal : Admin;

// تا رسیدنِ تکه، صفحه نباید سفید بماند — همان زمینه‌ی خودِ پنل با
// یک نبضِ آرام، که «دارد می‌آید» را بگوید بدون اینکه چیزی بپرد.
function Booting() {
  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center",
                  background: "var(--bg)" }}>
      <div className="fx-sk" style={{ width: 132, height: 8, borderRadius: 99 }} />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Suspense fallback={<Booting />}>
      <Root />
    </Suspense>
  </React.StrictMode>
);
