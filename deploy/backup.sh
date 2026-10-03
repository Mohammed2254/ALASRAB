#!/usr/bin/env bash
# نسخةٌ احتياطية مضغوطة من القاعدة — و-٢١.
#
# `ARCHITECTURE.md §٨` يقول «نسخة القاعدة من المنصّة المستضيفة»، ولم تكن
# ثمّة آليةٌ مبنيّة. وهذا **الحدّ الأدنى المعقول**، لا نظام نسخٍ كامل:
# نسخةٌ يوميّة محليّة تُبقي آخر أسبوعين.
#
# **ونسخةٌ على القرص نفسه ليست نسخةً احتياطية.** انقلها خارج الخادم —
# سطرٌ في `cron` بـ`rclone`/`scp` كافٍ، ويبقى قرارَ صاحب الخادم.
#
# cron اليوميّ (٣:١٥ فجرًا):
#   15 3 * * * cd $HOME/asrab-v2 && ./deploy/backup.sh >> ~/asrab-backup.log 2>&1

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ASRAB_BACKUP_DIR:-$HOME/asrab-backups}"
KEEP_DAYS="${ASRAB_BACKUP_KEEP_DAYS:-14}"

cd "$DIR"
mkdir -p "$OUT"
FILE="$OUT/asrab-$(date +%F-%H%M).sql.gz"

# `-T` بلا طرفية — وإلّا فشل الأمر داخل cron.
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  exec -T db pg_dump -U asrab asrab_v2 | gzip > "$FILE"

# **فحصٌ أن الملفّ ليس فارغًا**: `pg_dump` الفاشل عبر أنبوبٍ يُنتج ملفًّا
# صالح الشكل وفارغ المحتوى، فتُكتشَف الكارثة يوم الاستعادة لا يوم النسخ.
if [ "$(gzip -dc "$FILE" | head -c 64 | wc -c)" -lt 32 ]; then
  rm -f "$FILE"
  echo "⛔ النسخة فارغة — لم تُحفَظ. راجع حاوية القاعدة." >&2
  exit 1
fi

echo "✅ $FILE ($(du -h "$FILE" | cut -f1))"
find "$OUT" -name 'asrab-*.sql.gz' -mtime "+$KEEP_DAYS" -delete
