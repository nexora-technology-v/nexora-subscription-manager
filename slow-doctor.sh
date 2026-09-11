#!/usr/bin/env bash
#
# Why is the server slow?
#
# This does not guess. It measures, and for every number it says where
# the line between fine and bad actually is.
#
# Run:  sudo bash slow-doctor.sh
#
set -u

R=$'\e[38;5;203m'; G=$'\e[38;5;42m'; Y=$'\e[38;5;220m'
D=$'\e[38;5;245m'; W=$'\e[1m'; X=$'\e[0m'

ok()   { echo "  ${G}OK${X}   $1"; }
warn() { echo "  ${Y}WARN${X} $1"; }
bad()  { echo "  ${R}BAD${X}  $1"; }
info() { echo "       ${D}$1${X}"; }
head() { echo ""; echo "${W}$1${X}"; echo "${D}──────────────────────────────────────────────${X}"; }

echo ""
echo "${W}Nexora — slowness report${X}"
echo "${D}$(date '+%Y-%m-%d %H:%M')  ·  $(hostname)${X}"

# ═══ 1. CPU ═══
head "1. CPU load"
CORES=$(nproc 2>/dev/null || echo 1)
LOAD1=$(awk '{print $1}' /proc/loadavg 2>/dev/null || echo 0)
LOAD5=$(awk '{print $2}' /proc/loadavg 2>/dev/null || echo 0)
RATIO=$(awk -v l="$LOAD1" -v c="$CORES" 'BEGIN{printf "%.2f", l/c}')
echo "  load 1min: ${W}$LOAD1${X}   5min: $LOAD5   cores: $CORES"
echo "  load per core: ${W}$RATIO${X}   ${D}(1.00 = fully busy)${X}"

if awk -v r="$RATIO" 'BEGIN{exit !(r>1.5)}'; then
  bad "CPU is saturated — this alone makes everything slow"
elif awk -v r="$RATIO" 'BEGIN{exit !(r>0.7)}'; then
  warn "CPU is working hard; little headroom left for spikes"
else
  ok "CPU has headroom"
fi

echo ""
echo "  ${D}Top CPU consumers:${X}"
ps -eo pcpu,pmem,rss,comm --sort=-pcpu 2>/dev/null | head -7 \
  | awk 'NR==1{printf "       %-6s %-6s %-9s %s\n","%CPU","%MEM","RSS","COMMAND"; next}
         {printf "       %-6s %-6s %-9s %s\n", $1, $2, int($3/1024)"M", $4}'

# ═══ 2. Memory ═══
head "2. Memory"
if [ -r /proc/meminfo ]; then
  MT=$(awk '/MemTotal/{print $2}' /proc/meminfo)
  MA=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
  ST=$(awk '/SwapTotal/{print $2}' /proc/meminfo)
  SF=$(awk '/SwapFree/{print $2}' /proc/meminfo)
  USED=$(( (MT - MA) * 100 / MT ))
  echo "  used: ${W}${USED}%${X}   free: $((MA/1024)) MB of $((MT/1024)) MB"
  if   [ "$USED" -ge 90 ]; then bad "memory nearly exhausted — the kernel is thrashing"
  elif [ "$USED" -ge 75 ]; then warn "memory filling up"
  else ok "plenty of memory"; fi

  if [ "${ST:-0}" -gt 0 ]; then
    SU=$(( (ST - SF) * 100 / ST ))
    if [ "$SU" -ge 20 ]; then
      bad "swap is ${SU}% used — the server is paging to disk"
    else
      ok "swap barely touched (${SU}%)"
    fi
  else
    info "no swap configured"
  fi
fi

# ═══ 3. Disk ═══
head "3. Disk"
df -h / 2>/dev/null | awk 'NR==2{printf "  root: %s of %s used (%s)\n", $3, $2, $5}'
DPCT=$(df / 2>/dev/null | awk 'NR==2{gsub("%","",$5); print $5}')
if [ "${DPCT:-0}" -ge 90 ]; then bad "disk almost full — SQLite and logs suffer"
else ok "disk space is fine"; fi

DD=$(dd if=/dev/zero of=/tmp/.nx-io bs=1M count=64 oflag=direct 2>&1 | tail -1)
rm -f /tmp/.nx-io
echo "  write: ${D}${DD}${X}"
case "$DD" in
  *GB/s) ok "disk is fast" ;;
  *MB/s)
    NUM=$(echo "$DD" | grep -oE '[0-9.]+ MB/s' | grep -oE '^[0-9.]+')
    if awk -v n="${NUM:-999}" 'BEGIN{exit !(n<50)}'; then
      bad "disk is slow — the bot database lives here"
    else ok "disk speed acceptable"; fi ;;
esac

# ═══ 4. Services ═══
head "4. Services"
for s in nexora-panel nexora-bot x-ui nginx; do
  systemctl list-unit-files 2>/dev/null | grep -q "^$s" || continue
  ST=$(systemctl is-active "$s" 2>/dev/null)
  RS=$(systemctl show "$s" -p NRestarts --value 2>/dev/null || echo 0)
  MEM=$(systemctl show "$s" -p MemoryCurrent --value 2>/dev/null)
  MB="?"; [ "${MEM:-0}" -gt 0 ] 2>/dev/null && MB=$((MEM/1024/1024))
  if [ "$ST" != "active" ]; then
    bad "$s is $ST"
  elif [ "${RS:-0}" -gt 5 ]; then
    warn "$s up but restarted ${RS} times — unstable (${MB}MB)"
  else
    ok "$s up — ${MB}MB"
  fi
done

# ═══ 5. Telegram latency ═══
head "5. Telegram latency"
info "this dominates how fast the bot feels"
T=$(curl -o /dev/null -s -w '%{time_connect} %{time_total}' -m 15 \
      https://api.telegram.org 2>/dev/null)
if [ -n "$T" ]; then
  TC=$(echo "$T" | awk '{print $1}'); TT=$(echo "$T" | awk '{print $2}')
  echo "  connect: ${W}${TC}s${X}   total: ${W}${TT}s${X}"
  if   awk -v t="$TT" 'BEGIN{exit !(t>2)}';   then
    bad "very high latency — every bot reply costs at least this"
    info "if this server is in Iran, the bot needs a tunnel or proxy"
  elif awk -v t="$TT" 'BEGIN{exit !(t>0.8)}'; then
    warn "noticeable latency — the bot will feel sluggish"
  else ok "latency to Telegram is good"; fi
else
  bad "Telegram unreachable from this server — the bot cannot work"
fi

# ═══ 6. Bot database ═══
head "6. Bot database"
BOTDB=""
for p in /opt/nexora/data/bot.db /opt/nexora-panel/data/bot.db; do
  [ -f "$p" ] && BOTDB="$p" && break
done
if [ -n "$BOTDB" ]; then
  echo "  $BOTDB  (${W}$(du -h "$BOTDB" | cut -f1)${X})"
  if command -v sqlite3 >/dev/null 2>&1; then
    U=$(sqlite3 "$BOTDB" "SELECT COUNT(*) FROM users" 2>/dev/null || echo ?)
    O=$(sqlite3 "$BOTDB" "SELECT COUNT(*) FROM orders" 2>/dev/null || echo ?)
    S=$(sqlite3 "$BOTDB" "SELECT COUNT(*) FROM subscriptions WHERE is_active=1" 2>/dev/null || echo ?)
    JM=$(sqlite3 "$BOTDB" "PRAGMA journal_mode" 2>/dev/null || echo ?)
    echo "  users: $U   orders: $O   active subs: $S   journal: ${W}${JM}${X}"
    if [ "$JM" = "wal" ]; then
      ok "WAL on — readers and writers do not block each other"
    else
      warn "WAL off — every write locks the whole database"
      info "fix: sqlite3 $BOTDB 'PRAGMA journal_mode=WAL;' && systemctl restart nexora-bot"
    fi
  fi
else
  info "bot database not found"
fi

# ═══ 7. Connections ═══
head "7. Active connections"
if command -v ss >/dev/null 2>&1; then
  # ss -tun with a state filter drops the State column, so the peer is
  # the last field. Using $NF instead of a fixed index is what makes
  # this work for both tcp and udp rows, and for IPv6.
  RAW=$(ss -tunH state established 2>/dev/null)
  TOT=$(printf '%s\n' "$RAW" | grep -c . )
  echo "  established: ${W}${TOT}${X}"

  PEERS=$(printf '%s\n' "$RAW" | awk 'NF>=5 {print $NF}' \
          | sed -E 's/:[0-9]+$//; s/^\[//; s/\]$//' \
          | grep -vE '^(127\.0\.0\.1|::1|\*|0\.0\.0\.0|)$')

  UNIQ=$(printf '%s\n' "$PEERS" | sort -u | grep -c .)
  echo "  unique peer IPs: ${W}${UNIQ}${X}"

  if [ "$UNIQ" -gt 0 ]; then
    echo ""
    echo "  ${D}Busiest peers:${X}"
    printf '%s\n' "$PEERS" | sort | uniq -c | sort -rn | head -8 \
      | awk -v tot="$TOT" '{
          pct = tot>0 ? ($1*100/tot) : 0
          printf "       %-40s %6d  (%.1f%%)\n", $2, $1, pct
        }'

    TOPN=$(printf '%s\n' "$PEERS" | sort | uniq -c | sort -rn | head -1 | awk '{print $1}')
    TOPIP=$(printf '%s\n' "$PEERS" | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')
    if [ "${TOPN:-0}" -gt 0 ] && [ "$TOT" -gt 0 ]; then
      SHARE=$(awk -v n="$TOPN" -v t="$TOT" 'BEGIN{printf "%.0f", n*100/t}')
      if [ "$SHARE" -ge 30 ]; then
        warn "$TOPIP holds ${SHARE}% of all connections"
        info "if that is your own tunnel node, this is expected"
        info "otherwise: one account shared widely, or a scan"
      fi
    fi
  fi

  echo ""
  echo "  ${D}Busiest local ports:${X}"
  printf '%s\n' "$RAW" | awk 'NF>=5 {print $(NF-1)}' \
    | sed -E 's/.*:([0-9]+)$/\1/' | sort | uniq -c | sort -rn | head -6 \
    | awk '{printf "       port %-8s %6d\n", $2, $1}'

  # Connections per active subscription tells you whether the count is
  # normal customer usage or something else entirely.
  if [ -n "${S:-}" ] && [ "${S:-0}" -gt 0 ] 2>/dev/null; then
    PER=$(awk -v c="$TOT" -v s="$S" 'BEGIN{printf "%.0f", c/s}')
    echo ""
    echo "  ${W}${PER}${X} connections per active subscription  ${D}(${TOT} / ${S})${X}"
    if [ "$PER" -gt 200 ]; then
      bad "far more connections than your subscriptions can explain"
      info "likely a scan, or configs in use that the bot does not know about"
    elif [ "$PER" -gt 60 ]; then
      warn "high per subscription — normal for heavy use, worth a look"
    else
      ok "in the normal range for VPN traffic"
    fi
    info "note: clients added directly in x-ui are not counted here"
  fi

  if [ "$TOT" -gt 2000 ]; then
    echo ""
    warn "over 2000 established connections — this is what your CPU is doing"
    info "each one costs Xray memory and scheduling time"
  fi
fi

# ═══ 8. Xray ═══
head "8. Xray"
XPID=$(pgrep -x xray 2>/dev/null | head -1)
if [ -n "$XPID" ]; then
  XFD=$(ls /proc/"$XPID"/fd 2>/dev/null | wc -l)
  XLIM=$(awk '/Max open files/{print $4}' /proc/"$XPID"/limits 2>/dev/null)
  XMEM=$(awk '/VmRSS/{print int($2/1024)}' /proc/"$XPID"/status 2>/dev/null)
  echo "  pid $XPID   memory: ${W}${XMEM:-?}MB${X}   open files: ${W}${XFD}${X} / ${XLIM:-?}"
  if [ -n "$XLIM" ] && [ "$XLIM" != "unlimited" ] && [ "${XFD:-0}" -gt 0 ]; then
    PCT=$(( XFD * 100 / XLIM ))
    if [ "$PCT" -ge 80 ]; then
      bad "file descriptors ${PCT}% used — new connections will start failing"
      info "raise LimitNOFILE in the x-ui service unit"
    elif [ "$PCT" -ge 50 ]; then
      warn "file descriptors ${PCT}% used"
    else
      ok "file descriptor headroom is fine"
    fi
  fi
else
  info "xray process not found under that name"
fi

head "What to send"
info "Copy this whole output. BAD lines come first, WARN next."
echo ""
