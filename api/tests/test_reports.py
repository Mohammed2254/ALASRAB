"""
التقرير الدوري للمشرف — FR-085 (و-١٠ جزئية).

**قراءة خالصة:** لا `ledger` ولا كتابة ولا جدول جديد — و`test_report_writes_nothing`
يثبت ذلك سلوكيًّا لا بالادّعاء.

فُصل عن `test_events.py` لأن اجتماعهما في ملفّ واحد **أخفى الحقيقة**: زيادةُ
pytest بمقدار ١٣ بدت كأنها لـو-٣ وحدها، فبدا التقرير بلا تغطية وهو مغطّى بستّة.
اسم الملفّ جزءٌ من التتبّع.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.extensions import db
from app.models import Membership, PointEvent
from app.services import ledger

ORIGIN = {"Origin": "http://localhost:5173"}
REPORT = "/api/admin/report"
NOW = datetime.now(UTC)


def _login(client, student_no="1001"):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": "1234"}, headers=ORIGIN
    )


def _make_admin(user_id):
    m = db.session.scalar(select(Membership).where(Membership.user_id == user_id))
    m.role = "admin"
    db.session.commit()


def _event(seeded, user_key="1001", delta="10", kind="quran", days_ago=1):
    return ledger.append(
        [
            ledger.EventSpec(
                org_id=seeded["org_id"],
                kind=kind,
                delta=Decimal(delta),
                user_id=seeded["users"][user_key],
                occurred_at=NOW - timedelta(days=days_ago),
            )
        ]
    )[0]


def test_report_requires_admin(client, seeded):
    """@covers ق-٣٤ — المسار السالب لـFR-085: طالب عاديّ ⇒ ٤٠٣ · وبلا كوكي ⇒ ٤٠١."""
    assert client.get(REPORT).status_code == 401
    _login(client)
    assert client.get(REPORT).status_code == 403


def test_report_counts_window_movement_not_lifetime_balance(client, seeded):
    """
    @covers ق-٣٢

    «من تقدّم» سؤالٌ عن الأسبوع لا عن العمر: رصيدٌ قديم ضخم لا يجعل صاحبه
    متقدّمًا هذا الأسبوع.
    """
    _event(seeded, user_key="1001", delta="500", days_ago=60)  # خارج النافذة
    _event(seeded, user_key="1002", delta="30", days_ago=2)  # داخلها

    _make_admin(seeded["users"]["1001"])
    _login(client)
    body = client.get(f"{REPORT}?days=7").json

    assert body["totals"]["hours"] == "30.00"
    assert body["totals"]["active_pilots"] == 1
    assert [m["hours"] for m in body["top_movers"]] == ["30.00"]


def test_report_uses_team_average_not_sum(client, seeded):
    """@covers ق-٣٣ — اتّساقًا مع FR-051: المجموع يقيس الحجم لا الاجتهاد."""
    _event(seeded, user_key="1001", delta="20", days_ago=1)
    _event(seeded, user_key="1002", delta="10", days_ago=1)

    _make_admin(seeded["users"]["1001"])
    _login(client)
    team = client.get(REPORT).json["teams"][0]

    assert team["hours"] == "30.00"
    assert team["members"] == 2
    assert team["avg_hours"] == "15.00"


def test_report_lists_grounded_by_name_for_admin(client, seeded):
    """
    @covers ق-٣٦

    «من سقط» بالاسم — **للمشرف وحده**. القرار ٥ يمنع عرضه للطلاب، وهذه شاشة
    إشراف: من يلاحق الطالب يحتاج أن يعرف من يلاحق.
    """
    _event(seeded, user_key="1002", delta="10", kind="quran", days_ago=30)

    _make_admin(seeded["users"]["1001"])
    _login(client)
    body = client.get(REPORT).json

    names = [g["full_name"] for g in body["grounded"]]
    assert "طالب ثانٍ" in names
    assert body["totals"]["grounded_pilots"] == len(body["grounded"])


def test_report_window_is_bounded(client, seeded):
    """
    @covers ق-٣٧, ق-٢٠٤

    حدٌّ أعلى للنافذة: تقريرٌ بلا حدّ يمسح السجلّ كلّه على كل طلب.

    **وهو أيضًا حارس استقلال النافذتين** (`RULES.md` §٩.١): هذه نافذة «آخر N
    يومًا» متدحرجة بمعامل، لا «أسبوع المنظّمة». و-١٢ وحّدت الثانية في
    `services/week.py` ولم تمسّ هذه — و«توحيدٌ» يجعل التقرير أسبوعيًّا يُسقط هذا
    الاختبار، وهو المقصود: العقد مُختبَر لا مفترَض.
    """
    _make_admin(seeded["users"]["1001"])
    _login(client)
    assert client.get(f"{REPORT}?days=9999").json["window"]["days"] == 90
    assert client.get(f"{REPORT}?days=0").json["window"]["days"] == 1


def test_report_window_carries_both_dates(client, seeded):
    """
    @covers ق-٣٧

    `from` و`to` **غير فارغين**. أُضيف بعد أن عرضت الشاشة «null — 31 أغسطس»:
    `data_key` يسمّي الحقل خارجيًّا، وMarshmallow يقرأ القيمة بالاسم الداخلي —
    فبقي `from` فارغًا. **والاختبارات كانت تفحص `days` وحده فلم تمسكه.**
    """
    _make_admin(seeded["users"]["1001"])
    _login(client)
    window = client.get(f"{REPORT}?days=7").json["window"]

    assert window["from"] is not None
    assert window["to"] is not None
    assert window["from"] < window["to"]


def test_report_writes_nothing(client, seeded):
    """@covers ق-٣٥ — قراءة خالصة: لا حدث يُلحق ولا صفّ يتغيّر."""
    _event(seeded, delta="10")
    before = db.session.scalar(select(db.func.count(PointEvent.id)))

    _make_admin(seeded["users"]["1001"])
    _login(client)
    client.get(REPORT)

    assert db.session.scalar(select(db.func.count(PointEvent.id))) == before
