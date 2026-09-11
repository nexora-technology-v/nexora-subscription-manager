# 📤 راهنمای آپلود به گیت‌هاب

## قدم ۱ — ساخت ریپازیتوری

در گیت‌هاب:
1. دکمه‌ی **New repository**
2. نام پیشنهادی: `nexora-subscription-manager`
3. **Description** (بایوی ریپو):
   ```
   Self-hosted admin panel for 3x-ui subscription pages — multi-reseller white-labeling, one-click config import, live preview.
   ```
4. **Public** یا **Private** — هر کدام (توضیح تفاوتشان پایین‌تر)
5. ⚠️ هیچ گزینه‌ای را تیک نزنید (README, .gitignore, license) — چون در پروژه داریم
6. **Create repository**

## قدم ۲ — تنظیم Topics

بعد از ساخت ریپو، کنار **About** روی چرخ‌دنده بزنید و این تگ‌ها را اضافه کنید:

```
xray  3x-ui  vpn  subscription-page  fastapi  react  self-hosted  white-label  vless  telegram
```

این باعث می‌شود پروژه در جستجوی گیت‌هاب پیدا شود.

## قدم ۳ — آپلود از کامپیوتر خودتان

### اگر git نصب دارید

در پوشه‌ی پروژه (روی کامپیوتر خودتان، نه سرور):

```bash
git init
git add .
git commit -m "Initial release v1.2.0"
git branch -M main
git remote add origin https://github.com/nexora-technology-v/nexora-subscription-manager.git
git push -u origin main
```

⚠️ به‌جای `USERNAME` نام کاربری گیت‌هاب خودتان را بگذارید.

### اگر git ندارید (روش ساده‌تر)

1. در صفحه‌ی ریپازیتوری، روی **uploading an existing file** کلیک کنید
2. همه‌ی فایل‌ها و پوشه‌ها را بکشید داخل صفحه
3. پایین صفحه، پیام commit بنویسید: `Initial release v1.2.0`
4. **Commit changes**

⚠️ **قبل از آپلود، این فایل‌ها را حذف کنید** (اگر وجود دارند):
```
data/auth.json
frontend/node_modules/
frontend/dist/
backend/venv/
backend/__pycache__/
```

## قدم ۴ — ساخت Release

بعد از آپلود:

1. سمت راست، بخش **Releases** → **Create a new release**
2. **Tag**: `v1.2.0` → دکمه‌ی Create new tag
3. **Title**: `v1.2.0 — Automated installer & multi-reseller support`
4. **Description**: محتوای `CHANGELOG.md` را کپی کنید
5. **Publish release**

این کار باعث می‌شود کاربران بتوانند نسخه‌ی مشخصی را دانلود کنند و `nexora update` هم بتواند از آن استفاده کند.

---

## Public یا Private؟

| | Public | Private |
|---|---|---|
| دیده‌شدن کد | همه می‌بینند | فقط شما |
| تبلیغ برند | ✅ نام و کانالتان دیده می‌شود | ❌ |
| ستاره گرفتن | ✅ | ❌ |
| رقبا کد را می‌بینند | ⚠️ بله | ✅ نه |
| به‌روزرسانی خودکار | بدون توکن | نیاز به توکن |

**پیشنهاد من:** اگر می‌خواهید برند Nexora دیده شود و اعتبار فنی بسازید، **Public**. اگر نگران کپی‌شدن توسط رقبا هستید، **Private**.

---

## به‌روزرسانی خودکار از گیت‌هاب

بعد از آپلود، دستور `nexora update` می‌تواند مستقیم از گیت‌هاب بگیرد:

### برای ریپازیتوری عمومی

روی سرور، فایل تنظیمات را بسازید:
```bash
echo 'GITHUB_REPO="nexora-technology-v/nexora-subscription-manager"' > /opt/nexora-panel/.github
```

سپس:
```bash
nexora update
```
بدون هیچ فایلی — خودش آخرین Release را دانلود و نصب می‌کند.

### برای ریپازیتوری خصوصی

اول یک توکن بسازید:
1. گیت‌هاب → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. **Generate new token** → فقط دسترسی `repo` را تیک بزنید
3. توکن را کپی کنید

روی سرور:
```bash
cat > /opt/nexora-panel/.github << 'EOF'
GITHUB_REPO="nexora-technology-v/nexora-subscription-manager"
GITHUB_TOKEN="ghp_توکن_شما"
EOF
chmod 600 /opt/nexora-panel/.github
```

⚠️ `chmod 600` مهم است — این توکن دسترسی کامل به ریپازیتوری‌های شما دارد.

---

## بعد از هر تغییر در آینده

```bash
git add .
git commit -m "توضیح تغییر"
git push
```

و اگر نسخه‌ی جدید است، یک Release جدید هم بسازید تا `nexora update` آن را ببیند.
