# مصفوفة التتبّع

> **الغرض:** لكل متطلَّب **مسار تنفيذ صريح** — وحدة، وجدول، واختبار، ووحدة عمل.
> **ليس كل متطلَّب يحتاج endpoint مستقلًّا:** بعضها **قيد** يُفرض داخل مسار آخر
> (`FR-021`)، وبعضها **بنية** لا سلوك (`FR-061`). العمود يقول `—` حينها ويُذكر
> المسار الذي يتحقّق فيه.

**السلسلة:** `SCOPE → TRACEABILITY → ARCHITECTURE → DATABASE → RULES → API → SLICE`

---

## المصادقة

| FR | المسار | الوحدة | الجدول | الثابت | الاختبار | وحدة العمل |
|---|---|---|---|:--:|---|:--:|
| FR-001 | `POST /auth/login` | `services/auth` · `security` | `users` `sessions` `login_attempts` | — | رقم صحيح ⇒ كوكي · **رسالة واحدة للحالتين** | **و-١** |
| FR-002 | `POST /auth/logout` · `GET /auth/me` | `services/auth` | `sessions` | — | بعد `logout` نفس الكوكي ⇒ `401` | **و-١** |
| FR-003 | قيد داخل `POST /auth/login` | `services/auth` | `login_attempts` | — | ٦ محاولات ⇒ `429` يذكر المهلة | و-٢ |
| FR-004 | `PATCH /admin/teams` (المستخدم) | `services/auth` | `users` `sessions` `audit_log` | — | إعادة التعيين **تُبطل كل الجلسات** | و-٢ |

## بطاقة الطيار

| FR | المسار | الوحدة | الجدول | الثابت | الاختبار | وحدة العمل |
|---|---|---|---|:--:|---|:--:|
| FR-010 | `GET /me/deck` | `services/deck` · `rules/engine` | `point_events` `weights` `rank_thresholds` | ث-١١ | ٦١٢ ساعة ⇒ «طيار أول» | **و-١** |
| FR-011 | ضمن `/me/deck` | `services/deck` | `rank_thresholds` | — | **٤٢.٥٪ داخل الشريحة لا ٦٨٪ مطلقة** | **و-١** |
| FR-012 | `GET /me/events` | `services/deck` | `point_events` | — | التصحيح يظهر **سالبًا بسببه** | و-٣ |
| FR-013 | ضمن `/me/deck` | `services/readiness` | `point_events` `orgs` | ث-١٤ | ١٥ يومًا بلا حدث ⇒ `grounded` · **لا عمود في المخطط** | **و-١** |

## القراءة

| FR | المسار | الوحدة | الجدول | الثابت | الاختبار | وحدة العمل |
|---|---|---|---|:--:|---|:--:|
| FR-020 | `POST /me/readings` | `services/reading` | `reading_submissions` | — | طلب مكرّر ⇒ `409` | و-٤ |
| FR-021 | **قيد** — لا endpoint | `services/reading` | `reading_submissions` | **ث-٥** | إرسال ⇒ رصيد لم يتغيّر | و-٤ |
| FR-022 | `GET /admin/readings` · `approve` · `reject` | `services/reading` · `ledger` | `reading_submissions` `point_events` | ث-٦ | **الطابور على مستوى الجمعية** (§٧.٣) | و-٤ |
| FR-023 | **قيد** داخل `approve` | `services/reading` · `ledger` | `point_events` | — | اعتماد متأخّر ⇒ `occurred_at = read_on` | و-٤ |
| FR-024 | `GET /me/readings` | `services/reading` | `reading_submissions` | ث-٦ | المرفوض يعرض سببه للطالب | و-٤ |

## القرآن — اللصق

| FR | المسار | الوحدة | الجدول | الثابت | الاختبار | وحدة العمل |
|---|---|---|---|:--:|---|:--:|
| FR-030 | `POST /admin/paste/preview` | `ingest/rasd` | — | — | ترويسة ناقصة ⇒ رفض **بلا تخمين ترتيب** | و-٥ |
| FR-031 | ضمن `preview` | `services/matching` | `users` | — | **لا كتابة في وضع المعاينة** | و-٥ |
| FR-032 | ضمن `preview` | `services/matching` | `users` | — | المتشابه يُعرض ببدائله ولا يُطبَّق | و-٥ |
| FR-033 | `POST /admin/paste/commit` | `services/paste` | `raw_rows` | — | الخام محفوظ **قبل** اشتقاق النقاط | و-٥ |
| FR-034 | **قيد** داخل `commit` | `services/ledger` | `point_events` | **ث-٣** | **لصق مرّتين ⇒ الرصيد لم يتغيّر** | و-٥ |
| FR-040 | عمود اختياري في `preview`/`commit` | `ingest/rasd` | `point_events` | — | ترويسة بلا حضور ⇒ **لا شيء يُكسر** | و-٥ |

## التعديل القرآني

| FR | المسار | الوحدة | الجدول | الثابت | الاختبار | وحدة العمل |
|---|---|---|---|:--:|---|:--:|
| FR-035 | `POST /admin/events/{id}/reverse` | `services/ledger` | `point_events` | **ث-٢ · ث-٧** | بلا سبب ⇒ `422` · `UPDATE` مباشر ⇒ استثناء | و-٦ |
| FR-036 | `POST /admin/quran/entry` | `ingest/manual` · `ledger` | `point_events` `raw_rows` | ث-٧ | الحدث منسوب وبسبب | و-٦ |
| FR-037 | **أثر جانبي** لكل تعديل | `services/ledger` | `audit_log` | — | كل تصحيح يظهر في `/admin/audit` | و-٦ |
| FR-080 | نفس مسار FR-035 | `services/ledger` | `point_events` | ث-٢ | — | و-٦ |

## اللوحات والتفاعل

| FR | المسار | الوحدة | الجدول | الثابت | الاختبار | وحدة العمل |
|---|---|---|---|:--:|---|:--:|
| FR-050 | `GET /boards/pilots` | `services/standings` | `point_events` | — | الترتيب بالساعات | و-٩ |
| FR-051 | `GET /boards/teams` | `services/standings` | `point_events` `memberships` | ث-٤ | **بالمعدّل** · سرب أكبر لا يتقدّم بحجمه | و-٩ |
| FR-052 | ضمن `/boards/teams` | `services/standings` | — | — | التعادل يُفكّ بمعيار ثابت **معلَن** | و-٩ |
| FR-053 | `GET /boards/formation` | `services/standings` · `readiness` | `point_events` | — | **الاسم داخل السرب فقط** (ف-١) | و-٩ |
| FR-060 | `GET /questions/today` · `POST .../answer` | `services/engagement` · `ledger` | `daily_questions` `answers` | **ث-٨** | إجابة ثانية ⇒ `409` · **الصحيح وشرحه في الحالتين** | و-٩ |
| FR-061 | `POST /notes` | `services/engagement` | `notes` | **ث-١٢** | **فحص المخطط: لا `user_id` ولا `ip`** · الردّ بلا `id` | و-٩ |
| FR-062 | `POST /admin/week/pilot` · `GET /week/pilot` | `services/engagement` | `pilot_of_week` | **ث-٩** | ثانٍ لنفس الأسبوع ⇒ رفض · السبب إلزامي | و-٩ |
| FR-041 | `POST /admin/attendance` | `services/entry` · `ledger` | `point_events` | — | **احتياطي** — يُبنى إن لم يُتِح راصد الحضور | و-٩ |
| FR-042 | ضمن `/admin/attendance` | `services/entry` | `point_events` | — | معاملة واحدة · تراجع ٥ دقائق | و-٩ |

## الوقود

| FR | المسار | الوحدة | الجدول | الثابت | الاختبار | وحدة العمل |
|---|---|---|---|:--:|---|:--:|
| FR-070 | `POST /admin/fuel/assess` | `services/fuel` · `ledger` | `fuel_*` `point_events` | **ث-١ · ث-١٠أ · ث-١٠ب** | مجموع أوزان ٩٥ ⇒ `422` | و-٨ |
| FR-071 | ضمن `assess` | `services/fuel` | `fuel_scores` | — | كل بند محفوظ مفصّلًا | و-٨ |
| FR-072 | `GET /station` | `services/fuel` | `point_events` | ث-١ | وقود السرب لا الفرد | و-٨ |

## الإدارة

| FR | المسار | الوحدة | الجدول | الثابت | الاختبار | وحدة العمل |
|---|---|---|---|:--:|---|:--:|
| FR-081 | `GET·POST /admin/weights` | `services/rules_admin` | `weight_versions` `weights` | **ث-١١** | حدث ماضٍ يستعمل الوزن القديم | و-٧ |
| FR-082 | `/admin/thresholds` + `preview` | `services/rules_admin` | `rank_thresholds` `users` | **ث-١٣أ · ث-١٣ب** | `demoted` فارغ · سُلّم متناقض ⇒ `422` | و-٧ |
| FR-083 | `/admin/teams` | `services/teams` | `teams` `memberships` | **ث-٤** | النقل لا ينقل التاريخ · أرشفة لا حذف | و-٧ |
| FR-084 | `GET /admin/audit` | `services/audit` | `audit_log` | — | **مفتوح لكل المشرفين** — تعويض دمج الدورين | و-٧ |
| FR-085 | `GET /admin/report` | `services/reports` | `point_events` | — | **بلا جدول جديد** — مشتقّ من السجلّ | و-١٠ |
| FR-086 | `POST /admin/recalc` | `services/paste` · `ledger` | `raw_rows` `point_events` | ث-٢ | `dry_run` افتراضيًّا · **لا حذف** | و-١٠ |

---

## وحدات العمل

| # | الوحدة | البوابة |
|---|---|---|
| **و-١** | **الشريحة الرأسية** — دخول + بطاقة | [`SLICE-01.md`](../plans/SLICE-01.md) · تكشف أخطاء المعمار قبل البناء فوقه |
| و-٢ | **إعادة تعيين PIN وسجلّ التدقيق** — والقفل (FR-003) منفَّذ منذ و-١ | تبني `audit_log`: أوّل كاتب فيه |
| و-٣ | سجلّ أحداث الطالب | |
| و-٤ | القراءة: إدخال واعتماد | **أوّل مسار يستعمل `ledger`** |
| و-٥ | اللصق والاستيراد | **الاختبار الإلزامي: لصق مرّتين** · معلَّق على س-١ |
| و-٦ | التصحيح والتعديل القرآني | ث-٢ مفروض بمشغّل |
| و-٧ | الأوزان والعتبات والأسراب والسجلّ | |
| و-٨ | الوقود ببنوده | |
| و-٩ | اللوحات والتشكيل والتفاعل | حذف كل بيانات مؤلَّفة |
| و-١٠ | التقارير وإعادة الحساب والنشر | |

**٤١ متطلَّبًا · ١٠ وحدات · صفر متطلَّب بلا مسار.**

---

## الفحص

```bash
comm -3 <(grep -o 'FR-[0-9]\{3\}' docs/product/SCOPE.md | sort -u) \
        <(grep -o 'FR-[0-9]\{3\}' docs/design/TRACEABILITY.md | sort -u)
```
**مخرَج فارغ** = لا متطلَّب بلا مسار تنفيذ، ولا مسار بلا متطلَّب.
