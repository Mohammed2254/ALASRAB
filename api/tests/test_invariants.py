"""
ثوابت المجال المفروضة في قاعدة البيانات — `DATABASE.md` §٤.٣.

كل اختبار هنا يثبت أن **مخالفة القاعدة مستحيلة فيزيائيًّا لا ممنوعة أدبيًّا**.
ويُشغّل SQL الحقيقي عمدًا: اختبارٌ يمرّ بطبقة التطبيق يثبت أن التطبيق مؤدَّب،
لا أن القاعدة محميّة — والفرق هو كل الفرق (ADR-002).
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.extensions import db
from app.models import PointEvent
from app.services import ledger

NOW = datetime(2026, 8, 1, tzinfo=UTC)


def _raw_insert(**cols):
    """إدخال مباشر يتجاوز `ledger` عمدًا — نختبر القاعدة لا كود التطبيق."""
    keys = ", ".join(cols)
    vals = ", ".join(f":{k}" for k in cols)
    db.session.execute(
        db.text(f"INSERT INTO point_events ({keys}, occurred_at) VALUES ({vals}, :now)"),
        {**cols, "now": NOW},
    )
    db.session.commit()


# ═══ ث-١ — الساعات فردية · الوقود جماعي · ولا يلتقيان ═══


@pytest.mark.parametrize(
    "case, cols",
    [
        (
            "طالب يكسب وقودًا",
            dict(scope="individual", user_id=1, team_id=None, currency="fuel", delta=5, kind="x"),
        ),
        (
            "سرب يكسب ساعات",
            dict(scope="team", user_id=None, team_id=1, currency="hours", delta=5, kind="x"),
        ),
        (
            "حدث فردي بلا طالب",
            dict(
                scope="individual", user_id=None, team_id=None, currency="hours", delta=5, kind="x"
            ),
        ),
        (
            "حدث فردي لطالب وسرب معًا",
            dict(scope="individual", user_id=1, team_id=1, currency="hours", delta=5, kind="x"),
        ),
    ],
)
def test_currency_scope_cannot_be_mixed(seeded, case, cols):
    with pytest.raises((IntegrityError, DBAPIError)):
        _raw_insert(org_id=seeded["org_id"], **cols)
    db.session.rollback()


def test_valid_individual_event_is_accepted(seeded):
    _raw_insert(
        org_id=seeded["org_id"],
        scope="individual",
        user_id=seeded["users"]["1001"],
        team_id=None,
        currency="hours",
        delta=10,
        kind="quran",
    )
    assert db.session.scalar(db.select(db.func.count(PointEvent.id))) == 1


# ═══ ث-٢ — سجلّ إلحاق فقط ═══


def test_update_on_point_events_is_rejected(seeded):
    """@covers ق-١٢"""
    e = ledger.append(
        [
            ledger.EventSpec(
                org_id=seeded["org_id"],
                kind="quran",
                delta=Decimal("10"),
                user_id=seeded["users"]["1001"],
                occurred_at=NOW,
            )
        ]
    )[0]
    with pytest.raises(DBAPIError, match="إلحاق فقط"):
        db.session.execute(
            db.text("UPDATE point_events SET delta = 999 WHERE id = :i"), {"i": e.id}
        )
    db.session.rollback()


def test_delete_on_point_events_is_rejected(seeded):
    """@covers ق-١٢"""
    e = ledger.append(
        [
            ledger.EventSpec(
                org_id=seeded["org_id"],
                kind="quran",
                delta=Decimal("10"),
                user_id=seeded["users"]["1001"],
                occurred_at=NOW,
            )
        ]
    )[0]
    with pytest.raises(DBAPIError, match="إلحاق فقط"):
        db.session.execute(db.text("DELETE FROM point_events WHERE id = :i"), {"i": e.id})
    db.session.rollback()


def test_truncate_bypasses_append_only_trigger(seeded):
    """
    سلوك PostgreSQL الذي تعتمد عليه كل تركيبة اختبار: TRUNCATE لا يُطلق مشغّلات
    الصفوف. **يُختبر لا يُفترض** — لو تغيّر، انهارت البذرة النظيفة كلها بلا إنذار.
    """
    ledger.append(
        [
            ledger.EventSpec(
                org_id=seeded["org_id"],
                kind="quran",
                delta=Decimal("10"),
                user_id=seeded["users"]["1001"],
                occurred_at=NOW,
            )
        ]
    )
    db.session.execute(db.text("TRUNCATE point_events RESTART IDENTITY CASCADE"))
    db.session.commit()
    assert db.session.scalar(db.select(db.func.count(PointEvent.id))) == 0


# ═══ ث-٣ — الـidempotency ═══


def test_same_external_ref_cannot_be_inserted_twice(seeded):
    spec = ledger.EventSpec(
        org_id=seeded["org_id"],
        kind="quran",
        delta=Decimal("10"),
        user_id=seeded["users"]["1001"],
        occurred_at=NOW,
        external_ref="rasd:TST:2026-08-01:1001:quran",
    )
    ledger.append([spec])
    with pytest.raises(IntegrityError):
        ledger.append([spec])
    db.session.rollback()


def test_null_external_ref_repeats_freely(seeded):
    """الفهرس جزئي: الأحداث اليدوية بلا مرجع خارجي تتكرّر بلا قيد."""
    spec = ledger.EventSpec(
        org_id=seeded["org_id"],
        kind="manual",
        delta=Decimal("1"),
        user_id=seeded["users"]["1001"],
        occurred_at=NOW,
    )
    ledger.append([spec])
    ledger.append([spec])
    assert db.session.scalar(db.select(db.func.count(PointEvent.id))) == 2


# ═══ ث-٧ — التصحيح يوجب سببًا ═══


def test_correction_without_reason_is_rejected_by_database(seeded):
    with pytest.raises((IntegrityError, DBAPIError)):
        _raw_insert(
            org_id=seeded["org_id"],
            scope="individual",
            user_id=seeded["users"]["1001"],
            team_id=None,
            currency="hours",
            delta=-10,
            kind="correction",
        )
    db.session.rollback()


def test_reverse_produces_opposite_event_with_reason(seeded):
    original = ledger.append(
        [
            ledger.EventSpec(
                org_id=seeded["org_id"],
                kind="quran",
                delta=Decimal("40"),
                user_id=seeded["users"]["1001"],
                occurred_at=NOW,
            )
        ]
    )[0]
    correction = ledger.reverse(original, "خطأ في تصدير راصد", actor_id=seeded["users"]["1002"])

    assert correction.delta == Decimal("-40.00")
    assert correction.kind == "correction"
    # التصحيح يخصّ لحظة الأصل لا لحظة التصحيح — وإلا انتقل الأثر إلى أسبوع آخر.
    assert correction.occurred_at == original.occurred_at
    assert db.session.scalar(db.select(db.func.sum(PointEvent.delta))) == Decimal("0.00")


def test_reverse_refuses_empty_reason(seeded):
    e = ledger.append(
        [
            ledger.EventSpec(
                org_id=seeded["org_id"],
                kind="quran",
                delta=Decimal("5"),
                user_id=seeded["users"]["1001"],
                occurred_at=NOW,
            )
        ]
    )[0]
    with pytest.raises(ValueError, match="سببًا"):
        ledger.reverse(e, "   ", actor_id=1)


# ═══ ث-٤ — عضوية سارية واحدة ═══


def test_second_active_membership_is_rejected(seeded):
    from app.models import Membership

    db.session.add(
        Membership(
            org_id=seeded["org_id"],
            user_id=seeded["users"]["1001"],
            team_id=seeded["team_id"],
            role="pilot",
        )
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


# ═══ ث-١٤ — «أرضي» محسوبة لا مخزَّنة ═══


def test_users_table_has_no_grounded_column(seeded):
    cols = db.session.execute(
        db.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='grounded'"
        )
    ).all()
    assert cols == [], "عمود grounded يخالف ث-١٤: القيمة المشتقّة تفترق عن مصدرها"


# ═══ حدّ ledger ═══


def test_ledger_refuses_event_that_is_neither_or_both(seeded):
    with pytest.raises(ValueError, match="إمّا لطالب"):
        ledger.append([ledger.EventSpec(org_id=1, kind="x", delta=Decimal("1"), occurred_at=NOW)])


# ═══ ث-٥ · ث-٦ — طلبات القراءة (و-٤) ═══


def _raw_reading(**cols):
    """
    إدخال مباشر يتجاوز `services/reading` عمدًا.

    اختبارٌ يمرّ بطبقة التطبيق يثبت أن التطبيق مؤدَّب، **لا أن القاعدة محميّة** —
    والفرق هو ADR-002 كلّه.
    """
    cols.setdefault("book_title", "كتاب الاختبار")
    keys = ", ".join(cols)
    vals = ", ".join(f":{k}" for k in cols)
    db.session.execute(db.text(f"INSERT INTO reading_submissions ({keys}) VALUES ({vals})"), cols)
    db.session.commit()


@pytest.mark.parametrize(
    "case, cols",
    [
        (
            "معتمد بلا حدث",
            dict(status="approved", point_event_id=None),
        ),
        (
            "معلَّق مع حدث",
            dict(status="pending", point_event_id=-1),
        ),
        (
            "مرفوض مع حدث",
            dict(status="rejected", review_reason="سبب", point_event_id=-1),
        ),
    ],
)
def test_approved_and_event_are_inseparable(seeded, case, cols):
    """
    @covers ق-١٩ · ث-٥

    يمنع الخطأين معًا: اعتمادٌ بلا ساعات فيشتكي الطالب ولا يجد أثرًا، وساعاتٌ
    بلا اعتماد فتُمنح بلا مراجعة.
    """
    if cols.get("point_event_id") == -1:
        cols["point_event_id"] = ledger.append(
            [
                ledger.EventSpec(
                    org_id=seeded["org_id"],
                    kind="reading",
                    delta=Decimal("6"),
                    user_id=seeded["users"]["1001"],
                    occurred_at=NOW,
                )
            ]
        )[0].id

    with pytest.raises((IntegrityError, DBAPIError)):
        _raw_reading(
            org_id=seeded["org_id"],
            user_id=seeded["users"]["1001"],
            read_on=NOW.date(),
            pages=40,
            **cols,
        )
    db.session.rollback()


def test_rejection_without_reason_is_rejected_by_database(seeded):
    """@covers ق-٢٠ · ث-٦ — رفضٌ صامت يقتل الثقة أسرع من غياب الميزة."""
    with pytest.raises((IntegrityError, DBAPIError)):
        _raw_reading(
            org_id=seeded["org_id"],
            user_id=seeded["users"]["1001"],
            read_on=NOW.date(),
            pages=40,
            status="rejected",
        )
    db.session.rollback()


def test_valid_reading_rows_are_accepted(seeded):
    """@covers ق-١٩ · ق-٢٠ — الحدّ الآخر: القيود ليست مفرطة."""
    from app.models import ReadingSubmission

    _raw_reading(
        org_id=seeded["org_id"],
        user_id=seeded["users"]["1001"],
        read_on=NOW.date(),
        pages=40,
        status="pending",
    )
    _raw_reading(
        org_id=seeded["org_id"],
        user_id=seeded["users"]["1001"],
        read_on=NOW.date(),
        pages=12,
        book_title="كتاب مرفوض",
        status="rejected",
        review_reason="خارج القائمة",
    )
    assert db.session.scalar(db.select(db.func.count(ReadingSubmission.id))) == 2
