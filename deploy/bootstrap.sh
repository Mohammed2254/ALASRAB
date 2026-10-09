#!/usr/bin/env bash
# تجهيز خادم جديد لتشغيل «الأسراب» — و-٢١.
#
# يُشغَّل **مرّةً واحدة** على خادم Ubuntu/Debian نظيف، بمستخدمٍ له sudo.
# وما بعده تحديثٌ بأمرين لا أكثر (`docs/DEPLOY.md §٧`).
#
#   curl -fsSL https://raw.githubusercontent.com/Mohammed2254/ALASRAB/main/deploy/bootstrap.sh | bash
#
# **لا يلمس الأسرار ولا ينشئها:** يتوقّف ويطلب `.env.prod` بيدك. سكربتٌ
# يولّد كلمات مرور ويطبعها في سجلّ الطرفية يُسرّبها إلى تاريخ الأوامر.

set -euo pipefail

REPO="${ASRAB_REPO:-https://github.com/Mohammed2254/ALASRAB.git}"
DIR="${ASRAB_DIR:-$HOME/asrab-v2}"
COMPOSE="docker compose -f docker-compose.prod.yml --env-file .env.prod"

say() { printf '\n\033[1m›\033[0m %s\n' "$*"; }
die() { printf '\n\033[31m⛔ %s\033[0m\n' "$*" >&2; exit 1; }

# ٠ — تصليب الخادم: ثلاثة أشياء تقرّر هل يصمد خادمٌ صغير بلا رقيب
#
# · **تحديثاتٌ أمنية تلقائية** — خادمٌ لا يُحدَّث يصير مكشوفًا بثغرةٍ معلَنة
#   بعد أسابيع، وأحدٌ لن يدخل شهريًّا ليُحدِّث يدويًّا.
# · **جدارٌ** — Docker يكتب في `iptables` مباشرةً ويتجاوز UFW للمنافذ
#   المنشورة، فالجدار هنا يحرس **ما عدا** الحاويات: SSH وما قد يُفتح سهوًا.
# · **تدوير سجلّات Docker** — في `docker-compose.prod.yml`، وهنا افتراضٌ
#   على مستوى العفريت ليشمل أيّ حاويةٍ تُشغَّل يدويًّا.
harden_host() {
  say "تصليب الخادم (تحديثات · جدار · سجلّات)"

  if command -v apt-get >/dev/null 2>&1; then
    sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq || true
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
      unattended-upgrades ufw ca-certificates curl || true
    # التفعيل غير التفاعليّ — `dpkg-reconfigure` يسأل، وcURL لا يجيب.
    printf 'APT::Periodic::Update-Package-Lists "1";\nAPT::Periodic::Unattended-Upgrade "1";\n' \
      | sudo tee /etc/apt/apt.conf.d/20auto-upgrades >/dev/null
  fi

  if command -v ufw >/dev/null 2>&1 && ! sudo ufw status | grep -q '^Status: active'; then
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw allow 22/tcp    comment 'SSH'
    sudo ufw allow 80/tcp    comment 'HTTP — تحويل Caddy وتحدّي الشهادة'
    sudo ufw allow 443/tcp   comment 'HTTPS'
    sudo ufw --force enable
  fi

  # افتراضُ العفريت: سقفٌ لأيّ حاوية لا يشملها `x-logging`.
  if [ ! -f /etc/docker/daemon.json ]; then
    sudo mkdir -p /etc/docker
    printf '{\n  "log-driver": "json-file",\n  "log-opts": { "max-size": "10m", "max-file": "3" }\n}\n' \
      | sudo tee /etc/docker/daemon.json >/dev/null
    sudo systemctl restart docker 2>/dev/null || true
  fi
}

# ١ — دوكر
if ! command -v docker >/dev/null 2>&1; then
  say "تثبيت دوكر"
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
  say "أُضِفت إلى مجموعة docker — **أعد تسجيل الدخول** ثم شغّل هذا السكربت مرّة أخرى."
  exit 0
fi
docker info >/dev/null 2>&1 || die "دوكر مثبَّت ولا يعمل بلا sudo — أعد تسجيل الدخول أوّلًا."

harden_host

# ٢ — الكود
if [ -d "$DIR/.git" ]; then
  say "تحديث الكود في $DIR"
  git -C "$DIR" pull --ff-only
else
  say "استنساخ $REPO إلى $DIR"
  git clone --depth 1 "$REPO" "$DIR"
fi
cd "$DIR"

# ٣ — الأسرار: يُطلَب ولا يُولَّد
if [ ! -f .env.prod ]; then
  say "لا .env.prod — أنشئه الآن ثم أعد التشغيل:"
  cat <<'TPL'

cat > .env.prod << 'EOF'
DB_PASSWORD=<كلمة مرور طويلة عشوائية>
SECRET_KEY=<الناتج من الأمر أدناه>
DOMAIN=<نطاقك، أو اتركه إن استعملت نفق Cloudflare>
EOF

# لتوليد SECRET_KEY:
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'

TPL
  die "متوقّف عند الأسرار — بقصد."
fi
grep -q 'CHANGE_ME' .env.prod && die ".env.prod ما زال يحمل قيمة CHANGE_ME."

# ٤ — البناء والتشغيل
say "بناء وتشغيل"
$COMPOSE up -d --build

# ٥ — الهجرة: **يدويّة دائمًا ولا تُشغَّل عند كل إعادة تشغيل** (`OPERATIONS.md`)
say "تطبيق الهجرات"
$COMPOSE run --rm app flask db upgrade

# ٦ — التأسيس: على قاعدة فارغة وحدها، ويرفض الثانية
if $COMPOSE run --rm -T app python -c "
from app import create_app
from app.services.provision import org_exists
app = create_app()
with app.app_context():
    raise SystemExit(0 if org_exists() else 1)
" 2>/dev/null; then
  say "توجد جمعية — لا تأسيس. تمّ."
else
  say "قاعدة فارغة — أسِّس الجمعية وأوّل مشرف الآن:"
  printf '\n  cd %s && %s run --rm app flask bootstrap-org\n\n' "$DIR" "$COMPOSE"
  say "الرمز يُعرض **مرّةً واحدة** — اقرأه واحتفظ به."
fi

# ٧ — النسخ الاحتياطيّ **يُجدوَل** لا يُترك لتذكّر أحد: نسخةٌ يدويّة يتذكّرها
# المرء أسبوعين ثم ينساها، وتُكتشَف الكارثة يوم الحاجة.
if ! crontab -l 2>/dev/null | grep -q 'deploy/backup.sh'; then
  say "جدولة نسخةٍ احتياطية يومية (٣:١٥ فجرًا بتوقيت الخادم)"
  (crontab -l 2>/dev/null; echo "15 3 * * * cd $DIR && ./deploy/backup.sh >> \$HOME/asrab-backup.log 2>&1") | crontab -
  say "⚠️ وهي **على القرص نفسه** — انقلها خارج الخادم (rclone/scp)، وإلّا"
  say "   فقدانُ القرص يفقد النسخَ معه."
fi

say "فحص الصحّة"
$COMPOSE exec -T app python -c "
import urllib.request, sys
with urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5) as r:
    print(r.status, r.read().decode())
" || die "الصحّة لم تستجب — راجع: $COMPOSE logs app"
