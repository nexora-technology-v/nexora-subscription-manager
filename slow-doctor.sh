#!/usr/bin/env bash
#
# چرا سرور و ربات کند هستند؟
#
# این اسکریپت حدس نمی‌زند — اندازه می‌گیرد. هر بخش یک عدد واقعی از
# همین سرور می‌دهد و می‌گوید آن عدد از کجا به بعد بد است.
#
# اجرا:  sudo bash slow-doctor.sh
#
set -u

R=$'\e[38;5;203m'; G=$'\e[38;5;42m'; Y=$'\e[38;5;220m'
D=$'\e[38;5;245m'; W=$'\e[1m'; X=$'\e[0m'

ok()   { echo "  ${G}✓${X} $1"; }
warn() { echo "  ${Y}!${X} $1"; }
bad()  { echo "  ${R}✗${X} $1"; }
info() { echo "    ${D}$1${X}"; }
head() { echo ""; echo "${W}$1${X}"; echo "${D}────────────────────────────────────────────${X}"; }

echo ""
echo "${W}تشخیص کندی — نکسورا${X}"
echo "${D}$(date '+%Y-%m-%d %H:%M')${X}"

# ═══ ۱. بار سیستم ═══
head "۱. بار پردازنده"
CORES=$(nproc 2>/dev/null || echo 1)
LOAD=$(awk '{print $1}' /proc/loadavg 2>/dev/null || echo 0)
RATIO=$(awk -v l="$LOAD" -v c="$CORES" 'BEGIN{printf "%.2f", l/c}')
echo "  بار ۱ دقیقه: ${W}$LOAD${X}   هسته: $CORES   نسبت: ${W}$RATIO${X}"
if awk -v r="$RATIO" 'BEGIN{exit !(r>1.5)}'; then
  bad "پردازنده اشباع است — همین تنهایی همه‌چیز را کند می‌کند"
  info "پرمصرف‌ترین پردازه‌ها:"
  ps -eo pcpu,pmem,comm --sort=-pcpu 2>/dev/null | head -6 | sed 's/^/      /'
elif awk -v r="$RATIO" 'BEGIN{exit !(r>0.8)}'; then
  warn "بار بالاست ولی هنوز بحرانی نیست"
else
  ok "بار پردازنده سالم است"
fi

# ═══ ۲. حافظه و swap ═══
head "۲. حافظه"
if [ -r /proc/meminfo ]; then
  MT=$(awk '/MemTotal/{print $2}' /proc/meminfo)
  MA=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
  ST=$(awk '/SwapTotal/{print $2}' /proc/meminfo)
  SF=$(awk '/SwapFree/{print $2}' /proc/meminfo)
  USED=$(( (MT - MA) * 100 / MT ))
  echo "  مصرف حافظه: ${W}${USED}%${X}  (آزاد: $((MA/1024)) MB از $((MT/1024)) MB)"
  if [ "$USED" -ge 90 ]; then
    bad "حافظه تقریباً پر است — کرنل مدام در حال جابه‌جایی است"
  elif [ "$USED" -ge 75 ]; then
    warn "حافظه رو به پرشدن"
  else
    ok "حافظه کافی است"
  fi
  if [ "${ST:-0}" -gt 0 ]; then
    SU=$(( (ST - SF) * 100 / ST ))
    if [ "$SU" -ge 20 ]; then
      bad "swap ${SU}% پر است — این مستقیماً یعنی کندی شدید"
      info "سرور دارد از دیسک به‌جای رم استفاده می‌کند"
    else
      ok "swap تقریباً دست‌نخورده (${SU}%)"
    fi
  fi
fi

# ═══ ۳. دیسک ═══
head "۳. دیسک"
df -h / 2>/dev/null | awk 'NR==2{printf "  ریشه: %s از %s مصرف شده (%s)\n", $3, $2, $5}'
DPCT=$(df / 2>/dev/null | awk 'NR==2{gsub("%","",$5); print $5}')
[ "${DPCT:-0}" -ge 90 ] && bad "دیسک پر است — SQLite و لاگ‌ها کند می‌شوند" \
                        || ok "فضای دیسک کافی است"

echo ""
echo "  سرعت نوشتن دیسک:"
DD=$(dd if=/dev/zero of=/tmp/.nx-io bs=1M count=64 oflag=direct 2>&1 | tail -1)
rm -f /tmp/.nx-io
echo "    ${D}${DD}${X}"
SPD=$(echo "$DD" | grep -oE '[0-9.]+ [MG]B/s' | tail -1)
case "$SPD" in
  *GB/s) ok "دیسک سریع است" ;;
  *MB/s)
    NUM=$(echo "$SPD" | grep -oE '^[0-9.]+')
    if awk -v n="$NUM" 'BEGIN{exit !(n<50)}'; then
      bad "دیسک کند است ($SPD) — دیتابیس ربات روی همین است"
      info "هر خواندن تنظیمات یک عملیات دیسک است"
    else
      ok "سرعت دیسک قابل قبول ($SPD)"
    fi ;;
esac

# ═══ ۴. سرویس‌ها ═══
head "۴. سرویس‌ها"
for s in nexora-panel nexora-bot x-ui nginx; do
  if systemctl list-unit-files 2>/dev/null | grep -q "^$s"; then
    ST=$(systemctl is-active "$s" 2>/dev/null)
    RS=$(systemctl show "$s" -p NRestarts --value 2>/dev/null || echo 0)
    MEM=$(systemctl show "$s" -p MemoryCurrent --value 2>/dev/null)
    MEM_MB="?"
    [ "${MEM:-0}" -gt 0 ] 2>/dev/null && MEM_MB=$((MEM/1024/1024))
    if [ "$ST" = "active" ]; then
      if [ "${RS:-0}" -gt 5 ]; then
        warn "$s روشن است ولی ${RS} بار ری‌استارت شده — ناپایدار (${MEM_MB}MB)"
      else
        ok "$s روشن — ${MEM_MB}MB حافظه"
      fi
    else
      bad "$s وضعیت: $ST"
    fi
  fi
done

# ═══ ۵. اتصال به تلگرام ═══
head "۵. تأخیر تا تلگرام"
info "کندی ربات بیشتر از هر چیزی به این بستگی دارد"
T=$(curl -o /dev/null -s -w '%{time_connect} %{time_total}' \
      -m 15 https://api.telegram.org 2>/dev/null)
if [ -n "$T" ]; then
  TC=$(echo "$T" | awk '{print $1}')
  TT=$(echo "$T" | awk '{print $2}')
  echo "  اتصال: ${W}${TC}s${X}   کل: ${W}${TT}s${X}"
  if awk -v t="$TT" 'BEGIN{exit !(t>2)}'; then
    bad "تأخیر تا تلگرام خیلی زیاد است"
    info "هر پیام ربات دست‌کم همین‌قدر طول می‌کشد"
    info "اگر سرور ایران است، تانل یا پروکسی برای ربات لازم دارید"
  elif awk -v t="$TT" 'BEGIN{exit !(t>0.8)}'; then
    warn "تأخیر محسوس است — ربات کند حس می‌شود"
  else
    ok "تأخیر تا تلگرام خوب است"
  fi
else
  bad "تلگرام از این سرور در دسترس نیست"
  info "ربات اصلاً نمی‌تواند کار کند"
fi

# ═══ ۶. دیتابیس ربات ═══
head "۶. دیتابیس ربات"
for p in /opt/nexora/data/bot.db /opt/nexora-panel/data/bot.db; do
  [ -f "$p" ] || continue
  SZ=$(du -h "$p" | cut -f1)
  echo "  $p  (${W}${SZ}${X})"
  if command -v sqlite3 >/dev/null 2>&1; then
    U=$(sqlite3 "$p" "SELECT COUNT(*) FROM users" 2>/dev/null || echo ?)
    O=$(sqlite3 "$p" "SELECT COUNT(*) FROM orders" 2>/dev/null || echo ?)
    S=$(sqlite3 "$p" "SELECT COUNT(*) FROM subscriptions" 2>/dev/null || echo ?)
    JM=$(sqlite3 "$p" "PRAGMA journal_mode" 2>/dev/null || echo ?)
    echo "    کاربران: $U   سفارش‌ها: $O   اشتراک‌ها: $S"
    echo "    journal_mode: ${W}${JM}${X}"
    if [ "$JM" = "wal" ]; then
      ok "WAL روشن است — خواندن و نوشتن هم‌زمان قفل نمی‌شوند"
    else
      warn "WAL خاموش است"
      info "با کاربر زیاد، هر نوشتن کل دیتابیس را قفل می‌کند"
      info "روشن‌کردن:  sqlite3 $p 'PRAGMA journal_mode=WAL;'"
    fi
  fi
  break
done

# ═══ ۷. اتصال‌ها ═══
head "۷. اتصال‌های فعال"
if command -v ss >/dev/null 2>&1; then
  TOT=$(ss -tunH state established 2>/dev/null | wc -l)
  echo "  کل اتصال‌های برقرار: ${W}${TOT}${X}"
  echo "  پرمصرف‌ترین آی‌پی‌ها:"
  ss -tunH state established 2>/dev/null \
    | awk '{print $5}' | sed 's/:[0-9]*$//' | tr -d '[]' \
    | grep -vE '^(127\.0\.0\.1|::1)$' | sort | uniq -c | sort -rn | head -5 \
    | awk '{printf "      %-42s %s اتصال\n", $2, $1}'
  [ "$TOT" -gt 2000 ] && warn "تعداد اتصال‌ها بالاست — بار شبکه سنگین است"
fi

# ═══ خلاصه ═══
head "چه چیزی را بفرستید"
info "کل همین خروجی را کپی کنید و بفرستید."
info "خط‌های ✗ قرمز مهم‌ترین‌اند — از آن‌ها شروع می‌کنیم."
echo ""
