"""
مصفوفة الصلاحيات — **مولَّدةٌ من `url_map` لا مكتوبةٌ بيد**.

**الفجوة التي يسدّها:** ٤٢ مسارًا إداريًّا، **خمسةٌ منها لا تظهر في أيّ
اختبار** (`/admin/fuel/week/{approve,scores,tasks,team}` و
`/admin/notes/<id>`)، **ولا شيء كان يمشي على المسارات** فيؤكّد أن كلَّ
`/api/admin/*` يردّ ٤٠٣ لطالب و٤٠١ لمجهول. فمسارٌ جديد يُضاف بلا
`@admin_required` **يمرّ صامتًا**.

وهذا أخطرُ صنفِ عطلٍ في المنصّة لا أحدَها: `SCOPE.md §٣.٣` يقرّ بأن الدورَين
مدموجان (من يُدخل الدرجات هو من يضبط قواعد احتسابها)، **فالحمايةُ منقولةٌ من
منع الصلاحية إلى كشف الاستعمال** — وكشفُ الاستعمال يسقط كلُّه إن دخل طالبٌ
مسارًا إداريًّا.

**والتوليد هو المقصد لا الاختصار:** قائمةٌ مكتوبةٌ بيدٍ تُغطّي ما كُتب يومَ
كتابتها، وهذه تُغطّي **كلَّ مسارٍ قائمٍ والقادمَ بعده** — فالحرس لا يحتاج أن
يتذكّره أحد.

@covers ق-٢٩١
"""

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import Membership

ORIGIN = {"Origin": "http://localhost:5173"}

# الطرقُ الآمنة تُجرَّب بلا جسم؛ والمغيِّرة تحتاج `Origin` (ADR-006) وجسمًا
# فارغًا — والمطلوبُ هو **رمز الصلاحية** لا صحّة الجسم، فـ٤٢٢ لا تُقبل هنا:
# ٤٢٢ تعني أن الطلب **عبر** الحارس ووصل إلى التحقّق من المخطّط.
METHODS = ("GET", "POST", "PATCH", "DELETE", "PUT")


def _admin_rules(app):
    """كلُّ قاعدةٍ تحت `/api/admin/` مع طرقها المغيِّرة والآمنة."""
    out = []
    for rule in app.url_map.iter_rules():
        if not str(rule).startswith("/api/admin/"):
            continue
        # معرّفاتٌ تُستبدل برقمٍ لا وجود له: المطلوب رمزُ الصلاحية قبل
        # البحث، فعدمُ وجود السجلّ لا يُضعف الفحص.
        path = str(rule)
        for var in rule.arguments:
            path = path.replace(f"<int:{var}>", "999999999").replace(f"<{var}>", "999999999")
        for m in sorted(rule.methods & set(METHODS)):
            out.append((m, path))
    return sorted(set(out))


def test_the_matrix_is_not_empty(app):
    """
    **حارسُ الفراغ.** استخراجٌ يعطي صفرًا يجعل كلَّ ما بعده ينجح على لا شيء —
    وهو العطل نفسه الذي وقع في بوّابة `ق` عند بنائها.
    """
    rules = _admin_rules(app)
    assert len(rules) >= 40, f"استُخرج {len(rules)} فقط — الاستخراج معطوب لا المسارات"


def test_every_admin_route_refuses_an_anonymous_caller(client, app):
    """لا جلسة ⇒ ٤٠١. و**لا ٤٢٢**: ٤٢٢ تعني أن الطلب عبر الحارس.

    @covers ق-٢٩١
    """
    leaks = []
    for method, path in _admin_rules(app):
        r = client.open(path, method=method, headers=ORIGIN, json={})
        if r.status_code not in (401, 405):
            leaks.append(f"{method} {path} → {r.status_code}")
    assert not leaks, "مسارات تقبل مجهولًا:\n  " + "\n  ".join(leaks)


def test_every_admin_route_refuses_a_pilot(client, seeded, app):
    """
    جلسةُ طالب ⇒ ٤٠٣. **وهذا ما لم يكن محروسًا**: مسارٌ يُضاف بلا
    `@admin_required` كان يمرّ صامتًا، وخمسةُ مسارات لم تكن في أيّ اختبار.

    @covers ق-٢٩١
    """
    membership = db.session.scalar(
        select(Membership).where(Membership.user_id == seeded["users"]["1002"])
    )
    assert membership.role == "pilot", "تركيبةُ الاختبار تغيّرت — الفحص يحتاج طالبًا"
    client.post("/api/auth/login", json={"student_no": "1002", "pin": "1234"}, headers=ORIGIN)

    leaks = []
    for method, path in _admin_rules(app):
        r = client.open(path, method=method, headers=ORIGIN, json={})
        if r.status_code not in (403, 405):
            leaks.append(f"{method} {path} → {r.status_code}")
    assert not leaks, "مسارات يصلها طالب:\n  " + "\n  ".join(leaks)


@pytest.mark.parametrize("path", ["/api/me/deck", "/api/boards/pilots", "/api/station"])
def test_pilot_routes_stay_open_to_a_pilot(client, seeded, path):
    """
    **والحرس ليس منعًا مطلقًا.** فحصٌ يمنع الجميع يمرّ خضرَاء وهو يكسر
    المنصّة — فهذا الضلعُ الآخر يُثبت أن الطالب ما زال يصل إلى شاشاته.

    @covers ق-٢٩١
    """
    client.post("/api/auth/login", json={"student_no": "1002", "pin": "1234"}, headers=ORIGIN)
    assert client.get(path, headers=ORIGIN).status_code == 200
