import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import Portal, { portalSlug } from "./portal/index.jsx";
import Mini, { isMini } from "./mini/index.jsx";
import "./index.css";

// آدرس تعیین می‌کند کدام اپ بالا بیاید.
//
// /r/<نشانی> پنل نماینده است و /app مینی‌اپ مشتری. هیچ‌کدام ربطی به
// پنل مدیر ندارند — نه کدشان، نه مسیرهایشان. این شرط تنها جایی است
// که این سه به هم می‌رسند، و عمداً همین‌قدر کوچک نگه داشته شده.
const Root = isMini() ? Mini : portalSlug() ? Portal : App;

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);
