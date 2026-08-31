"""
سجلّ أحداث الطالب — و-٣ · FR-012.

**قراءة خالصة:** لا `ledger` ولا كتابة ولا جدول جديد.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.services import ledger

ORIGIN = {"Origin": "http://localhost:5173"}
EVENTS = "/api/me/events"
NOW = datetime.now(UTC)


def _login(client, student_no="1001"):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": "1234"}, headers=ORIGIN
    )


def _event(seeded, user_key="1001", delta="10", kind="quran", days_ago=1, reason=None):
    return ledger.append(
        [
            ledger.EventSpec(
                org_id=seeded["org_id"],
                kind=kind,
                delta=Decimal(delta),
                user_id=seeded["users"][user_key],
                occurred_at=NOW - timedelta(days=days_ago),
                reason=reason,
            )
        ]
    )[0]


# ═══ ق-٢٧ — السجلّ الأحدث أوّلًا ═══


def test_events_are_newest_first_with_kind_and_date(client, seeded):
    """@covers ق-٢٧"""
    _event(seeded, delta="5", kind="reading", days_ago=5)
    _event(seeded, delta="10", kind="quran", days_ago=1)

    _login(client)
    events = client.get(EVENTS).json["events"]

    assert [e["kind"] for e in events] == ["quran", "reading"]
    assert events[0]["delta"] == "10.00"
    assert events[0]["occurred_on"] == (NOW - timedelta(days=1)).date().isoformat()


def test_empty_log_is_a_designed_state(client, seeded):
    """@covers ق-٢٧ — قائمة فارغة بـ٢٠٠ لا خطأ."""
    _login(client)
    r = client.get(EVENTS)
    assert r.status_code == 200
    assert r.json["events"] == []


def test_limit_is_bounded(client, seeded):
    """@covers ق-٢٧ — حدٌّ أعلى يمنع سحب السجلّ كلّه بطلب واحد."""
    for i in range(5):
        _event(seeded, delta="1", days_ago=i + 1)
    _login(client)
    assert len(client.get(f"{EVENTS}?limit=3").json["events"]) == 3
    assert len(client.get(f"{EVENTS}?limit=9999").json["events"]) == 5


# ═══ ق-٢٨ — التصحيح يظهر سالبًا بسببه ═══


def test_correction_shows_negative_with_its_reason(client, seeded):
    """
    @covers ق-٢٨

    «إخفاؤها هو ما يثير الشك لا إظهارها» (ط-٤). طالبٌ يرى رصيده نقص بلا سطر
    يفسّره يظنّ خللًا أو تلاعبًا — والسطر بسببه يُنهي الشكّ.
    """
    original = _event(seeded, delta="40", kind="quran", days_ago=3)
    ledger.reverse(original, "خطأ في تصدير راصد", actor_id=seeded["users"]["1002"])

    _login(client)
    events = client.get(EVENTS).json["events"]
    correction = next(e for e in events if e["kind"] == "correction")

    assert correction["delta"] == "-40.00"  # بإشارته لا بقيمته المطلقة
    assert correction["reason"] == "خطأ في تصدير راصد"
    assert len(events) == 2  # الأصل والتصحيح كلاهما ظاهر


def test_ordinary_events_carry_no_reason(client, seeded):
    """@covers ق-٢٨ — `reason` فارغ في غير التصحيح، ولا يُختلق نصّ لملء الحقل."""
    _event(seeded, delta="10")
    _login(client)
    assert client.get(EVENTS).json["events"][0]["reason"] is None


# ═══ ق-٢٩ — المسار السالب الإلزامي ═══


def test_events_without_cookie_is_401(client, seeded):
    """@covers ق-٢٩ — الشقّ الأوّل: بلا مصادقة."""
    assert client.get(EVENTS).status_code == 401


def test_student_cannot_read_another_students_events(client, seeded):
    """
    @covers ق-٢٩ — الشقّ الثاني: تمرير معرّف لا يغيّر شيئًا.

    لا معرّف في المسار ولا في الاستعلام، فلا يوجد ما يُتلاعب به أصلًا.
    """
    _event(seeded, user_key="1001", delta="10")
    _event(seeded, user_key="1002", delta="777")

    _login(client)
    victim = seeded["users"]["1002"]
    for attempt in ("", f"?user_id={victim}", f"?user_id={victim}&student_no=1002"):
        events = client.get(EVENTS + attempt).json["events"]
        assert [e["delta"] for e in events] == ["10.00"], attempt
