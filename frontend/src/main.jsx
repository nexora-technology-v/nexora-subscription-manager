import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import Portal, { portalSlug } from "./portal/index.jsx";
import "./index.css";

// آدرس تعیین می‌کند کدام اپ بالا بیاید.
//
// /r/<نشانی> پنل نماینده است و هیچ ربطی به پنل مدیر ندارد — نه
// کدش، نه مسیرهایش. این شرط تنها جایی است که این دو به هم می‌رسند،
// و عمداً همین‌قدر کوچک نگه داشته شده.
const Root = portalSlug() ? Portal : App;

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);
