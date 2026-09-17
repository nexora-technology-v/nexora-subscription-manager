#!/usr/bin/env node
/**
 * `dist-test/harness.html` را می‌سازد: همان پنلِ ساخته‌شده، ولی با
 * داده‌ی ساختگی، تا بشود بدون بکند و رمز *نگاهش کرد*.
 *
 * چرا یک ابزار و نه یک فایلِ دستی: نامِ فایل‌های ساخته‌شده با هر
 * بیلد عوض می‌شود (هش دارند). نسخه‌ی دستی بعد از اولین بیلد به
 * فایل‌های مرده اشاره می‌کرد و صفحه‌ی سفید می‌داد.
 *
 * اجرا:
 *     cd frontend && NEXORA_SINGLE_BUNDLE=1 npx vite build
 *     node tools/make-harness.js
 *     cd frontend && npx vite preview --outDir dist-test --port 5180
 *
 * و بعد، هر سه اپ از همین یک آدرس:
 *
 *     http://localhost:5180/harness.html             پنل مدیر
 *     http://localhost:5180/harness.html?as=portal   پنل نماینده
 *     http://localhost:5180/harness.html?as=mini     مینی‌اپ مشتری
 *
 * چرا `?as=` و نه آدرس واقعی: هر سه اپ از `location.pathname`
 * انتخاب می‌شوند و سرورِ پیش‌نمایش فایلی روی `/r/<نشانی>` ندارد.
 * اسکریپتِ داده مسیر را *پیش از* اجرای باندل عوض می‌کند.
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.dirname(__dirname);
const DIST = path.join(ROOT, "frontend", "dist-test");
const indexPath = path.join(DIST, "index.html");

if (!fs.existsSync(indexPath)) {
  console.error("❌ dist-test ساخته نشده. اول:");
  console.error("   cd frontend && NEXORA_SINGLE_BUNDLE=1 npx vite build");
  process.exit(1);
}

const bootPath = path.join(ROOT, "tools", "harness-boot.js");
const boot = fs.readFileSync(bootPath, "utf8");

// نحوِ داده‌ی ساختگی را همین‌جا بسنج.
//
// یک خطای نحوی در این فایل، صفحه را نمی‌شکند — فقط اسکریپت اجرا
// نمی‌شود و `fetch` دزدیده نمی‌شود. نتیجه: هارنس بالا می‌آید، به
// سرورِ واقعی درخواست می‌دهد، صفحه‌ی ورود نشان می‌دهد، و آدم فکر
// می‌کند پنل خراب شده. یک‌بار همین‌جا وقت گرفت.
try {
  new Function(boot);
} catch (e) {
  console.error("❌ harness-boot.js نحوش خراب است:", e.message);
  process.exit(1);
}
let html = fs.readFileSync(indexPath, "utf8");

// اسکریپتِ داده باید *پیش از* باندل اجرا شود، وگرنه اپ با fetchِ
// واقعی بالا می‌آید و روی چرخنده می‌ماند
html = html.replace("</head>", `  <script>\n${boot}\n  </script>\n</head>`);
html = html.replace("<title>", "<title>[HARNESS] ");

fs.writeFileSync(path.join(DIST, "harness.html"), html, "utf8");
console.log("✅ dist-test/harness.html ساخته شد");
