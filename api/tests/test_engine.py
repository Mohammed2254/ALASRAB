"""
محرّك القواعد — `RULES.md` §١–§٤.

الاختبارات تشغّل الاستعلام الحقيقي على إصدارَي أوزان حقيقيَّين في القاعدة: فحصُ
شكل الدالّة يثبت أنها كُتبت، لا أنها تختار الإصدار الصحيح.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import event

from app.extensions import db
from app.rules.engine import Achievement, hours_for, ruleset_at

# قبل سريان الإصدار الأحدث (٢٠٢٦-٠٦-٠١) وبعده.
PAST = datetime(2025, 3, 10, tzinfo=UTC)
RECENT = datetime(2026, 7, 15, tzinfo=UTC)


def _pages(occurred_at, quantity=10, mastery=None, activity="memorize"):
    return Achievement(
        user_id=1,
        occurred_at=occurred_at,
        activity_type=activity,
        quantity=Decimal(quantity),
        mastery=mastery,
    )


# ═══ ث-١١ — القرار الأهمّ في المحرّك ═══


def test_historical_event_uses_the_ruleset_of_its_own_time(seeded):
    """
    حدثٌ وقع قبل الإصدار الجديد يُحتسب بالوزن القديم (١.٠) لا الحالي (٢.٥).

    هذا السطر تحديدًا هو ما يمنع أن يغيّر تعديلُ وزنٍ اليومَ أرقامَ الماضي،
    فيستيقظ الطلاب على ترتيب لم يصنعوه — بلا أن يفعل أحدٌ شيئًا خاطئًا.
    """
    assert hours_for(seeded["org_id"], _pages(PAST)) == Decimal("10.00")


def test_recent_event_uses_the_current_ruleset(seeded):
    """الحدّ الآخر لنفس القاعدة: بلاه قد يمرّ اختبارٌ يستعمل القديم دائمًا."""
    assert hours_for(seeded["org_id"], _pages(RECENT)) == Decimal("25.00")


def test_ruleset_boundary_is_inclusive_of_effective_from(seeded):
    """اللحظة نفسها تنتمي للإصدار الجديد — حدٌّ يجب أن يكون معلنًا لا مصادفة."""
    at_boundary = datetime(2026, 6, 1, tzinfo=UTC)
    assert hours_for(seeded["org_id"], _pages(at_boundary)) == Decimal("25.00")


def test_moment_before_any_version_fails_loudly(seeded):
    """
    الفشل الصريح: احتسابُ حدثٍ بقاعدة لم تكن قائمة وقت وقوعه يعطي رقمًا يبدو
    معقولًا وهو مخترَع. الصمت هنا أسوأ من التوقّف.
    """
    with pytest.raises(ValueError, match="لا إصدار أوزان سارٍ"):
        hours_for(seeded["org_id"], _pages(datetime(2019, 1, 1, tzinfo=UTC)))


# ═══ الرفض بدل التخمين ═══


def test_unknown_activity_raises_arabic_error(seeded):
    with pytest.raises(ValueError, match="لا وزن للنشاط"):
        hours_for(seeded["org_id"], _pages(RECENT, activity="pottery"))


def test_unknown_mastery_raises_arabic_error(seeded):
    with pytest.raises(ValueError, match="لا مضاعف للتقدير"):
        hours_for(seeded["org_id"], _pages(RECENT, mastery="excellent"))


# ═══ مضاعف الإتقان ═══


def test_mastery_multiplier_is_applied(seeded):
    # ١٠ × ٢.٥ × ٢.٠ = ٥٠
    assert hours_for(seeded["org_id"], _pages(RECENT, mastery="mastered")) == Decimal("50.00")


def test_mastery_multiplier_is_also_versioned(seeded):
    """المضاعف يتبع الإصدار كالوزن: ١٠ × ١.٠ × ١.٥ = ١٥."""
    assert hours_for(seeded["org_id"], _pages(PAST, mastery="mastered")) == Decimal("15.00")


def test_none_mastery_means_multiplier_one(seeded):
    """
    نموذج النسبة (ف-٩) لا يحمل تقديرًا. `None` يجب أن يعني ×١ لا أن يفشل —
    وإلا استحال استعمال المحرّك مع تصدير راصد إن جاء نسبةً.
    """
    assert hours_for(seeded["org_id"], _pages(RECENT, mastery=None)) == Decimal("25.00")


# ═══ ADR-005 — الوحدتان بلا تغيير في المخطط ═══


def test_percentage_unit_works_through_the_same_engine(seeded):
    """٨٥ نقطة مئوية × ٠.٢ = ١٧.٠٠ — صفٌّ في جدول الأوزان، لا فرعٌ في الكود."""
    progress = _pages(RECENT, quantity=85, activity="quran_progress")
    assert hours_for(seeded["org_id"], progress) == Decimal("17.00")


# ═══ الدقّة ═══


def test_rounding_happens_once_at_the_end(seeded):
    """
    ٧ × ٢.٥ × ٢.٠ = ٣٥ بالضبط. والمهمّ أن الناتج NUMERIC(8,2) بمنزلتين، فلا
    ينجرف المجموع عبر آلاف الصفوف حتى يظهر في الترتيب.
    """
    result = hours_for(seeded["org_id"], _pages(RECENT, quantity=7, mastery="mastered"))
    assert result == Decimal("35.00")
    assert result.as_tuple().exponent == -2


def test_fractional_quantity_keeps_two_places(seeded):
    """٣ × ٠.٢ = ٠.٦٠ — نصف صفحة تقدّم لا يُفقد ولا يتضخّم."""
    assert hours_for(
        seeded["org_id"], _pages(RECENT, quantity=3, activity="quran_progress")
    ) == Decimal("0.60")


# ═══ المبرّر المقيس لوجود RuleSet ═══


def test_ruleset_loads_once_per_moment_not_once_per_achievement(seeded, app):
    """
    مبرّر `RuleSet` مقيس لا مدّعى: دفعةٌ من اثني عشر إنجازًا تشترك في لحظة
    الوقوع تكلّف **ثلاثة استعلامات لا ستة وثلاثين**.

    وهذا N+1 في أكثر مسار حساسية للزمن عندنا — الشاشة التي معيارها «أقلّ من
    دقيقة» (NFR-02). العدّ الفعلي هو ما يمنع أن يتحوّل التجريد إلى ادّعاء.
    """
    counter = {"n": 0}

    def count(conn, cursor, statement, params, context, executemany):
        counter["n"] += 1

    event.listen(db.engine, "before_cursor_execute", count)
    try:
        rules = ruleset_at(seeded["org_id"], RECENT)  # ٣ استعلامات
        loaded = counter["n"]
        for _ in range(12):
            rules.hours_for(_pages(RECENT))  # صفر
        after_batch = counter["n"]
    finally:
        event.remove(db.engine, "before_cursor_execute", count)

    assert loaded == 3, f"تحميل القواعد كلّف {loaded} استعلامات لا ٣"
    assert after_batch == loaded, "الحساب لا يجوز أن يلمس القاعدة إطلاقًا"


# ═══ حدّ المحرّك ═══


def test_engine_never_writes(seeded):
    """
    المحرّك يقرأ ويحسب ولا يُلحق. من يكتب هو `ledger` وحده (AGENTS ٨).
    فحصٌ سلوكيّ: بعد حسابات عدّة، لا صفّ جديد في السجلّ.
    """
    before = db.session.scalar(db.text("SELECT count(*) FROM point_events"))
    for _ in range(5):
        hours_for(seeded["org_id"], _pages(RECENT))
    assert db.session.scalar(db.text("SELECT count(*) FROM point_events")) == before
