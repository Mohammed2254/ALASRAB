"""
سجلّ الأحداث: المالك الوحيد لإلحاق `point_events` (AGENTS ٨).

**المشكلة التي يحلّها:** سبعة مسارات تُلحق أحداثًا (لصق · إضافة يدوية · تصحيح ·
اعتماد قراءة · حضور · وقود · سؤال يومي). كلٌّ منها يجب أن يحترم `external_ref`
الحتمي، والقيد المركزي، وحظر التعديل. **سبع نسخ من المسؤولية تعني أن السابعة
ستنساها.**

**وما ليس عليه:** ليس غلافًا على SQLAlchemy، ولا صنف CRUD عامًّا. مسؤوليته واحدة
ضيّقة: *الإلحاق الصحيح*. أمّا *متى* يُلحق حدث ولماذا فتملكه خدمة المجال —
`reading.py` تقرّر أن الاعتماد يستحقّ حدثًا، وهذا الملفّ يعرف كيف يُلحق حدثٌ صحيح.

**اختبار الحدّ:** إن احتاج يومًا أن يعرف ما «القراءة» أو ما «الوقود»، فقد تجاوزه.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from ..extensions import db
from ..models import PointEvent


@dataclass(frozen=True)
class EventSpec:
    """ما تصفه خدمة المجال. تحويله إلى صفٍّ صحيح مسؤولية هذا الملفّ وحده."""

    org_id: int
    kind: str
    delta: Decimal
    occurred_at: datetime
    user_id: int | None = None
    team_id: int | None = None
    reason: str | None = None
    actor_id: int | None = None
    external_ref: str | None = None


def _row(spec: EventSpec) -> PointEvent:
    """
    يشتقّ scope و currency من الحقل المملوء — لا يقبلهما من المستدعي.

    القيد المركزي في القاعدة يرفض الخلط على أي حال (ث-١)، لكن اشتقاقهما هنا يمنع
    الخطأ **قبل** وقوعه بدل أن يفجّره في وجه المستخدم برسالة قاعدة بيانات.
    """
    if (spec.user_id is None) == (spec.team_id is None):
        raise ValueError("الحدث إمّا لطالب وإمّا لسرب — لا كلاهما ولا لا أحد.")

    individual = spec.user_id is not None
    return PointEvent(
        org_id=spec.org_id,
        scope="individual" if individual else "team",
        user_id=spec.user_id,
        team_id=spec.team_id,
        currency="hours" if individual else "fuel",
        delta=spec.delta,
        kind=spec.kind,
        reason=spec.reason,
        actor_id=spec.actor_id,
        external_ref=spec.external_ref,
        occurred_at=spec.occurred_at,
    )


def append(specs: list[EventSpec]) -> list[PointEvent]:
    """
    إلحاق ذرّي: إمّا كل الأحداث أو لا شيء.

    الدفعة الجزئية أسوأ من الفشل الكامل — يرى المشرف نصف سربه محدَّثًا ولا يعرف
    أين توقّف، فيعيد اللصق كلّه.
    """
    rows = [_row(s) for s in specs]
    db.session.add_all(rows)
    db.session.commit()
    return rows


def reverse(event: PointEvent, reason: str, actor_id: int) -> PointEvent:
    """
    التصحيح **حدث معاكس** لا `UPDATE` — والمشغّل في القاعدة يمنع البديل (ث-٢).

    والسبب إلزامي: تصحيحٌ بلا سبب يظهر في بطاقة الطالب كتلاعب.
    """
    if not reason or not reason.strip():
        raise ValueError("التصحيح يوجب سببًا مكتوبًا.")

    return append(
        [
            EventSpec(
                org_id=event.org_id,
                kind="correction",
                delta=-event.delta,
                occurred_at=event.occurred_at,  # لا now(): التصحيح يخصّ لحظة الأصل
                user_id=event.user_id,
                team_id=event.team_id,
                reason=reason.strip(),
                actor_id=actor_id,
            )
        ]
    )[0]
