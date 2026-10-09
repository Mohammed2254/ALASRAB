"""
الوقود — و-٨ · FR-070 · FR-071 · FR-072.

**عملة جماعية منفصلة تمامًا لا تمرّ بـ`rules/engine.py`** — لا `Achievement` ولا
`ruleset_at`؛ حسابٌ مختلف لعملة مختلفة (`RULES.md` §١، `ARCHITECTURE.md`
«`rules/` لا تملك: ❌ الوقود»). `ledger.append` وحده هو المشترك، وهو **بلا أي
تعديل** — القيد `currency_scope_match` يستوعب `fuel`/`team` منذ و-١.

@implements FR-070, FR-071, FR-072
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import FuelActivity, FuelAssessment, FuelCriterion, FuelScore, PointEvent
from . import audit, ledger

CENT = Decimal("0.01")
RECENT_LIMIT = 10


class FuelError(Exception):
    """خطأ عملٍ يُترجَم إلى رمز حالة في المسار — لا يعرف HTTP (نمط `ReadingError`)."""

    def __init__(self, message: str, status: int = 422):
        self.status = status
        super().__init__(message)


def local_start_of_day_utc(org, d: date) -> datetime:
    """
    `RULES.md` §٩ — نفس تحويل `reading.occurred_at_for` و`rules_admin`،
    مكرَّر عمدًا لا مستورَدًا (ثلاثة أسطر لا تبرّر اقتران و-٨ بوحدة أخرى).
    """
    return datetime.combine(d, time.min, tzinfo=ZoneInfo(org.timezone)).astimezone(UTC)


def score_totals(
    criteria: dict[int, FuelCriterion], scores: dict[int, Decimal], litres_full: Decimal
) -> tuple[Decimal, Decimal]:
    """
    (نسبةٌ مئوية، لترات) من درجات البنود — **حسابٌ واحد** يستعمله التقييم
    المباشر والاعتماد الأسبوعيّ معًا، فلا يفترقان في رقمٍ يراه السرب.
    """
    total_pct = sum(
        (Decimal(score) * criteria[cid].weight_pct / 100 for cid, score in scores.items()),
        Decimal(0),
    ).quantize(CENT, rounding=ROUND_HALF_UP)
    litres = (total_pct / 100 * litres_full).quantize(CENT, rounding=ROUND_HALF_UP)
    return total_pct, litres


def assert_weights_sum_100(weights: list[Decimal], label: str) -> None:
    total = sum(weights, Decimal(0))
    if total != 100:
        raise FuelError(f"أوزان {label} يجب أن تجمع ١٠٠٪ بالضبط — المجموع الحالي {total}.")


# ═══ الأنشطة — بنية تحتية لـ FR-070 ═══


def list_activities(org_id: int) -> list[dict]:
    activities = db.session.scalars(
        select(FuelActivity)
        .where(FuelActivity.org_id == org_id, FuelActivity.archived_at.is_(None))
        .order_by(FuelActivity.id)
    ).all()
    result = []
    for a in activities:
        criteria = db.session.scalars(
            select(FuelCriterion)
            .where(FuelCriterion.activity_id == a.id)
            .order_by(FuelCriterion.position)
        ).all()
        result.append(
            {
                "id": a.id,
                "key": a.key,
                "name": a.name,
                "litres_full": a.litres_full,
                "criteria": [
                    {"id": c.id, "key": c.key, "name": c.name, "weight_pct": c.weight_pct}
                    for c in criteria
                ],
            }
        )
    return result


def create_activity(
    org, key: str, name: str, litres_full: Decimal, criteria: list[dict]
) -> FuelActivity:
    """
    إنشاءٌ **جديد** — لا تعديل على نشاط قائم. **ث-١٠أ** يُفحص هنا (رسالة
    واضحة للمشرف) وفي القاعدة (`fuel_criteria_sum_100`، دفاعٌ حقيقي إن نُسي
    هذا الفحص التمهيدي يومًا — ADR-002).
    """
    assert_weights_sum_100([Decimal(c["weight_pct"]) for c in criteria], "النشاط")

    activity = FuelActivity(org_id=org.id, key=key, name=name, litres_full=litres_full)
    db.session.add(activity)
    db.session.flush()

    for i, c in enumerate(criteria):
        db.session.add(
            FuelCriterion(
                activity_id=activity.id,
                key=c["key"],
                name=c["name"],
                weight_pct=Decimal(c["weight_pct"]),
                position=i,
            )
        )
    db.session.commit()
    return activity


# ═══ التقييم — FR-070 · FR-071 ═══


@dataclass(frozen=True)
class AssessmentResult:
    id: int
    total_pct: Decimal
    litres: Decimal


def assess(
    org,
    team_id: int,
    activity_id: int,
    occurred_on: date,
    scores: dict[int, Decimal],
    note: str | None,
    actor_id: int,
) -> AssessmentResult:
    """
    تقييمٌ **جديد** — لا حالة معلَّقة له (خلافًا للقراءة)، فيُلحق حدثه فورًا.

    **ث-١٠ب** يُفحص هنا وفي القاعدة (`fuel_scores_sum_100`، مؤجَّل لنهاية
    المعاملة): مجموع أوزان البنود **المُقيَّمة فعلًا** = ١٠٠٪، لا كل بنود
    النشاط بالضرورة — يمسك انجرافًا بعد تعريف سليم أو تغطية جزئية.
    """
    activity = db.session.get(FuelActivity, activity_id)
    if activity is None or activity.org_id != org.id:
        raise FuelError("لا نشاط بهذا المعرّف.", status=404)

    criteria = {
        c.id: c
        for c in db.session.scalars(
            select(FuelCriterion).where(FuelCriterion.activity_id == activity_id)
        )
    }
    unknown = set(scores) - set(criteria)
    if unknown:
        raise FuelError(f"بنود لا تنتمي لهذا النشاط: {sorted(unknown)}")

    assert_weights_sum_100([criteria[cid].weight_pct for cid in scores], "البنود المُقيَّمة")

    total_pct, litres = score_totals(criteria, scores, activity.litres_full)

    occurred_at = local_start_of_day_utc(org, occurred_on)
    # لا external_ref هنا عمدًا: منع التكرار مملوك بالكامل لقيد
    # `uq_fuel_assessment_per_day` أدناه. لو مُنح الحدث external_ref حتميًّا من
    # نفس المفتاح الطبيعي (سرب+نشاط+يوم)، لاصطدم تكرارٌ بقيد `point_events`
    # أوّلًا برسالة IntegrityError خام غير معالَجة — **أُثبت هذا فعليًّا**، لا
    # افتُرض: محاولة تكرار كانت تسقط بـ٥٠٠ قبل هذا التصحيح، لا ٤٠٩ الموثَّق.
    event = ledger.append(
        [
            ledger.EventSpec(
                org_id=org.id,
                kind="fuel",
                delta=litres,
                team_id=team_id,
                occurred_at=occurred_at,
                actor_id=actor_id,
            )
        ]
    )[0]

    assessment = FuelAssessment(
        org_id=org.id,
        team_id=team_id,
        activity_id=activity_id,
        occurred_on=occurred_on,
        total_pct=total_pct,
        litres=litres,
        note=note,
        actor_id=actor_id,
        point_event_id=event.id,
    )
    db.session.add(assessment)
    try:
        db.session.flush()
    except IntegrityError as exc:
        db.session.rollback()
        raise FuelError("هذا النشاط مُقيَّم لهذا السرب في هذا اليوم من قبل.", status=409) from exc

    for cid, score in scores.items():
        db.session.add(FuelScore(assessment_id=assessment.id, criterion_id=cid, score_pct=score))

    audit.record(
        org_id=org.id,
        kind="fuel_assessment",
        summary=f"تقييم «{activity.name}» — {total_pct}٪",
        actor_id=actor_id,
        after={"assessment_id": assessment.id, "litres": str(litres)},
    )
    db.session.commit()
    return AssessmentResult(id=assessment.id, total_pct=total_pct, litres=litres)


# ═══ محطة التزوّد — FR-072 ═══


def team_fuel(org_id: int, team_id: int) -> dict:
    """وقود السرب **تراكميًّا لا الفرد** (ث-١) وآخر تقييماته — يشرح الرقم (FR-071)."""
    total = db.session.scalar(
        select(db.func.coalesce(db.func.sum(PointEvent.delta), 0)).where(
            PointEvent.org_id == org_id,
            PointEvent.team_id == team_id,
            PointEvent.scope == "team",
            PointEvent.currency == "fuel",
        )
    )
    rows = db.session.execute(
        select(FuelAssessment, FuelActivity.name)
        .join(FuelActivity, FuelActivity.id == FuelAssessment.activity_id)
        .where(FuelAssessment.org_id == org_id, FuelAssessment.team_id == team_id)
        .order_by(FuelAssessment.occurred_on.desc(), FuelAssessment.id.desc())
        .limit(RECENT_LIMIT)
    ).all()
    return {
        "litres": Decimal(total).quantize(CENT),
        "recent": [
            {
                "activity_name": name,
                "occurred_on": a.occurred_on,
                "total_pct": a.total_pct,
                "litres": a.litres,
            }
            for a, name in rows
        ],
    }
