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
    """الفهرس جزئي: الأحداث بلا مرجع خارجي تتكرّر بلا قيد."""
    spec = ledger.EventSpec(
        org_id=seeded["org_id"],
        kind="quran",
        delta=Decimal("1"),
        user_id=seeded["users"]["1001"],
        occurred_at=NOW,
    )
    ledger.append([spec])
    ledger.append([spec])
    assert db.session.scalar(db.select(db.func.count(PointEvent.id))) == 2


# ═══ ث-٧ — التصحيح أو الإدخال اليدوي يوجب سببًا ═══


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


def test_manual_entry_without_reason_is_rejected_by_database(seeded):
    """التوسيع في و-٦: نفس ث-٧، والآن يشمل `kind='manual'` لا `correction` وحده."""
    with pytest.raises((IntegrityError, DBAPIError)):
        _raw_insert(
            org_id=seeded["org_id"],
            scope="individual",
            user_id=seeded["users"]["1001"],
            team_id=None,
            currency="hours",
            delta=10,
            kind="manual",
        )
    db.session.rollback()


def test_manual_entry_with_reason_is_accepted_by_database(seeded):
    """المقابل الإيجابي: نفس القيد لا يرفض غير المخالف — سقوطٌ للسبب المُدَّعى بالضبط."""
    _raw_insert(
        org_id=seeded["org_id"],
        scope="individual",
        user_id=seeded["users"]["1001"],
        team_id=None,
        currency="hours",
        delta=10,
        kind="manual",
        reason="غاب عن تصدير راصد",
    )
    assert db.session.scalar(db.select(db.func.count(PointEvent.id))) == 1


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


# ═══ ث-١٣أ · ث-١٣ب — و-٧: سُلّم متّسق · الرتبة لا تنخفض ═══


def test_inconsistent_ladder_is_rejected_by_database(seeded):
    """
    @covers ق-٥١

    إدخالٌ يتجاوز `services/rules_admin` عمدًا — القاعدة تحمي لا التطبيق.
    """
    with pytest.raises(DBAPIError, match="غير متّسق"):
        db.session.execute(
            db.text(
                "INSERT INTO rank_thresholds (org_id, key, name, tier, at_hours) "
                "VALUES (:org, 'bad', 'رتبة مخالفة', 5, 50)"
            ),
            {"org": seeded["org_id"]},
        )
    db.session.rollback()


def test_consistent_ladder_addition_is_accepted(seeded):
    """@covers ق-٥١ — الحدّ الآخر: القيد ليس مفرطًا."""
    db.session.execute(
        db.text(
            "INSERT INTO rank_thresholds (org_id, key, name, tier, at_hours) "
            "VALUES (:org, 'ace', 'صقر', 5, 2000)"
        ),
        {"org": seeded["org_id"]},
    )
    db.session.commit()
    assert (
        db.session.scalar(
            db.text("SELECT count(*) FROM rank_thresholds WHERE key='ace'")
        )
        == 1
    )


def test_highest_achieved_tier_cannot_be_lowered_by_direct_update(seeded):
    """
    @covers ق-٥٠

    دفاعٌ ثانٍ خلف `services/rules_admin`: حتى لو أخطأ كودٌ مستقبليّ ونسي شرط
    الارتفاع فقط، القاعدة ترفض — نفس منهج ث-٢ الذي كاد يشحن مخالفة بلا مشغّل.
    """
    uid = seeded["users"]["1001"]
    db.session.execute(
        db.text("UPDATE users SET highest_achieved_tier = 3 WHERE id = :u"), {"u": uid}
    )
    db.session.commit()

    with pytest.raises(DBAPIError, match="لا تنخفض"):
        db.session.execute(
            db.text("UPDATE users SET highest_achieved_tier = 1 WHERE id = :u"), {"u": uid}
        )
    db.session.rollback()


def test_highest_achieved_tier_can_be_raised(seeded):
    """@covers ق-٥٠ — الحدّ الآخر: الارتفاع مسموح دائمًا."""
    uid = seeded["users"]["1001"]
    db.session.execute(
        db.text("UPDATE users SET highest_achieved_tier = 3 WHERE id = :u"), {"u": uid}
    )
    db.session.commit()
    assert db.session.scalar(
        db.text("SELECT highest_achieved_tier FROM users WHERE id = :u"), {"u": uid}
    ) == 3


# ═══ ث-١٠أ · ث-١٠ب · و-٨ — أوزان الوقود تجمع ١٠٠٪ على نقطتين ═══


def _make_activity(org_id, weights):
    """نشاطٌ وبنوده — `weights` قائمة أوزان. مجموعها يُقرَّر عند COMMIT (مؤجَّل)."""
    aid = db.session.scalar(
        db.text(
            "INSERT INTO fuel_activities (org_id, key, name, litres_full) "
            "VALUES (:org, 'a'||floor(random()*1e9)::text, 'نشاط', 50) RETURNING id"
        ),
        {"org": org_id},
    )
    for i, w in enumerate(weights):
        db.session.execute(
            db.text(
                "INSERT INTO fuel_criteria (activity_id, key, name, weight_pct, position) "
                "VALUES (:aid, :key, :key, :w, :pos)"
            ),
            {"aid": aid, "key": f"c{i}", "w": w, "pos": i},
        )
    return aid


def _insert_assessment(org_id, team_id, activity_id, actor_id, point_event_id):
    """`point_event_id=None` يُدرَج `NULL` حرفيًّا — يستهدف ق-٦٧ عمدًا."""
    cols = "org_id, team_id, activity_id, occurred_on, total_pct, litres, actor_id, point_event_id"
    pe = ":pe" if point_event_id is not None else "NULL"
    return db.session.scalar(
        db.text(
            f"INSERT INTO fuel_assessments ({cols}) "
            f"VALUES (:org, :team, :act, CURRENT_DATE, 100, 50, :actor, {pe}) RETURNING id"
        ),
        {
            "org": org_id,
            "team": team_id,
            "act": activity_id,
            "actor": actor_id,
            "pe": point_event_id,
        },
    )


def test_activity_with_weights_summing_to_100_is_accepted(seeded):
    """@covers ق-٦٥ — الحدّ الآخر: القيد لا يرفض إدراجًا متعدّد الصفوف صحيحًا."""
    aid = _make_activity(seeded["org_id"], [40, 60])
    db.session.commit()
    assert (
        db.session.scalar(
            db.text("SELECT count(*) FROM fuel_criteria WHERE activity_id=:a"), {"a": aid}
        )
        == 2
    )


def test_activity_with_weights_not_summing_to_100_is_rejected(seeded):
    """@covers ق-٦٥"""
    _make_activity(seeded["org_id"], [40, 50])
    with pytest.raises(DBAPIError, match="بنود النشاط"):
        db.session.commit()
    db.session.rollback()


def test_assessment_scoring_all_criteria_is_accepted(seeded):
    """@covers ق-٦٦ — الحدّ الآخر: تقييم يُغطّي كل البنود يمرّ."""
    aid = _make_activity(seeded["org_id"], [40, 60])
    db.session.commit()
    criteria = db.session.execute(
        db.text("SELECT id FROM fuel_criteria WHERE activity_id=:a ORDER BY position"), {"a": aid}
    ).scalars().all()

    event_id = ledger.append(
        [
            ledger.EventSpec(
                org_id=seeded["org_id"],
                kind="fuel",
                delta=Decimal("47.00"),
                team_id=seeded["team_id"],
                occurred_at=NOW,
            )
        ]
    )[0].id
    asmt_id = _insert_assessment(
        seeded["org_id"], seeded["team_id"], aid, seeded["users"]["1001"], event_id
    )
    for cid in criteria:
        db.session.execute(
            db.text(
                "INSERT INTO fuel_scores (assessment_id, criterion_id, score_pct) "
                "VALUES (:asmt, :cid, 90)"
            ),
            {"asmt": asmt_id, "cid": cid},
        )
    db.session.commit()
    assert (
        db.session.scalar(
            db.text("SELECT count(*) FROM fuel_scores WHERE assessment_id=:a"), {"a": asmt_id}
        )
        == 2
    )


def test_assessment_scoring_only_some_criteria_is_rejected(seeded):
    """
    @covers ق-٦٦

    يمسك انجرافًا/تغطية جزئية: بندٌ واحد من اثنين — وزنه وحده لا يبلغ ١٠٠٪،
    حتى لو كان النشاط سليمًا تمامًا عند تعريفه (ث-١٠أ لا يكفي وحده).
    """
    aid = _make_activity(seeded["org_id"], [40, 60])
    db.session.commit()
    first_criterion = db.session.scalar(
        db.text("SELECT id FROM fuel_criteria WHERE activity_id=:a ORDER BY position LIMIT 1"),
        {"a": aid},
    )

    event_id = ledger.append(
        [
            ledger.EventSpec(
                org_id=seeded["org_id"],
                kind="fuel",
                delta=Decimal("40.00"),
                team_id=seeded["team_id"],
                occurred_at=NOW,
            )
        ]
    )[0].id
    asmt_id = _insert_assessment(
        seeded["org_id"], seeded["team_id"], aid, seeded["users"]["1001"], event_id
    )
    db.session.execute(
        db.text(
            "INSERT INTO fuel_scores (assessment_id, criterion_id, score_pct) "
            "VALUES (:asmt, :cid, 100)"
        ),
        {"asmt": asmt_id, "cid": first_criterion},
    )
    with pytest.raises(DBAPIError, match="البنود المقيَّمة"):
        db.session.commit()
    db.session.rollback()


def test_fuel_assessment_without_point_event_is_rejected(seeded):
    """@covers ق-٦٧"""
    aid = _make_activity(seeded["org_id"], [100])
    db.session.commit()
    with pytest.raises(IntegrityError):
        _insert_assessment(seeded["org_id"], seeded["team_id"], aid, seeded["users"]["1001"], None)
        db.session.commit()
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
