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
 *     → http://localhost:5180/harness.html
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

const boot = fs.readFileSync(path.join(ROOT, "tools", "harness-boot.js"), "utf8");
let html = fs.readFileSync(indexPath, "utf8");

// اسکریپتِ داده باید *پیش از* باندل اجرا شود، وگرنه اپ با fetchِ
// واقعی بالا می‌آید و روی چرخنده می‌ماند
html = html.replace("</head>", `  <script>\n${boot}\n  </script>\n</head>`);
html = html.replace("<title>", "<title>[HARNESS] ");

fs.writeFileSync(path.join(DIST, "harness.html"), html, "utf8");
console.log("✅ dist-test/harness.html ساخته شد");
