#!/usr/bin/env bash
#
# بوابة التتبّع الميكانيكي لـ`SLICE-01` §٨.
#
# العلاقة المفروضة:   معيار  →  مالك تحقّق معلَن  →  دليل
#
# **لماذا لا يكفي أن نتذكّر؟** لأن البوابة تُقرأ بالعين: حذفُ اختبارٍ لا يُسقطها،
# فتبقى تقول «مكتملة» بلا تغطية. هذا السكربت يجعل الرابط إلزاميًّا:
#
#   · المصدر الوحيد للمعايير: جدول §٧ في `docs/plans/SLICE-01.md`.
#   · المصدر الوحيد للتغطية: وسم `@covers ق-N` داخل ملفّ التحقّق نفسه.
#   · معيارٌ بلا مالك ⇒ سقوط. ومالكٌ يعلن معيارًا غير معلَن ⇒ سقوط.
#
# **الوسم داخل الملفّ لا في اسمه:** نقلُ اختبارٍ أو إعادة تسميته لا تكسر البوابة،
# وحذفُ وسمه يكسرها — وهو المطلوب.
#
# **ولا نجاح على فراغ:** استخراجٌ يعطي صفر معايير عطلٌ في الفحص لا نجاحٌ له —
# وقد وقع هذا فعلًا عند بناء السكربت (فشل محليّة صامت أعطى ✅ على لا شيء).
set -uo pipefail
export LC_ALL=C.UTF-8   # الأرقام العربية-الهندية متعدّدة البايتات: بلا هذا يفشل النطاق

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SPEC="$ROOT/docs/plans/SLICE-01.md"
SEARCH=("$ROOT/api/tests" "$ROOT/web/src/test" "$ROOT/web/scripts")
# المصدر وحده. الوسم يعيش في الكود المكتوب لا في مخرَجه المترجَم، و`__pycache__`
# يحمل نسخًا قديمة من النصوص التوثيقية. (`grep` يرفض اليوم إخراج مطابقات من ملفّ
# ثنائي فلا تمرير كاذب — لكن الاعتماد على ذلك اعتمادٌ على تفصيل أداة، والنطاق
# الصحيح أصلًا هو المصدر.)
SOURCES=(--include='*.py' --include='*.js' --include='*.jsx' --include='*.mjs' --include='*.sh')
DIGITS='[٠١٢٣٤٥٦٧٨٩]'
MIN_CRITERIA=12   # حارس الفراغ: البوابة لا تمرّ على استخراج فاشل

[ -f "$SPEC" ] || { echo "❌ لا مواصفة في $SPEC"; exit 2; }

declared=$(grep -oE "^\| \*{0,2}ق-$DIGITS+" "$SPEC" | grep -oE "ق-$DIGITS+" | sort -u)
covered=$(grep -rhoE "${SOURCES[@]}" "@covers +ق-$DIGITS+(, *ق-$DIGITS+)*" "${SEARCH[@]}" 2>/dev/null \
          | grep -oE "ق-$DIGITS+" | sort -u)

n_declared=$(printf '%s\n' "$declared" | grep -c . || true)
n_covered=$(printf '%s\n' "$covered" | grep -c . || true)

echo "═══ تتبّع بوابة SLICE-01 §٨ ═══"
echo "  معايير معلَنة في §٧: $n_declared"
echo "  معايير لها مالك:     $n_covered"

if [ "$n_declared" -lt "$MIN_CRITERIA" ]; then
  echo "  ❌ استُخرج $n_declared معيارًا فقط (الحدّ الأدنى $MIN_CRITERIA)."
  echo "     إمّا حُذفت معايير من §٧، وإمّا انكسر الاستخراج — وكلاهما يوقف البوابة."
  exit 1
fi

status=0
missing=$(comm -23 <(printf '%s\n' "$declared") <(printf '%s\n' "$covered"))
orphan=$(comm -13 <(printf '%s\n' "$declared") <(printf '%s\n' "$covered"))

if [ -n "$missing" ]; then
  echo "  ❌ معايير بلا مالك تحقّق:"
  printf '%s\n' "$missing" | sed 's/^/     /'
  status=1
fi
if [ -n "$orphan" ]; then
  echo "  ❌ وسوم تدّعي تغطية معيار غير معلَن في §٧:"
  printf '%s\n' "$orphan" | sed 's/^/     /'
  status=1
fi

[ $status -ne 0 ] && exit $status

echo "  ✅ كل معيار له مالك، وكل مالك يعلن معيارًا قائمًا."
echo
echo "  المعيار → المالك:"
for criterion in $declared; do
  owners=""
  for file in $(grep -rlE "${SOURCES[@]}" "@covers" "${SEARCH[@]}" 2>/dev/null); do
    if grep -oE "@covers +ق-$DIGITS+(, *ق-$DIGITS+)*" "$file" \
       | grep -oE "ق-$DIGITS+" | grep -qx "$criterion"; then
      owners+="$(basename "$file") "
    fi
  done
  printf "    %-7s %s\n" "$criterion" "$owners"
done
