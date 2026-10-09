"""
تنسيق استيراد راصد — FR-030..034/040 (و-٥).

**`preview` بلا كتابة إطلاقًا، و`commit` يكتب `raw_rows` دائمًا** لكل صفّ
طالب حقيقيّ، ثم يُلحق أحداثًا **للصفوف الجديدة فقط** — أيّ (تاريخ، طالب،
نشاط) له `external_ref` قائم فعلًا يُستبعَد صراحةً بدل رفض الدفعة كلّها
(`docs/slices/و-٥.md` §٢.١ب): إعادة استيراد مصحَّحة لبعض الطلاب يجب أن تبقى
ممكنة للباقين.

@implements FR-030, FR-031, FR-032, FR-033, FR-034
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..ingest import rasd
from ..models import EntryDefault, Membership, Org, PointEvent, RawRow, Team
from ..rules.engine import Achievement, RuleSet, ruleset_at
from . import audit, ledger, week
from .errors import ServiceError
from .matching import match_names

SOURCE = "rasd"

# الفئات الثلاث القائمة على نسبة (kind='quran'، وزنٌ مستقلّ لكلٍّ، قرار #٣).
PERCENT_CATEGORIES = ("hifz", "thabat", "muraja3a")
QURAN_ACTIVITY = {cat: f"quran_{cat}" for cat in PERCENT_CATEGORIES}
ATTENDANCE_ACTIVITY = "attendance"
DISPLAY_PRECISION = Decimal("0.1")

# `entry_defaults.activity_type` ⇒ مفتاح صفّ `ingest/rasd` المطبَّع — قرار
# #١١: صفٌّ لكل عمود مصدر، لا لكل فئة (`docs/slices/و-٥.md` §٢.٢).
_ENTRY_DEFAULT_TO_KEY = {
    "quran_hifz_target": "hifz_target",
    "quran_hifz_achieved": "hifz_achieved",
    "quran_thabat_target": "thabat_target",
    "quran_thabat_achieved": "thabat_achieved",
    "quran_muraja3a_target": "muraja3a_target",
    "quran_muraja3a_achieved": "muraja3a_achieved",
    "attendance": "attendance",
    "tasmi3_days": "tasmi3_days",
}


def _load_column_config(org_id: int) -> tuple[dict[str, list[str]], dict[str, Decimal]]:
    """
    `entry_defaults` ⇒ (عمود كنسيّ ⇒ مرادفاته، مفتاح الصفّ ⇒ افتراضيّه) —
    منظّمة بلا صفوف `entry_defaults` تحصل على قواميس فارغة، فيسقط `rasd.parse`
    إلى الترويسة الكنسيّة والافتراض صفر — سلوكٌ متطابق مع الملفّين الحقيقيّين
    (بلا حاجة لبذر مسبَق ليعمل الاستيراد).
    """
    rows = db.session.scalars(select(EntryDefault).where(EntryDefault.org_id == org_id))
    aliases: dict[str, list[str]] = {}
    defaults: dict[str, Decimal] = {}
    for row in rows:
        aliases[row.label] = list(row.aliases)
        key = _ENTRY_DEFAULT_TO_KEY.get(row.activity_type)
        if key:
            defaults[key] = row.quantity
    return aliases, defaults


class PasteError(ServiceError):
    """خطأ نطاق paste — الاسمُ يبقى لأن المسارات تُلقّط به (`services/errors.py`)."""


def _local_today(org: Org) -> date:
    return datetime.now(ZoneInfo(org.timezone)).date()


def _occurred_at_for(org: Org, occurred_on: date) -> datetime:
    """بدايةُ اليوم بتوقيت الجمعية — المالكُ `services/week.py` (و-٢٢)."""
    return week.start_of_day_utc(org, occurred_on)


def _percent(target: Decimal, achieved: Decimal) -> Decimal:
    """
    نسبة داخلية دائمًا — **لا تُصدَّق نسبة راصد ولا «الإجمالي» أبدًا** (قرار #١).

    `مستهدف=٠ ⇒ نسبة=٠` صراحةً — حالة حقيقية موثَّقة في العيّنة الصغيرة، لا
    استثناء `ZeroDivisionError` يُسقط الصفّ كله.
    """
    if target == 0:
        return Decimal("0")
    return achieved / target * 100


def _external_ref(team_id: int, occurred_on: date, user_id: int, activity_type: str) -> str:
    """`{source}:{team}:{date}:{user}:{activity}` — `RULES.md` §٦ حرفيًّا."""
    return f"{SOURCE}:{team_id}:{occurred_on.isoformat()}:{user_id}:{activity_type}"


def _batch_id(org_id: int, occurred_on: date, rows: list[dict]) -> str:
    """
    SHA-256 مُقتضَب لمحتوى الدفعة كلّها — **حارس تكرار بالمجموع الاختباري**
    (قرار #٩): نفس الملفّ لنفس التاريخ ⇒ نفس القيمة حتمًا، فحصها استعلامٌ واحد.
    """
    payload = json.dumps(
        {"org": org_id, "date": occurred_on.isoformat(), "rows": [r["raw"] for r in rows]},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _row_percentages(row: dict) -> dict[str, Decimal]:
    return {
        cat: _percent(row[f"{cat}_target"], row[f"{cat}_achieved"]) for cat in PERCENT_CATEGORIES
    }


def _already_imported(org_id: int, external_ref: str) -> bool:
    """
    فحصٌ استباقي **قبل** الإلحاق — لا اعتمادًا وحيدًا على `uq_event_external_ref`
    (الذي يبقى حارسًا أخيرًا لأي تسابق، لا الآلية الأساسية، `docs/slices/و-٥.md` §٢.١ب).
    """
    return (
        db.session.scalar(
            select(PointEvent.id)
            .where(PointEvent.org_id == org_id, PointEvent.external_ref == external_ref)
            .limit(1)
        )
        is not None
    )


def _parse_or_raise(org_id: int, file_bytes: bytes) -> rasd.ParseResult:
    aliases, defaults = _load_column_config(org_id)
    try:
        return rasd.parse(file_bytes, aliases, defaults)
    except ValueError as exc:
        raise PasteError(str(exc)) from exc


# ═══ الخطّة — مصدرٌ واحد للمعاينة والتنفيذ ═══
#
# `preview` و`commit` كانا يحسبان الشيء نفسه بمسارَي كودٍ مختلفَين، فكان
# انحرافُهما مسألةَ وقت: معاينةٌ تقول شيئًا وتنفيذٌ يفعل غيره. الآن يبنيان
# **نفس الخطّة** بنفس الدالّة — فالمعاينة حرفيًّا «ما سيفعله التنفيذ»، وهذا
# شرطُ «دقّة أخذ البيانات من راصد» (الأولوية العليا، و-٢٠).


@dataclass(frozen=True)
class CategoryPlan:
    """ما سيحدث لفئة واحدة من صفٍّ واحد."""

    key: str  # 'hifz' | 'thabat' | 'muraja3a' | 'attendance'
    activity_type: str
    kind: str  # 'quran' | 'attendance'
    #: 'created' | 'already_imported' | 'skipped_zero' | 'no_ruleset' | 'no_weight'
    status: str
    quantity: Decimal  # نقطة مئوية للفئات الثلاث، وعددُ أيامٍ للحضور
    hours: Decimal | None  # `None` حين لا يمكن الاحتساب أصلًا
    external_ref: str


@dataclass(frozen=True)
class RowPlan:
    """ما سيحدث لصفّ طالبٍ واحد — بكل فئاته."""

    name: str
    match_status: str  # نتيجة `match_names` الخام
    status: str  # 'resolved' | 'unmatched' | 'ambiguous' | 'no_active_team'
    user_id: int | None
    team_id: int | None
    candidate_ids: list[int]
    percentages: dict[str, Decimal]
    attendance: Decimal
    tasmi3_days: Decimal
    categories: tuple[CategoryPlan, ...]
    overrides: tuple[dict, ...]


def _category_plan(
    org_id: int,
    *,
    key: str,
    activity_type: str,
    kind: str,
    quantity: Decimal,
    team_id: int,
    user_id: int,
    occurred_on: date,
    occurred_at: datetime,
    ruleset: RuleSet | None,
) -> CategoryPlan:
    """
    ترتيب الفحوص مقصود: **التكرار قبل الاحتساب**. صفٌّ سبق استيرادُه لا
    يُحتسب أصلًا، فلا معنى لسؤال الأوزان عنه.
    """
    ext_ref = _external_ref(team_id, occurred_on, user_id, activity_type)
    common = {
        "key": key,
        "activity_type": activity_type,
        "kind": kind,
        "quantity": quantity,
        "external_ref": ext_ref,
    }

    if _already_imported(org_id, ext_ref):
        return CategoryPlan(status="already_imported", hours=None, **common)
    if ruleset is None:
        return CategoryPlan(status="no_ruleset", hours=None, **common)
    try:
        hours = ruleset.hours_for(
            Achievement(
                user_id=user_id,
                occurred_at=occurred_at,
                activity_type=activity_type,
                quantity=quantity,
            )
        )
    except ValueError:
        # نشاطٌ بلا وزن في الإصدار السارّي — حالةٌ معروضة لا استثناءٌ بـ٥٠٠.
        # الترتيب في `rules_admin` يمنع إسقاط نشاطٍ قائم، فيبقى هذا لأوّل
        # إصدارٍ في منظّمة جديدة أُنشئ ناقصًا.
        return CategoryPlan(status="no_weight", hours=None, **common)

    if hours == 0:
        # لا حدث لصفرٍ حقيقيّ — نفس مبدأ `services/entry.record`: غيابٌ لا
        # يُنشئ حدثًا أصلًا، لا حدثًا بصفر ساعة (`docs/slices/و-٥.md`).
        return CategoryPlan(status="skipped_zero", hours=hours, **common)
    return CategoryPlan(status="created", hours=hours, **common)


def _resolved_quantity(
    name: str, field: str, original: Decimal, overrides: dict[str, Decimal]
) -> tuple[Decimal, dict | None]:
    """
    القيمة بعد تفويض المشرف، ومعها سطرُ تدقيقٍ حين تغيّرت فعلًا.

    دالّةٌ على مستوى الوحدة لا إغلاقٌ داخل الحلقة: الإغلاق يربط متغيّر الحلقة
    فيصير صحيحًا بالمصادفة (استُدعي في دورته) لا بالبناء.
    """
    value = overrides.get(field, original)
    if value == original:
        return original, None
    return value, {
        "name": name,
        "field": field,
        "original": str(original),
        "override": str(value),
    }


def _plan_rows(
    org: Org,
    rows: list[dict],
    matches: dict,
    occurred_on: date,
    occurred_at: datetime,
    ruleset: RuleSet | None,
    name_resolutions: dict[str, int],
    value_overrides: dict[str, dict[str, Decimal]],
) -> list[RowPlan]:
    """
    الصفوف المطبَّعة ⇒ خطّة لكل صفّ. **بلا كتابة إطلاقًا** — قراءاتٌ فقط،
    فتصلح للمعاينة كما تصلح للتنفيذ.
    """
    # user_id النهائي: تفويض المشرف أوّلًا (يغلب المطابقة التلقائية عمدًا —
    # يسمح بتصحيح مطابقة آلية خاطئة)، ثم نتيجة `match_names`.
    resolved: dict[str, int] = {}
    for row in rows:
        name = row["name"]
        if name in name_resolutions:
            resolved[name] = name_resolutions[name]
        elif matches[name].status == "matched":
            resolved[name] = matches[name].user_id

    team_by_user = dict(
        db.session.execute(
            select(Membership.user_id, Membership.team_id).where(
                Membership.user_id.in_(list(resolved.values()) or [-1]),
                Membership.left_at.is_(None),
            )
        ).all()
    )

    plans = []
    for row in rows:
        name = row["name"]
        match = matches[name]
        percentages = _row_percentages(row)
        shared = {
            "name": name,
            "match_status": match.status,
            "candidate_ids": match.candidate_ids,
            "percentages": percentages,
            "attendance": row["attendance"],
            "tasmi3_days": row["tasmi3_days"],
        }

        user_id = resolved.get(name)
        if user_id is None:
            plans.append(
                RowPlan(
                    status=match.status,
                    user_id=None,
                    team_id=None,
                    categories=(),
                    overrides=(),
                    **shared,
                )
            )
            continue

        team_id = team_by_user.get(user_id)
        if team_id is None:
            plans.append(
                RowPlan(
                    status="no_active_team",
                    user_id=user_id,
                    team_id=None,
                    categories=(),
                    overrides=(),
                    **shared,
                )
            )
            continue

        overrides = value_overrides.get(name, {})
        applied: list[dict] = []
        categories: list[CategoryPlan] = []

        for cat in PERCENT_CATEGORIES:
            achieved, note = _resolved_quantity(
                name, f"{cat}_achieved", row[f"{cat}_achieved"], overrides
            )
            if note is not None:
                applied.append(note)
            categories.append(
                _category_plan(
                    org.id,
                    key=cat,
                    activity_type=QURAN_ACTIVITY[cat],
                    kind="quran",
                    quantity=_percent(row[f"{cat}_target"], achieved),
                    team_id=team_id,
                    user_id=user_id,
                    occurred_on=occurred_on,
                    occurred_at=occurred_at,
                    ruleset=ruleset,
                )
            )

        attendance, note = _resolved_quantity(
            name, ATTENDANCE_ACTIVITY, row["attendance"], overrides
        )
        if note is not None:
            applied.append(note)

        categories.append(
            _category_plan(
                org.id,
                key=ATTENDANCE_ACTIVITY,
                activity_type=ATTENDANCE_ACTIVITY,
                kind="attendance",
                quantity=attendance,
                team_id=team_id,
                user_id=user_id,
                occurred_on=occurred_on,
                occurred_at=occurred_at,
                ruleset=ruleset,
            )
        )

        plans.append(
            RowPlan(
                status="resolved",
                user_id=user_id,
                team_id=team_id,
                categories=tuple(categories),
                overrides=tuple(applied),
                **shared,
            )
        )

    return plans


def _category_report(plan: CategoryPlan) -> dict:
    """شكل الردّ لفئة واحدة — `hours` يحضر فقط حين يكون للاحتساب معنى."""
    if plan.hours is None:
        return {"status": plan.status}
    return {"status": plan.status, "hours": str(plan.hours)}


def _totals(plans: list[RowPlan]) -> dict:
    """
    ما سيُكتب فعلًا، معدودًا قبل الكتابة — «لا `commit` بلا معاينة مقروءة».
    """
    created = [c for p in plans for c in p.categories if c.status == "created"]
    hours = sum((c.hours for c in created), Decimal("0"))
    return {
        "rows": len(plans),
        "rows_resolved": sum(1 for p in plans if p.status == "resolved"),
        "rows_needing_attention": sum(1 for p in plans if p.status != "resolved"),
        "events_new": len(created),
        "events_already_imported": sum(
            1 for p in plans for c in p.categories if c.status == "already_imported"
        ),
        "events_skipped_zero": sum(
            1 for p in plans for c in p.categories if c.status == "skipped_zero"
        ),
        "hours_total": hours.quantize(Decimal("0.01")),
    }


def _ruleset_or_none(org_id: int, occurred_at: datetime) -> RuleSet | None:
    """
    للمعاينة: غيابُ نسخة أوزان **لا يمنع النظر في الملفّ**، بل يُعرض تحذيرًا
    ويُترك الاحتساب فارغًا. (التنفيذ يرفض صراحةً — `commit` أدناه.)
    """
    try:
        return ruleset_at(org_id, occurred_at)
    except ValueError:
        return None


def preview(org: Org, file_bytes: bytes, occurred_on: date) -> dict:
    """
    FR-031 — **بلا كتابة إطلاقًا** (ق-١٩٢): لا `raw_rows`، لا حدث، لا `commit`.

    الحالات معروضة **بالمطابقة التلقائية وحدها**؛ تفويضات المشرف تُطبَّق في
    `commit`، فما يُعرض هنا هو الأسوأ حالًا لا الأفضل.
    """
    if occurred_on > _local_today(org):
        raise PasteError("لا يمكن استيراد بيانات بتاريخ لم يأتِ بعد.")

    parsed = _parse_or_raise(org.id, file_bytes)
    rows = parsed.rows
    matches = match_names(org.id, [r["name"] for r in rows])
    batch_id = _batch_id(org.id, occurred_on, rows)
    occurred_at = _occurred_at_for(org, occurred_on)
    ruleset = _ruleset_or_none(org.id, occurred_at)

    dup_row = db.session.execute(
        select(RawRow.imported_at, RawRow.imported_by)
        .where(RawRow.org_id == org.id, RawRow.batch_id == batch_id)
        .limit(1)
    ).first()

    plans = _plan_rows(org, rows, matches, occurred_on, occurred_at, ruleset, {}, {})

    preview_rows = [
        {
            "name": p.name,
            "match_status": p.match_status,
            "status": p.status,
            "user_id": p.user_id,
            "candidate_ids": p.candidate_ids,
            "percentages": {
                cat: str(v.quantize(DISPLAY_PRECISION)) for cat, v in p.percentages.items()
            },
            "attendance": str(p.attendance),
            "tasmi3_days": str(p.tasmi3_days),
            "categories": {c.key: _category_report(c) for c in p.categories},
        }
        for p in plans
    ]

    return {
        "batch_id": batch_id,
        "duplicate_warning": dup_row is not None,
        "duplicate_imported_at": dup_row[0].isoformat() if dup_row else None,
        # الاستبعاد مُعلَن لا صامت: صفّا «الإجمالي» و«المتوسط» في ملفّ راصد
        # بشكل صفّ طالبٍ تمامًا، فاختفاؤهما بلا ذكرٍ يُقرَأ كفقدان طالبَين.
        "excluded_labels": parsed.excluded_labels,
        "weights_missing": ruleset is None,
        "totals": _totals(plans),
        "rows": preview_rows,
    }


def commit(
    org: Org,
    actor_id: int,
    file_bytes: bytes,
    occurred_on: date,
    name_resolutions: dict[str, int] | None = None,
    value_overrides: dict[str, dict[str, Decimal]] | None = None,
) -> dict:
    """
    FR-033/034 — الخام يُكتب أوّلًا لكل صفّ طالب حقيقيّ، ثم فحص تكرار **لكل
    (تاريخ، طالب، نشاط)** يستبعد ما سبق استيراده، ثم إلحاق الجديد فقط.

    ذرّيّة مع `audit_log`: `ledger.append_pending` (`flush` لا `commit`) ثم
    `audit.record` ثم `commit` واحد — فشلٌ في أيّهما لا يترك حدثًا يتيمًا
    (نمط `services/reading.admin_submit`، و-١١).
    """
    if occurred_on > _local_today(org):
        raise PasteError("لا يمكن استيراد بيانات بتاريخ لم يأتِ بعد.")

    parsed = _parse_or_raise(org.id, file_bytes)
    rows = parsed.rows
    matches = match_names(org.id, [r["name"] for r in rows])
    batch_id = _batch_id(org.id, occurred_on, rows)
    occurred_at = _occurred_at_for(org, occurred_on)

    try:
        ruleset = ruleset_at(org.id, occurred_at)
    except ValueError as exc:
        raise PasteError(str(exc)) from exc

    # ١) الخام يُكتب أوّلًا لكل صفّ طالب حقيقيّ — دائمًا، بصرف النظر عن نتيجة
    # المطابقة لاحقًا (FR-033). صفوف التذييل مُستبعَدة فعلًا من `rasd.parse`.
    db.session.add_all(
        RawRow(
            org_id=org.id,
            batch_id=batch_id,
            source=SOURCE,
            payload=row["raw"],
            imported_by=actor_id,
        )
        for row in rows
    )

    # ٢) نفس الخطّة التي تراها المعاينة — ثم تُنفَّذ.
    plans = _plan_rows(
        org,
        rows,
        matches,
        occurred_on,
        occurred_at,
        ruleset,
        name_resolutions or {},
        value_overrides or {},
    )

    specs = []
    row_reports = []
    overrides_applied = []
    for plan in plans:
        overrides_applied.extend(plan.overrides)
        if plan.status != "resolved":
            row_reports.append({"name": plan.name, "status": plan.status, "user_id": plan.user_id})
            continue

        for cat in plan.categories:
            if cat.status != "created":
                continue
            specs.append(
                ledger.EventSpec(
                    org_id=org.id,
                    kind=cat.kind,
                    delta=cat.hours,
                    user_id=plan.user_id,
                    occurred_at=occurred_at,
                    actor_id=actor_id,
                    external_ref=cat.external_ref,
                )
            )

        row_reports.append(
            {
                "name": plan.name,
                "status": "resolved",
                "user_id": plan.user_id,
                "categories": {c.key: _category_report(c) for c in plan.categories},
            }
        )

    events = ledger.append_pending(specs) if specs else []

    audit.record(
        org_id=org.id,
        kind="rasd_import",
        summary=(
            f"استيراد راصد بتاريخ {occurred_on.isoformat()}: "
            f"{len(events)} حدثًا جديدًا من {len(rows)} صفًّا"
        ),
        actor_id=actor_id,
        after={
            "batch_id": batch_id,
            "events_created": len(events),
            "rows": len(rows),
            "overrides": overrides_applied,
        },
    )
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise PasteError(
            "تصادمٌ في الاستيراد — أُعيدت المحاولة، حدِّث المعاينة وحاول مجدَّدًا.", status=409
        ) from exc

    return {"batch_id": batch_id, "rows": row_reports, "events_created": len(events)}


# ═══ عرض الحضور من راصد — و-٢٠ ═══


def latest_import_view(org: Org) -> dict:
    """
    آخر استيراد راصد: تاريخه وصفوف حضوره — **للعرض فقط**.

    النموذج المعتمد يجعل شاشة الحضور «للعرض فقط — تصل من استيراد راصد، لا
    تُعدَّل هنا». والبيانات موجودة أصلًا منذ و-٥ في `raw_rows`؛ الناقص كان
    قراءتَها.

    **وتُقرأ بنفس إعدادات أعمدة الاستيراد** (`entry_defaults`) لا بأسماء
    مكتوبة هنا: ملفٌّ بترويسة مرادفة يُستورَد بنجاح ثم لا يُقرأ في هذه الشاشة
    — تباعدٌ صامت بين مسارَي قراءةٍ لنفس الملفّ.

    **والحضور عددٌ لا حاضر/غائب:** هكذا يصل من راصد فعلًا (`٢`/`١`/`٠` من
    أيام التسميع)، والنموذج يعرض حاصرتين لأن بياناته تجريبية.
    """
    latest = db.session.execute(
        select(RawRow.batch_id, RawRow.imported_at)
        .where(RawRow.org_id == org.id, RawRow.source == SOURCE)
        .order_by(RawRow.imported_at.desc(), RawRow.id.desc())
        .limit(1)
    ).first()
    if latest is None:
        return {"imported_at": None, "rows": []}

    batch_id, imported_at = latest
    payloads = db.session.scalars(
        select(RawRow.payload)
        .where(RawRow.org_id == org.id, RawRow.batch_id == batch_id)
        .order_by(RawRow.id)
    ).all()

    aliases, _defaults = _load_column_config(org.id)

    def column_for(canonical: str) -> set[str]:
        return {canonical, *aliases.get(canonical, [])}

    name_cols = column_for(rasd.STUDENT_COLUMN)
    attendance_cols = column_for("الحضور")
    days_cols = column_for("أيام التسميع")

    def pick(payload: dict, wanted: set[str]) -> str:
        for key, value in payload.items():
            if key in wanted:
                return (value or "").strip()
        return ""

    names = [pick(p, name_cols) for p in payloads]
    matches = match_names(org.id, names)
    team_names = dict(
        db.session.execute(
            select(Membership.user_id, Team.name)
            .join(Team, Team.id == Membership.team_id)
            .where(Membership.org_id == org.id, Membership.left_at.is_(None))
        ).all()
    )

    rows = []
    for payload, name in zip(payloads, names, strict=True):
        match = matches.get(name)
        user_id = match.user_id if match and match.status == "matched" else None
        rows.append(
            {
                "name": name,
                "team_name": team_names.get(user_id) if user_id else None,
                "attendance": pick(payload, attendance_cols),
                "tasmi3_days": pick(payload, days_cols),
                "matched": user_id is not None,
            }
        )

    return {"imported_at": imported_at.isoformat(), "rows": rows}
