"""
الأوزان والعتبات — و-٧ · FR-081 · FR-082.

**عمليتان مختلفتا الطبيعة تمامًا رغم تشابه الشكل:**
- الأوزان **تُؤرَّخ** (`effective_from`) لأنها ترتبط بلحظة وقوع الإنجاز (ث-١١).
- العتبات **لا تُؤرَّخ** — تمثّل معيارًا حاليًّا، لا سجلًّا ماليًّا. حمايتها من
  إعادة تفسير الماضي بأثر رجعي تمرّ بمِسنَن `users.highest_achieved_tier` لا
  بإصدارات (`docs/archive/slices/و-٧.md` §الرتب لا تنخفض).

@implements FR-081, FR-082
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from itertools import count

from sqlalchemy import func, select

from ..extensions import db
from ..models import (
    MasteryMultiplier,
    Membership,
    Org,
    PointEvent,
    RankThreshold,
    User,
    Weight,
    WeightVersion,
)
from ..rules.engine import CENT
from . import audit, week
from .errors import ServiceError


class RulesAdminError(ServiceError):
    """خطأ نطاق rules_admin — الاسمُ يبقى لأن المسارات تُلقّط به (`services/errors.py`)."""


# ═══ الأوزان — FR-081 ═══


def _local_start_of_day_utc(org: Org, d: date) -> datetime:
    """بدايةُ اليوم بتوقيت الجمعية — المالكُ `services/week.py` (و-٢٢)."""
    return week.start_of_day_utc(org, d)


def list_weights(org_id: int) -> dict:
    """الإصدار الأحدث بتفصيله، وتاريخ الإصدارات السابقة موجزًا."""
    versions = db.session.scalars(
        select(WeightVersion)
        .where(WeightVersion.org_id == org_id)
        .order_by(WeightVersion.effective_from.desc())
    ).all()
    if not versions:
        return {"current": None, "history": []}

    current = versions[0]
    weights = db.session.execute(
        select(Weight.activity_type, Weight.hours_per_unit).where(Weight.version_id == current.id)
    ).all()
    multipliers = db.session.execute(
        select(MasteryMultiplier.grade, MasteryMultiplier.multiplier).where(
            MasteryMultiplier.version_id == current.id
        )
    ).all()
    return {
        "current": {
            "id": current.id,
            "effective_from": current.effective_from,
            "note": current.note,
            "weights": [{"activity_type": a, "hours_per_unit": h} for a, h in weights],
            "multipliers": [{"grade": g, "multiplier": m} for g, m in multipliers],
        },
        "history": [
            {"id": v.id, "effective_from": v.effective_from, "note": v.note} for v in versions[1:]
        ],
    }


def create_weight_version(
    org,
    effective_from: date,
    weights: dict[str, Decimal],
    multipliers: dict[str, Decimal],
    note: str | None,
    actor_id: int,
) -> WeightVersion:
    """
    إصدارٌ **جديد** — لا `UPDATE` على إصدار قائم (ث-١١): تعديل إصدار قائم يمسّ
    كل حساب سابق استعمله، بخلاف إصدار جديد بتاريخ سريان لاحق.
    """
    new_effective = _local_start_of_day_utc(org, effective_from)

    latest = db.session.scalar(
        select(WeightVersion)
        .where(WeightVersion.org_id == org.id)
        .order_by(WeightVersion.effective_from.desc())
        .limit(1)
    )
    if latest is not None:
        if new_effective <= latest.effective_from:
            raise RulesAdminError("تاريخ السريان يجب أن يلي آخر إصدار قائم.")

        latest_activities = set(
            db.session.scalars(select(Weight.activity_type).where(Weight.version_id == latest.id))
        )
        missing = latest_activities - set(weights)
        if missing:
            # نشاطٌ يغيب عن الإصدار الجديد يصير مستحيل الاحتساب فجأة — والخطأ
            # يظهر لاحقًا في وجه طالب لا مشرف (`rules/engine.hours_for` يرفع
            # ValueError عند الاستدعاء الفعلي، لا عند إنشاء الإصدار).
            raise RulesAdminError(
                f"الإصدار الجديد يُسقِط أنشطة كانت محتسَبة في الإصدار الحالي: {sorted(missing)}"
            )

    version = WeightVersion(
        org_id=org.id, effective_from=new_effective, created_by=actor_id, note=note
    )
    db.session.add(version)
    db.session.flush()

    for activity, per_unit in weights.items():
        db.session.add(
            Weight(version_id=version.id, activity_type=activity, hours_per_unit=per_unit)
        )
    for grade, mult in multipliers.items():
        db.session.add(MasteryMultiplier(version_id=version.id, grade=grade, multiplier=mult))

    audit.record(
        org_id=org.id,
        kind="weights_version",
        summary=f"إصدار أوزان جديد ساري من {effective_from.isoformat()}",
        actor_id=actor_id,
        after={"version_id": version.id, "effective_from": effective_from.isoformat()},
    )
    db.session.commit()
    return version


# ═══ العتبات — FR-082 ═══


@dataclass(frozen=True)
class ThresholdRow:
    key: str
    name: str
    tier: int
    at_hours: Decimal


def list_thresholds(org_id: int) -> list[RankThreshold]:
    return list(
        db.session.scalars(
            select(RankThreshold).where(RankThreshold.org_id == org_id).order_by(RankThreshold.tier)
        )
    )


def _validate_rows(org_id: int, rows: list[ThresholdRow]) -> None:
    existing_keys = {r.key for r in list_thresholds(org_id)}
    submitted_keys = {r.key for r in rows}
    removed = existing_keys - submitted_keys
    if removed:
        # لا حذف رتبة أبدًا — من بلغها يفقدها صامتًا. الإضافة وحدها مسموحة.
        raise RulesAdminError(f"لا يجوز حذف رتب قائمة: {sorted(removed)}")

    by_tier = sorted(rows, key=lambda r: r.tier)
    if len({r.tier for r in rows}) != len(rows) or len({r.at_hours for r in rows}) != len(rows):
        raise RulesAdminError("سُلّم الرتب غير متّسق: قيم tier أو at_hours مكرَّرة.")
    for prev, cur in zip(by_tier, by_tier[1:], strict=False):
        if cur.at_hours <= prev.at_hours:
            # نفس رسالة مشغّل ث-١٣أ عمدًا — رسالة الخدمة أوضح للمشرف، والقاعدة
            # هي الضمانة الحقيقية إن نُسي هذا الفحص التمهيدي يومًا (ADR-002).
            raise RulesAdminError("سُلّم الرتب غير متّسق: تدرّج tier يجب أن يوافقه تدرّج at_hours.")


def _active_users_hours(org_id: int) -> dict[int, Decimal]:
    """رصيد كل طالب نشط — **تراكميّ لا نافذة**: الرتبة صفة عمر لا أسبوع."""
    rows = db.session.execute(
        select(User.id, func.coalesce(func.sum(PointEvent.delta), 0))
        .join(Membership, Membership.user_id == User.id)
        .outerjoin(
            PointEvent,
            (PointEvent.user_id == User.id)
            & (PointEvent.org_id == org_id)
            & (PointEvent.scope == "individual"),
        )
        .where(User.org_id == org_id, User.is_active.is_(True), Membership.left_at.is_(None))
        .group_by(User.id)
    ).all()
    return {uid: Decimal(hours).quantize(CENT) for uid, hours in rows}


def _tier_at(hours: Decimal, ladder: list[RankThreshold]) -> int:
    """
    موضع الرتبة الحيّة تحت سُلّمٍ معيَّن — **نفس منطق `deck.py::build`** حرفيًّا
    (أدنى رتبة أرضية لا يُسقَط منها)، مكرَّر عمدًا لا مستورَدًا: `deck.py` يقرأ
    القاعدة الحيّة، وهذه الدالّة تقيس سُلّمًا **قد يكون افتراضيًّا لم يُحفَظ بعد**
    (معاينة) — دمجهما يُدخل حالة «معاينة» في ملفّ ممنوعٍ عليه الكتابة.
    """
    sorted_ladder = sorted(ladder, key=lambda r: r.at_hours)
    reached = [r for r in sorted_ladder if hours >= r.at_hours]
    return reached[-1].tier if reached else sorted_ladder[0].tier


def _persisted_tiers(org_id: int) -> dict[int, int]:
    rows = db.session.execute(
        select(User.id, User.highest_achieved_tier).where(
            User.org_id == org_id, User.is_active.is_(True)
        )
    ).all()
    return dict(rows)


def preview_thresholds(org, rows: list[ThresholdRow]) -> dict:
    """
    **بلا كتابة.** من يرتفع ومن ينخفض تحت السُّلّم المقترَح.

    `demoted` فارغ **بالبناء لا بالصدفة** (و-٧ · ت-٢): لكل طالب `floor` هو
    `max(المِسنَن المحفوظ, رتبته الحيّة تحت السُّلّم *الحالي*)` — وهذا بالضبط ما
    سيُقفَل عليه لحظة الحفظ قبل استبدال السُّلّم. والرتبة بعد التغيير **لا يمكن
    رياضيًّا أن تقلّ عن** `floor` لأنها `max(floor, الرتبة تحت السُّلّم الجديد)`.
    """
    _validate_rows(org.id, rows)

    old_ladder = list_thresholds(org.id)
    persisted = _persisted_tiers(org.id)
    users_hours = _active_users_hours(org.id)

    promoted, demoted = [], []
    for user_id, hours in users_hours.items():
        floor = max(persisted.get(user_id, 0), _tier_at(hours, old_ladder))
        after = max(floor, _tier_at(hours, rows))
        if after > floor:
            promoted.append({"user_id": user_id, "from_tier": floor, "to_tier": after})
        elif after < floor:  # لا يقع رياضيًّا — الإثبات العدائي يستهدف هذا الشرط
            demoted.append({"user_id": user_id, "from_tier": floor, "to_tier": after})

    return {"promoted": promoted, "demoted": demoted, "warning": None}


def append_threshold(org, name: str, at_hours: Decimal, actor_id: int) -> dict:
    """
    رتبةٌ جديدة **في قمّة السُّلّم وحدها** — «+ إضافة رتبة» في النموذج (و-٢١).

    **ولماذا القمّة لا أيّ موضع:** `users.highest_achieved_tier` مِسنَنٌ يحفظ
    *رقم* الرتبة لا هويّتها. فإدخالُ رتبةٍ في الوسط يُعيد ترقيم ما بعدها:
    طالبٌ مِسنَنُه ٣ («رائد سرب» عند ٩٠٠) يصير ٣ رتبةً جديدة عند ٦٠٠ — **تنزيلٌ
    صامت في المعنى** بلا أن ينقص الرقم، فلا يُطلقه مشغّل ث-١٣ب ولا يراه أحد.
    وإصلاحُه هجرةٌ تحوّل المِسنَن إلى مفتاح، وهو قرارُ منتج لا زرّ.

    والإلحاق في القمّة **بلا هذا الأثر بالبناء**: ما قبله لا يتغيّر رقمه ولا
    عتبته، ولا طالب كان قد بلغ ما لم يكن موجودًا.

    **ويُحسَب `tier` في الخادم لا في الواجهة:** موضعُ الرتبة في السُّلّم قاعدةٌ
    لا عرض («الواجهة تعرض ولا تحسب»)، وحسابُه في العميل يعني رقمًا يصل
    القاعدة بلا أن يحرسه أحد.
    """
    ladder = list_thresholds(org.id)
    if not ladder:
        raise RulesAdminError("لا سُلّم رتب في هذه الجمعية — التأسيس ينشئه.")

    top = max(ladder, key=lambda r: r.tier)
    if at_hours <= top.at_hours:
        raise RulesAdminError(
            f"الرتبة الجديدة في قمّة السُّلّم، فعتبتها يجب أن تتجاوز "
            f"{top.at_hours} ساعة (عتبة «{top.name}»)."
        )

    key = _free_key({r.key for r in ladder})
    rows = [ThresholdRow(key=r.key, name=r.name, tier=r.tier, at_hours=r.at_hours) for r in ladder]
    rows.append(ThresholdRow(key=key, name=name.strip(), tier=top.tier + 1, at_hours=at_hours))

    # **يمرّ بـ`save_thresholds` لا بإدراجٍ مباشر:** هناك يقع قفل الأرضيات
    # وفحص تدرّج السُّلّم وسطر التدقيق. وإدراجٌ يتخطّاه يتخطّى ت-٢ كلّه.
    return save_thresholds(org, rows, actor_id)


def _free_key(taken: set[str]) -> str:
    """
    مفتاحٌ غير مستعمل. **لا يُشتقّ من الاسم العربيّ:** `key` معرّفٌ تقنيّ
    مستقرّ تُبنى عليه الأيقونات، وتعريبُه يجعل تغييرَ الاسم تغييرَ هويّة.
    """
    for index in count(start=len(taken) + 1):
        candidate = f"rank{index}"
        if candidate not in taken:
            return candidate
    raise AssertionError("unreachable")  # pragma: no cover


def save_thresholds(org, rows: list[ThresholdRow], actor_id: int) -> dict:
    """
    يحفظ ثم يُرجع **نفس شكل `preview_thresholds`** — فما رآه المشرف في المعاينة
    هو ما وقع فعلًا، لا حسابًا موازيًا قد يفترق عنه.
    """
    result = preview_thresholds(org, rows)  # يفحص ويحسب بلا كتابة — قبل أي تغيير

    old_ladder = list_thresholds(org.id)
    before = [
        {"key": r.key, "name": r.name, "tier": r.tier, "at_hours": str(r.at_hours)}
        for r in old_ladder
    ]

    # (١) قفل ما بلغه كل طالب تحت السُّلّم **الحالي قبل استبداله** — هذه هي
    # اللحظة الوحيدة التي يُرى فيها ذلك السُّلّم القديم؛ بعد الاستبدال يضيع.
    for user_id, hours in _active_users_hours(org.id).items():
        pre_tier = _tier_at(hours, old_ladder)
        db.session.execute(
            db.text(
                "UPDATE users SET highest_achieved_tier = GREATEST(highest_achieved_tier, :v) "
                "WHERE id = :uid"
            ),
            {"v": pre_tier, "uid": user_id},
        )

    # (٢) استبدال السُّلّم: تحديث القائم، وإدراج المفاتيح الجديدة فقط (لا حذف).
    existing = {r.key: r for r in old_ladder}
    for row in rows:
        if row.key in existing:
            existing[row.key].name = row.name
            existing[row.key].tier = row.tier
            existing[row.key].at_hours = row.at_hours
        else:
            db.session.add(
                RankThreshold(
                    org_id=org.id, key=row.key, name=row.name, tier=row.tier, at_hours=row.at_hours
                )
            )

    audit.record(
        org_id=org.id,
        kind="thresholds_update",
        summary="تحديث سُلّم الرتب",
        actor_id=actor_id,
        before={"thresholds": before},
        after={
            "thresholds": [
                {"key": r.key, "name": r.name, "tier": r.tier, "at_hours": str(r.at_hours)}
                for r in rows
            ]
        },
    )
    db.session.commit()
    return result
