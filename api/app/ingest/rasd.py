"""
محلّل تصدير راصد — Adapter وحيد (`RULES.md` §٦، ADR-005).

**بايتات ⇒ صفوف مطبَّعة. لا DB هنا** (`entry_defaults` يُحمَّل ويُمرَّر من
`services/paste.py`، لا يُقرأ من هذا الملفّ — الفصل نفسه بين «القاعدة» و«ما
يقرأ القاعدة» المتّبع في `rules/engine.py`). لا يخمّن ولا يبتلع الخطأ: يرفع
`ValueError` برسالة عربية مفهومة على أي انحراف عن العقد المعلن.

الشكل مأخوذ حرفيًّا من عيّنتين حقيقيّتين في `api/tests/fixtures/` — ١٣
عمودًا ثابتة **العدد والترتيب**، BOM في البداية، أسطر LF.
"""

import csv
import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

STUDENT_COLUMN = "الطالب"

# الترويسة الكنسيّة بترتيبها الحرفيّ — **العدد والترتيب لا يُخمَّنان أبدًا**
# (`RULES.md` §٦). كل موضع يقبل تسميته الكنسيّة أو أيّ مرادف مسجَّل في
# `entry_defaults.aliases` لنفس الموضع (`aliases` تُمرَّر من المستدعي).
CANONICAL_HEADER = [
    STUDENT_COLUMN,
    "أيام التسميع",
    "الحضور",
    "مستهدف الحفظ",
    "منجز الحفظ",
    "نسبة الحفظ",
    "المستهدف تثبيت",
    "المنجز تثبيت",
    "نسبة التثبيت",
    "المستهدف مراجعة",
    "المنجز مراجعة",
    "نسبة المراجعة",
    "الإجمالي",
]

# صفوف تذييل حقيقيّة (كلا عيّنتَي الاختبار) بنفس شكل صفّ الطالب تمامًا —
# الاستبعاد **بالمحتوى** لا بالموضع (قد يختلف عدد الطلاب فيتزحزح الموضع).
FOOTER_LABELS = {"الإجمالي", "المتوسط"}

# عمود كنسيّ → مفتاح الصفّ المطبَّع. «نسبة X» و«الإجمالي» غائبان عمدًا —
# يصلان إلى `raw` للأرشفة فقط، ولا تُصدَّق قيمتهما أبدًا (تُحسب داخليًّا،
# قرار #١).
_FIELD_KEYS = {
    "أيام التسميع": "tasmi3_days",
    "الحضور": "attendance",
    "مستهدف الحفظ": "hifz_target",
    "منجز الحفظ": "hifz_achieved",
    "المستهدف تثبيت": "thabat_target",
    "المنجز تثبيت": "thabat_achieved",
    "المستهدف مراجعة": "muraja3a_target",
    "المنجز مراجعة": "muraja3a_achieved",
}


@dataclass(frozen=True)
class ParseResult:
    """
    صفوف الطلاب الحقيقيّين، **ومعها ما استُبعد صراحةً**.

    الاستبعاد الصامت يُقرَأ كعطل: مشرفٌ يرى ٢٤ صفًّا في ملفٍّ فيه ٢٦ سطرًا
    يحتاج أن يعرف أنّ الفارق صفّا تذييل لا طالبَين ضائعَين (و-٢٠).
    """

    rows: list[dict]
    #: تسميات صفوف التذييل المستبعَدة، بترتيب ورودها في الملفّ.
    excluded_labels: list[str]


def _to_decimal(raw: str | None, column: str, default: Decimal) -> Decimal:
    text = (raw or "").strip()
    if text == "":
        return default
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"قيمة غير رقمية في عمود «{column}»: «{raw}»") from exc


def _resolve_header(
    actual_header: list[str] | None, aliases: dict[str, list[str]]
) -> dict[str, str]:
    """
    يطابق كل موضع بترويسته الكنسيّة أو مرادفٍ مسجَّل له — **لا يُخمَّن ترتيب
    ولا عدد الأعمدة**. يُرجع: عمود فعليّ في الملفّ ⇒ عمود كنسيّ.
    """
    if actual_header is None or len(actual_header) != len(CANONICAL_HEADER):
        raise ValueError(
            "ترويسة الملفّ لا تطابق العقد المتوقَّع — " f"يُتوقَّع {len(CANONICAL_HEADER)} عمودًا بالضبط."
        )
    resolved = {}
    for position, (canonical, actual) in enumerate(
        zip(CANONICAL_HEADER, actual_header, strict=True), start=1
    ):
        accepted = {canonical, *aliases.get(canonical, [])}
        if actual not in accepted:
            raise ValueError(
                f"عمود غير متوقَّع في الموضع {position}: «{actual}» — "
                f"يُتوقَّع «{canonical}» (أو أحد مرادفاته المسجَّلة)."
            )
        resolved[actual] = canonical
    return resolved


def parse(
    file_bytes: bytes,
    aliases: dict[str, list[str]] | None = None,
    defaults: dict[str, Decimal] | None = None,
) -> ParseResult:
    """
    الملفّ كاملًا ⇒ صفوف الطلاب الحقيقيّين، ومعها تسميات ما استُبعد.

    `aliases`: عمود كنسيّ ⇒ مرادفاته المقبولة (من `entry_defaults.aliases`،
    يُحمَّلها `services/paste.py`) — ترويسة راصد مستقبليّة مغايرة الأسماء
    تُقبل بلا لمس هذا الملفّ. `defaults`: `activity_type` ⇒ القيمة حين تغيب
    الخليّة (من `entry_defaults.quantity`؛ الافتراض العامّ صفر).
    """
    aliases = aliases or {}
    defaults = defaults or {}

    try:
        text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("الملفّ ليس UTF-8 صالحًا.") from exc

    reader = csv.DictReader(io.StringIO(text))
    actual_to_canonical = _resolve_header(reader.fieldnames, aliases)
    # عمود فعليّ ⇒ مفتاح الصفّ المطبَّع (يتجاوز أعمدة النسبة/الإجمالي/الطالب).
    actual_to_key = {
        actual: _FIELD_KEYS[canonical]
        for actual, canonical in actual_to_canonical.items()
        if canonical in _FIELD_KEYS
    }
    student_actual_column = next(
        actual for actual, canonical in actual_to_canonical.items() if canonical == STUDENT_COLUMN
    )

    rows = []
    excluded_labels = []
    for raw in reader:
        name = (raw.get(student_actual_column) or "").strip()
        if name in FOOTER_LABELS:
            excluded_labels.append(name)
            continue
        if name == "":
            continue

        row = {"name": name, "raw": raw}
        for actual_column, key in actual_to_key.items():
            default = defaults.get(key, Decimal("0"))
            row[key] = _to_decimal(raw.get(actual_column), actual_column, default)
        rows.append(row)

    return ParseResult(rows=rows, excluded_labels=excluded_labels)
