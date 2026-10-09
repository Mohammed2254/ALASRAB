#!/usr/bin/env bash
#
# بوّابة تتبّع **المتطلَّبات** — `SCOPE.md §١٢`.
#
# شقيقةُ `check-slice-gate.sh` بالشكل نفسه، وسببُ وجودها فجوةٌ مقيسة:
# المعايير (`ق-N`) محروسةٌ بالكامل منذ و-١ (٢٧٥/٢٧٥)، و**المتطلَّبات
# (`FR-NNN`) كانت بلا بوّابةٍ واحدة**. و`TRACEABILITY.md` — الجسر بينهما —
# كان آخرُ تعديلٍ له ٧ سبتمبر و`SCOPE.md` عُدِّل ٤ أكتوبر.
#
# **والفرقُ بين البوّابتين جوهريّ:** `ق` تقيس «هل اختبرتُ ما قلتُ إنّي
# سأختبره» — وهي قائمةٌ يختارها كاتبُ الشريحة. و`FR` تقيس «هل المنتج مكتمل».
# فـ«٢٧٥/٢٧٥ أخضر» كان يُقرأ اكتمالًا وهو ليس كذلك، وثمنُه دُفع:
#
#   · لا بندَ واحدًا لإنشاء طالب ⇒ قاعدةٌ منشورة لا يدخلها أحد (و-٢١).
#   · `FR-060` بندٌ MUST وشاشتُه ميتةٌ بالتصميم حتى و-٢١.
#   · حدُّ `/notes` موثَّقٌ في `API.md` وغيرُ مبنيّ من و-٤ إلى و-٢١.
#
# العلاقة المفروضة:   متطلَّب  →  مالك تنفيذ معلَن  →  كود
#
#   · المصدر الوحيد للمتطلَّبات: جدول `FR` في `docs/product/SCOPE.md`.
#   · المصدر الوحيد للتنفيذ: وسم `@implements FR-NNN` داخل الكود نفسه.
#   · متطلَّبٌ `MUST`/`SHOULD` بلا مالك ⇒ سقوط.
#   · ومالكٌ يعلن متطلَّبًا غير معلَن ⇒ سقوط.
#
# **و`COULD`/`FUTURE` مُعفاةٌ بمفردات الوثيقة نفسها** لا باستثناءٍ نكتبه هنا:
# هما مستوى «يُؤجَّل بقرار»، فإلزامُهما يجعل الإعفاء قرارَ سكربتٍ لا قرارَ
# منتج. ومتطلَّبٌ يُراد تأجيلُه يُنزَّل مستواه في `SCOPE.md` **صراحةً** —
# فيُرى التأجيل في الوثيقة لا في صمت البوّابة.
#
# @covers ق-٢٨٤
set -uo pipefail
export LC_ALL=C.UTF-8

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCOPE="$ROOT/docs/product/SCOPE.md"

[ -f "$SCOPE" ] || { echo "❌ لا $SCOPE — جذرٌ خاطئ أو ملفٌّ مفقود"; exit 2; }

# مواضع المالكين. والمجلّد الغائب يُتخطّى لا يُسقِط (نفس عُرف بوّابة `ق`)،
# والحارسُ الحقيقيّ ضدّ الفراغ هو `MIN_FR` أدناه.
SEARCH=()
for d in "$ROOT/api/app" "$ROOT/api/tests" "$ROOT/ui/src" "$ROOT/scripts" "$ROOT/ui/scripts"; do
  [ -d "$d" ] && SEARCH+=("$d")
done
[ ${#SEARCH[@]} -eq 0 ] && { echo "❌ لا مجلّد مصدرٍ واحد — جذرٌ خاطئ"; exit 2; }

# حارس الفراغ: استخراجٌ دونه **عطلٌ في الفحص لا نجاحٌ له**. وقد وقع هذا فعلًا
# في بوّابة `ق` عند بنائها (محليّةٌ فاشلة أعطت ✅ على لا شيء).
MIN_FR=40

# ═══ المتطلَّبات المُلزِمة: من جدول `FR` وحده ═══
#
# `| FR-001 | وصف | MUST | ط-١ |` — والحقلُ الثالث هو المستوى.
# والنطاق محصورٌ بالجدول: `MUST` تظهر في جدول الميزات (§٨) أيضًا، فقراءةُ
# الملفّ كلّه تخلط عددَين مختلفين.
binding=$(grep -oE '^\| (FR-[0-9]+[^|]*)\|[^|]*\|[[:space:]]*(MUST|SHOULD)[[:space:]]*\|' "$SCOPE" \
          | grep -oE 'FR-[0-9]+' | sort -u)
exempt=$(grep -oE '^\| (FR-[0-9]+[^|]*)\|[^|]*\|[[:space:]]*(COULD|FUTURE)[[:space:]]*\|' "$SCOPE" \
         | grep -oE 'FR-[0-9]+' | sort -u)
all_declared=$(printf '%s\n%s\n' "$binding" "$exempt" | grep -c . || true)

implemented=$(grep -rhoE "@implements +FR-[0-9]+(, *FR-[0-9]+)*" "${SEARCH[@]}" 2>/dev/null \
              | grep -oE 'FR-[0-9]+' | sort -u)

n_binding=$(printf '%s\n' "$binding" | grep -c . || true)
n_exempt=$(printf '%s\n' "$exempt" | grep -c . || true)
n_impl=$(printf '%s\n' "$implemented" | grep -c . || true)

echo "═══ تتبّع بوّابة المتطلَّبات ═══"
echo "  متطلَّبات معلَنة      : $all_declared"
echo "  منها مُلزِمة (MUST/SHOULD): $n_binding"
echo "  ومُعفاة (COULD/FUTURE)  : $n_exempt"
echo "  لها مالكُ تنفيذ معلَن   : $n_impl"

if [ "$all_declared" -lt "$MIN_FR" ]; then
  echo "  ❌ استُخرج $all_declared متطلَّبًا فقط (الحدّ الأدنى $MIN_FR)."
  echo "     إمّا حُذفت متطلَّبات، وإمّا انكسر الاستخراج — وكلاهما يوقف البوابة."
  exit 2
fi

status=0
missing=$(comm -23 <(printf '%s\n' "$binding") <(printf '%s\n' "$implemented"))
orphan=$(comm -13 <(printf '%s\n%s\n' "$binding" "$exempt" | sort -u) <(printf '%s\n' "$implemented"))

if [ -n "$missing" ]; then
  echo
  echo "  ❌ متطلَّبات مُلزِمة بلا مالك تنفيذ:"
  while read -r fr; do
    [ -z "$fr" ] && continue
    desc=$(grep -m1 "^| $fr |" "$SCOPE" | awk -F'|' '{print $3}' | sed 's/^ *//;s/ *$//')
    printf '     %-8s %s\n' "$fr" "${desc:0:72}"
  done <<< "$missing"
  echo
  echo "     ⇒ إمّا تُنفَّذ ويُوسَم مالكُها بـ@implements، وإمّا يُنزَّل مستواها"
  echo "       في SCOPE.md إلى COULD/FUTURE **صراحةً** — ولا ثالثَ لهما."
  status=1
fi

if [ -n "$orphan" ]; then
  echo
  echo "  ❌ وسوم تدّعي تنفيذ متطلَّبٍ غير معلَن في SCOPE.md:"
  printf '%s\n' "$orphan" | sed 's/^/     /'
  status=1
fi

[ $status -ne 0 ] && exit $status

echo
echo "  ✅ كل متطلَّبٍ مُلزِم له مالك، وكل مالكٍ يعلن متطلَّبًا قائمًا."

# `--list` يطبع الخريطة — **تُولَّد ولا تُكتب بيد.** و`TRACEABILITY.md` كان
# مصفوفةً يدوية تعفّنت شهرًا (كانت تقول إن مسار `FR-004` هو
# `PATCH /admin/teams`، والحقيقة `POST /admin/users/{id}/reset-pin`).
# ومعلومةٌ قديمة أسوأ من غيابها.
[ "${1:-}" = "--list" ] || exit 0

echo
echo "  المتطلَّب → المالك:"
for fr in $(printf '%s\n%s\n' "$binding" "$exempt" | sort -u); do
  [ -z "$fr" ] && continue
  level=$(grep -m1 "^| $fr |" "$SCOPE" | awk -F'|' '{gsub(/ /,"",$4); print $4}')
  owner=$(grep -rlE "@implements[^$]*\b$fr\b" "${SEARCH[@]}" 2>/dev/null \
          | head -1 | sed "s|$ROOT/||")
  printf '    %-8s %-7s %s\n' "$fr" "${level:-—}" "${owner:-— بلا مالك (مُعفًى)}"
done
