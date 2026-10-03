"""
أسبوع الوقود — و-٢٠ · النموذج المعتمد.

**مسوّدةٌ ثمّ اعتمادٌ واحد.** الأسبوع يبدأ بقائمة المهامّ الافتراضية (الأنشطة
القائمة)، ويُعيّن المشرف سربًا لكل مهمّة ويضع الدرجات — وكلّه **مسوّدة لا أثر
لها في الدفتر**. ثم يعتمد الأسبوع مرّةً واحدة، فتُكتب أحداث الوقود **مؤرَّخةً
ببداية ذلك الأسبوع** لا باليوم.

**ولماذا التأريخ بالأسبوع لا باليوم؟** لأن التقييم قد يتأخّر (قرار المستخدم):
المشرف يرجع إلى أسبوعٍ مضى فيقيّمه، فلو أُرّخ بلحظة الاعتماد لانتقلت لتراتُ
أسبوعٍ ماضٍ إلى أسبوعٍ حاضر — فيتغيّر ترتيبٌ لم يصنعه أحد.

**وق-٦٧ باقٍ:** المسوّدة في `fuel_week_scores`، ولا يُخلَق صفٌّ في
`fuel_assessments` إلا ومعه حدثُه في المعاملة نفسها.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import (
    FuelActivity,
    FuelAssessment,
    FuelCriterion,
    FuelScore,
    FuelWeek,
    FuelWeekScore,
    FuelWeekTask,
    Org,
    Team,
)
from . import audit, ledger
from .fuel import FuelError, assert_weights_sum_100, local_start_of_day_utc, score_totals


def _active_activities(org_id: int) -> list[FuelActivity]:
    return list(
        db.session.scalars(
            select(FuelActivity)
            .where(FuelActivity.org_id == org_id, FuelActivity.archived_at.is_(None))
            .order_by(FuelActivity.id)
        )
    )


def _criteria_of(activity_id: int) -> list[FuelCriterion]:
    return list(
        db.session.scalars(
            select(FuelCriterion)
            .where(FuelCriterion.activity_id == activity_id)
            .order_by(FuelCriterion.position)
        )
    )


def _week_row(org_id: int, week_start: date) -> FuelWeek | None:
    return db.session.scalar(
        select(FuelWeek).where(FuelWeek.org_id == org_id, FuelWeek.week_start == week_start)
    )


def _ensure_week(org: Org, week_start: date) -> FuelWeek:
    """
    يفتح الأسبوع عند **أوّل تعديل** لا عند العرض.

    العرضُ لا يكتب: أسبوعٌ لم يُفتح بعد يُعرَض بقائمته الافتراضية ومعرّفاتٍ
    عدم، فتصفّحُ الأسابيع الماضية لا يترك خلفه صفوفًا فارغة لكل أسبوع مرّ به
    المشرف.
    """
    week = _week_row(org.id, week_start)
    if week is not None:
        return week

    week = FuelWeek(org_id=org.id, week_start=week_start)
    db.session.add(week)
    try:
        db.session.flush()
    except IntegrityError:
        # سباقٌ على الفتح — الأسبوع موجود الآن، فيُقرأ لا يُعاد إنشاؤه.
        db.session.rollback()
        existing = _week_row(org.id, week_start)
        if existing is None:
            raise
        return existing

    # القائمة الافتراضية تُنسَخ مهامَّ لهذا الأسبوع (قرار المستخدم) — ثم
    # يُضيف المشرف ويُزيل **لهذا الأسبوع وحده**.
    for activity in _active_activities(org.id):
        db.session.add(FuelWeekTask(week_id=week.id, activity_id=activity.id))
    db.session.flush()
    return week


def _guard_open(week: FuelWeek | None) -> None:
    if week is not None and week.approved_at is not None:
        raise FuelError("هذا الأسبوع مُعتمَد — لا يُعدَّل بعد الاعتماد.", status=409)


def _task(org: Org, week_start: date, activity_id: int) -> FuelWeekTask:
    week = _week_row(org.id, week_start)
    _guard_open(week)
    week = _ensure_week(org, week_start)
    task = db.session.scalar(
        select(FuelWeekTask).where(
            FuelWeekTask.week_id == week.id, FuelWeekTask.activity_id == activity_id
        )
    )
    if task is None:
        raise FuelError("هذه المهمّة ليست في هذا الأسبوع.", status=404)
    return task


# ═══ العرض ═══


def week_view(org: Org, week_start: date) -> dict:
    """
    حالة الأسبوع كاملةً — **بلا كتابة**.

    `state`: `'unopened'` لم يُلمَس بعد · `'draft'` مسوّدة · `'approved'`
    اعتُمد. وهذا الحقل هو «الوضوح التام» المطلوب: لا يُخمَّن من غياب الدرجات.
    """
    week = _week_row(org.id, week_start)
    teams = {
        t.id: t.name
        for t in db.session.scalars(
            select(Team).where(Team.org_id == org.id, Team.archived_at.is_(None))
        )
    }

    if week is None:
        rows: list[FuelWeekTask] = []
        activities = _active_activities(org.id)
        state = "unopened"
        approved_at = None
    else:
        rows = list(
            db.session.scalars(
                select(FuelWeekTask)
                .where(FuelWeekTask.week_id == week.id)
                .order_by(FuelWeekTask.id)
            )
        )
        activities = list(
            db.session.scalars(
                select(FuelActivity).where(
                    FuelActivity.id.in_([t.activity_id for t in rows] or [-1])
                )
            )
        )
        state = "approved" if week.approved_at is not None else "draft"
        approved_at = week.approved_at.isoformat() if week.approved_at else None

    # ثلاث دفعات لا ثلاثة استعلامات لكل مهمّة: الأنشطة أعلاه، والبنود
    # والدرجات هنا. شاشةٌ تُفتح كثيرًا ومهامُّها تنمو — فثمنُها يجب أن يبقى
    # ثابتًا (نفس علاج `list_teams`، وتحرسه ق-٢٥٥).
    by_activity = {a.id: a for a in activities}
    criteria_of: dict[int, list[FuelCriterion]] = {}
    if by_activity:
        for criterion in db.session.scalars(
            select(FuelCriterion)
            .where(FuelCriterion.activity_id.in_(list(by_activity)))
            .order_by(FuelCriterion.position)
        ):
            criteria_of.setdefault(criterion.activity_id, []).append(criterion)

    scores_of: dict[int, dict[int, Decimal]] = {}
    if rows:
        for row in db.session.scalars(
            select(FuelWeekScore).where(FuelWeekScore.task_id.in_([t.id for t in rows]))
        ):
            scores_of.setdefault(row.task_id, {})[row.criterion_id] = row.score_pct

    ordered = (
        [(t.activity_id, t.team_id, scores_of.get(t.id, {})) for t in rows]
        if rows
        else [(a.id, None, {}) for a in activities]
    )

    out_tasks = []
    for activity_id, team_id, saved in ordered:
        activity = by_activity.get(activity_id)
        if activity is None:
            continue
        criteria = criteria_of.get(activity.id, [])
        valid = {c.id for c in criteria}
        scored = {cid: v for cid, v in saved.items() if cid in valid}
        total_pct, litres = (
            score_totals({c.id: c for c in criteria}, scored, activity.litres_full)
            if scored
            else (Decimal("0.00"), Decimal("0.00"))
        )
        out_tasks.append(
            {
                "activity_id": activity.id,
                "name": activity.name,
                "litres_full": activity.litres_full,
                "team_id": team_id,
                "team_name": teams.get(team_id) if team_id else None,
                "assessed": bool(scored),
                "total_pct": total_pct,
                "litres": litres,
                "criteria": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "weight_pct": c.weight_pct,
                        "score_pct": saved.get(c.id),
                    }
                    for c in criteria
                ],
            }
        )

    # **ما يصلح أن يُضاف لهذا الأسبوع** — «+ إضافة مهمة لهذا الأسبوع» في
    # النموذج (و-٢١). يُحسَب في الخادم لا في الواجهة: الفرقُ بين كلّ الأنشطة
    # ومهامِّ الأسبوع قاعدةٌ لا عرض، وجلبُه بنداءٍ ثانٍ من الشاشة يُدخل شلّالًا
    # في شاشةٍ تُفتح كثيرًا.
    #
    # وفارغةٌ حين `unopened` بالبناء لا بالشرط: الأسبوع الذي لم يُلمَس يعرض
    # **كل** الأنشطة مهامَّ افتراضية، فلا شيء خارجها يُضاف.
    assigned = {t.activity_id for t in rows}
    available = [
        {"id": a.id, "name": a.name}
        for a in (_active_activities(org.id) if week is not None else [])
        if a.id not in assigned
    ]

    return {
        "week_start": week_start.isoformat(),
        "state": state,
        "approved_at": approved_at,
        "tasks": out_tasks,
        "teams": [{"id": i, "name": n} for i, n in sorted(teams.items())],
        "available": available,
    }


# ═══ التعديل — كلّه مسوّدة ═══


def set_task_team(org: Org, week_start: date, activity_id: int, team_id: int | None) -> dict:
    task = _task(org, week_start, activity_id)
    if team_id is not None:
        team = db.session.get(Team, team_id)
        if team is None or team.org_id != org.id:
            raise FuelError("لا سرب بهذا المعرّف.", status=404)
    # لا قيد تفرّد على (أسبوع، سرب): «لكل سرب مهمّة واحدة» إرشادٌ لا قيد.
    task.team_id = team_id
    db.session.commit()
    return week_view(org, week_start)


def add_task(org: Org, week_start: date, activity_id: int) -> dict:
    activity = db.session.get(FuelActivity, activity_id)
    if activity is None or activity.org_id != org.id:
        raise FuelError("لا نشاط بهذا المعرّف.", status=404)
    week = _week_row(org.id, week_start)
    _guard_open(week)
    week = _ensure_week(org, week_start)
    db.session.add(FuelWeekTask(week_id=week.id, activity_id=activity_id))
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise FuelError("هذه المهمّة مضافة لهذا الأسبوع أصلًا.", status=409) from exc
    return week_view(org, week_start)


def remove_task(org: Org, week_start: date, activity_id: int) -> dict:
    """إزالةٌ **لهذا الأسبوع وحده** — لا تمسّ النشاط ولا أسبوعًا آخر."""
    task = _task(org, week_start, activity_id)
    db.session.query(FuelWeekScore).filter(FuelWeekScore.task_id == task.id).delete()
    db.session.delete(task)
    db.session.commit()
    return week_view(org, week_start)


def save_scores(org: Org, week_start: date, activity_id: int, scores: dict[int, Decimal]) -> dict:
    """درجاتٌ مسوّدة — **لا حدث دفتر**، ولا فحص «تجمع ١٠٠٪» إلا عند الاعتماد."""
    task = _task(org, week_start, activity_id)
    valid = {c.id for c in _criteria_of(activity_id)}
    unknown = set(scores) - valid
    if unknown:
        raise FuelError(f"بنود لا تنتمي لهذا النشاط: {sorted(unknown)}")

    db.session.query(FuelWeekScore).filter(FuelWeekScore.task_id == task.id).delete()
    for cid, score in scores.items():
        db.session.add(FuelWeekScore(task_id=task.id, criterion_id=cid, score_pct=score))
    db.session.commit()
    return week_view(org, week_start)


# ═══ الاعتماد — إجراءٌ واحد لا رجعة فيه ═══


def approve_week(org: Org, week_start: date, actor_id: int, now: datetime) -> dict:
    """
    يصبّ الأسبوع في وقود كل سرب — **مرّةً واحدة**.

    كلُّ مهمّة مُقيَّمة ولها سرب تُنتج تقييمًا وحدثَ دفترٍ مؤرَّخًا **ببداية
    الأسبوع**. والمهامّ بلا سرب أو بلا درجات تُتخطّى بلا ضجيج — ويُبلَّغ عددُها
    في الردّ فلا يُظنّ أنها احتُسبت.
    """
    week = _week_row(org.id, week_start)
    if week is None:
        raise FuelError("هذا الأسبوع لم يُفتح بعد — لا شيء لاعتماده.", status=404)
    if week.approved_at is not None:
        raise FuelError("هذا الأسبوع مُعتمَد من قبل.", status=409)

    occurred_at = local_start_of_day_utc(org, week_start)
    tasks = db.session.scalars(
        select(FuelWeekTask).where(FuelWeekTask.week_id == week.id).order_by(FuelWeekTask.id)
    ).all()

    written = 0
    skipped = 0
    total_litres = Decimal("0.00")

    for task in tasks:
        activity = db.session.get(FuelActivity, task.activity_id)
        scores = {
            s.criterion_id: s.score_pct
            for s in db.session.scalars(
                select(FuelWeekScore).where(FuelWeekScore.task_id == task.id)
            )
        }
        if activity is None or task.team_id is None or not scores:
            skipped += 1
            continue

        criteria = {c.id: c for c in _criteria_of(activity.id)}
        assert_weights_sum_100([criteria[cid].weight_pct for cid in scores], "البنود المُقيَّمة")
        total_pct, litres = score_totals(criteria, scores, activity.litres_full)

        event = ledger.append(
            [
                ledger.EventSpec(
                    org_id=org.id,
                    kind="fuel",
                    delta=litres,
                    team_id=task.team_id,
                    occurred_at=occurred_at,
                    actor_id=actor_id,
                )
            ]
        )[0]
        assessment = FuelAssessment(
            org_id=org.id,
            team_id=task.team_id,
            activity_id=activity.id,
            occurred_on=week_start,
            total_pct=total_pct,
            litres=litres,
            note=None,
            actor_id=actor_id,
            week_task_id=task.id,
            point_event_id=event.id,
        )
        db.session.add(assessment)
        db.session.flush()
        for cid, score in scores.items():
            db.session.add(
                FuelScore(assessment_id=assessment.id, criterion_id=cid, score_pct=score)
            )
        written += 1
        total_litres += litres

    week.approved_at = now
    week.approved_by = actor_id

    audit.record(
        org_id=org.id,
        kind="fuel_week_approved",
        summary=(
            f"اعتماد أسبوع الوقود {week_start.isoformat()}: "
            f"{written} مهمّة بمجموع {total_litres} لتر"
        ),
        actor_id=actor_id,
        after={
            "week_start": week_start.isoformat(),
            "assessments": written,
            "skipped": skipped,
            "litres": str(total_litres),
        },
    )
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise FuelError("تصادمٌ في الاعتماد — حدِّث الصفحة وحاول مجدَّدًا.", status=409) from exc

    return week_view(org, week_start)


# ═══ الشقّ الطيّاريّ — محطة التزوّد ═══


def team_task_this_week(org: Org, team_id: int, week_start: date) -> dict | None:
    """
    مهمّة السرب في أسبوعٍ بعينه — لمحطة التزوّد (`GET /me/station`).

    **يرى الطالب المسوّدة وحالتَها.** النموذج المعتمد يعرض «مسوّدة — بانتظار
    اعتماد المشرف»، وهذا مقصود: السرب يعرف ما يُقيَّم عليه **قبل** أن يُحتسب،
    لا بعده. ولا يلتبس ذلك بالوقود المحتسَب — اللترات هنا **متوقَّعة** حتى
    يُعتمد الأسبوع، وحقلُ `state` هو ما يفصل بينهما.

    `None` لسربٍ بلا مهمّة هذا الأسبوع — حالةٌ مصمَّمة لا عطل.
    """
    week = _week_row(org.id, week_start)
    if week is None:
        return None

    task = db.session.scalar(
        select(FuelWeekTask).where(FuelWeekTask.week_id == week.id, FuelWeekTask.team_id == team_id)
    )
    if task is None:
        return None

    activity = db.session.get(FuelActivity, task.activity_id)
    if activity is None:
        return None

    criteria = {c.id: c for c in _criteria_of(activity.id)}
    scores = {
        s.criterion_id: s.score_pct
        for s in db.session.scalars(select(FuelWeekScore).where(FuelWeekScore.task_id == task.id))
        if s.criterion_id in criteria
    }
    total_pct, litres = (
        score_totals(criteria, scores, activity.litres_full)
        if scores
        else (Decimal("0.00"), Decimal("0.00"))
    )
    return {
        "name": activity.name,
        "state": "approved" if week.approved_at is not None else "draft",
        "assessed": bool(scores),
        "total_pct": total_pct,
        "litres": litres,
    }
