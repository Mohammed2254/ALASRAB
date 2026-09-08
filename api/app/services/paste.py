"""
تنسيق استيراد راصد — FR-030..034/040 (و-٥).

**`preview` بلا كتابة إطلاقًا، و`commit` يكتب `raw_rows` دائمًا** لكل صفّ
طالب حقيقيّ، ثم يُلحق أحداثًا **للصفوف الجديدة فقط** — أيّ (تاريخ، طالب،
نشاط) له `external_ref` قائم فعلًا يُستبعَد صراحةً بدل رفض الدفعة كلّها
(`docs/slices/و-٥.md` §٢.١ب): إعادة استيراد مصحَّحة لبعض الطلاب يجب أن تبقى
ممكنة للباقين.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..ingest import rasd
from ..models import EntryDefault, Membership, Org, PointEvent, RawRow
from ..rules.engine import Achievement, ruleset_at
from . import audit, ledger
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


class PasteError(Exception):
    """خطأ عملٍ يُترجَم إلى رمز حالة في المسار — لا يعرف HTTP (نمط `ReadingError`)."""

    def __init__(self, message: str, status: int = 422):
        self.status = status
        super().__init__(message)


def _local_today(org: Org) -> date:
    return datetime.now(ZoneInfo(org.timezone)).date()


def _occurred_at_for(org: Org, occurred_on: date) -> datetime:
    """نفس تحويل `reading.occurred_at_for`، مكرَّر عمدًا لا مستوردًا (`RULES.md` §٩)."""
    return datetime.combine(occurred_on, time.min, tzinfo=ZoneInfo(org.timezone)).astimezone(UTC)


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


def _parse_or_raise(org_id: int, file_bytes: bytes) -> list[dict]:
    aliases, defaults = _load_column_config(org_id)
    try:
        return rasd.parse(file_bytes, aliases, defaults)
    except ValueError as exc:
        raise PasteError(str(exc)) from exc


@dataclass(frozen=True)
class PreviewRow:
    name: str
    match_status: str  # 'matched' | 'ambiguous' | 'unmatched'
    user_id: int | None
    candidate_ids: list[int]
    percentages: dict[str, str]
    attendance: str
    tasmi3_days: str


def preview(org: Org, file_bytes: bytes, occurred_on: date) -> dict:
    """
    FR-031 — **بلا كتابة إطلاقًا** (ق-١٩٢): لا `raw_rows`، لا حدث، لا `commit`.
    """
    if occurred_on > _local_today(org):
        raise PasteError("لا يمكن استيراد بيانات بتاريخ لم يأتِ بعد.")

    rows = _parse_or_raise(org.id, file_bytes)
    matches = match_names(org.id, [r["name"] for r in rows])
    batch_id = _batch_id(org.id, occurred_on, rows)

    dup_row = db.session.execute(
        select(RawRow.imported_at, RawRow.imported_by)
        .where(RawRow.org_id == org.id, RawRow.batch_id == batch_id)
        .limit(1)
    ).first()

    preview_rows = []
    for row in rows:
        m = matches[row["name"]]
        percentages = {
            cat: str(v.quantize(DISPLAY_PRECISION)) for cat, v in _row_percentages(row).items()
        }
        preview_rows.append(
            {
                "name": row["name"],
                "match_status": m.status,
                "user_id": m.user_id,
                "candidate_ids": m.candidate_ids,
                "percentages": percentages,
                "attendance": str(row["attendance"]),
                "tasmi3_days": str(row["tasmi3_days"]),
            }
        )

    return {
        "batch_id": batch_id,
        "duplicate_warning": dup_row is not None,
        "duplicate_imported_at": dup_row[0].isoformat() if dup_row else None,
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

    name_resolutions = name_resolutions or {}
    value_overrides = value_overrides or {}

    rows = _parse_or_raise(org.id, file_bytes)
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

    # ٢) user_id النهائي: تفويض المشرف أوّلًا (يغلب المطابقة التلقائية عمدًا —
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

    specs = []
    row_reports = []
    overrides_applied = []
    for row in rows:
        name = row["name"]
        user_id = resolved.get(name)
        if user_id is None:
            row_reports.append({"name": name, "status": matches[name].status, "user_id": None})
            continue
        team_id = team_by_user.get(user_id)
        if team_id is None:
            row_reports.append({"name": name, "status": "no_active_team", "user_id": user_id})
            continue

        overrides = value_overrides.get(name, {})
        categories: dict[str, dict] = {}

        for cat in PERCENT_CATEGORIES:
            target = row[f"{cat}_target"]
            original_achieved = row[f"{cat}_achieved"]
            achieved = overrides.get(f"{cat}_achieved", original_achieved)
            if achieved != original_achieved:
                overrides_applied.append(
                    {
                        "name": name,
                        "field": f"{cat}_achieved",
                        "original": str(original_achieved),
                        "override": str(achieved),
                    }
                )
            activity_type = QURAN_ACTIVITY[cat]
            ext_ref = _external_ref(team_id, occurred_on, user_id, activity_type)
            if _already_imported(org.id, ext_ref):
                categories[cat] = {"status": "already_imported"}
                continue
            percent = _percent(target, achieved)
            hours = ruleset.hours_for(
                Achievement(
                    user_id=user_id,
                    occurred_at=occurred_at,
                    activity_type=activity_type,
                    quantity=percent,
                )
            )
            if hours == 0:
                # لا حدث لصفرٍ حقيقيّ — نفس مبدأ `services/entry.record`: غيابٌ
                # لا يُنشئ حدثًا أصلًا، لا حدثًا بصفر ساعة (`docs/slices/و-٥.md`).
                categories[cat] = {"status": "skipped_zero", "hours": "0.00"}
                continue
            specs.append(
                ledger.EventSpec(
                    org_id=org.id,
                    kind="quran",
                    delta=hours,
                    user_id=user_id,
                    occurred_at=occurred_at,
                    actor_id=actor_id,
                    external_ref=ext_ref,
                )
            )
            categories[cat] = {"status": "created", "hours": str(hours)}

        original_attendance = row["attendance"]
        attendance_qty = overrides.get("attendance", original_attendance)
        if attendance_qty != original_attendance:
            overrides_applied.append(
                {
                    "name": name,
                    "field": "attendance",
                    "original": str(original_attendance),
                    "override": str(attendance_qty),
                }
            )
        att_ref = _external_ref(team_id, occurred_on, user_id, ATTENDANCE_ACTIVITY)
        if _already_imported(org.id, att_ref):
            categories["attendance"] = {"status": "already_imported"}
        else:
            att_hours = ruleset.hours_for(
                Achievement(
                    user_id=user_id,
                    occurred_at=occurred_at,
                    activity_type=ATTENDANCE_ACTIVITY,
                    quantity=attendance_qty,
                )
            )
            if att_hours == 0:
                # لا حدث لصفرٍ حقيقيّ — نفس مبدأ `services/entry.record`.
                categories["attendance"] = {"status": "skipped_zero", "hours": "0.00"}
            else:
                specs.append(
                    ledger.EventSpec(
                        org_id=org.id,
                        kind="attendance",
                        delta=att_hours,
                        user_id=user_id,
                        occurred_at=occurred_at,
                        actor_id=actor_id,
                        external_ref=att_ref,
                    )
                )
                categories["attendance"] = {"status": "created", "hours": str(att_hours)}

        row_reports.append(
            {"name": name, "status": "resolved", "user_id": user_id, "categories": categories}
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
