"""
سجلّ التدقيق: المالك الوحيد للكتابة في `audit_log`.

**نفس مبدأ `ledger`:** ثلاثة كتّاب قادمون — إعادة تعيين PIN (FR-004)، والتصحيح
القرآني (FR-037)، وتغيير الأوزان (و-٧). وثلاث نسخ من «الكتابة الصحيحة» تعني أن
الثالثة ستنسى شيئًا: الفاعل، أو الملخّص المقروء، أو ألّا تتسرّب قيمة سرّية.

**والفاعل هو المشرف لا الطالب.** سجلٌّ ينسب الفعل لضحيّته يقلب معنى التدقيق —
وهو التعويض الوحيد عن دمج الدورين (`SCOPE.md` §٣.٣).
"""

from typing import Any

from ..extensions import db
from ..models import AuditEntry


def record(
    org_id: int,
    kind: str,
    summary: str,
    actor_id: int,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditEntry:
    """
    سطرٌ واحد. **لا `commit` هنا:** الكتابة أثرٌ جانبيّ لفعلٍ آخر، وإتمامها
    منفردةً يعني سطر تدقيق لفعلٍ ربما فشل بعده.

    والمستدعي يُتمّ المعاملة — فيصير التدقيق والفعل **ذرّيَّين معًا**.
    """
    entry = AuditEntry(
        org_id=org_id,
        kind=kind,
        summary=summary,
        actor_id=actor_id,
        before=before,
        after=after,
    )
    db.session.add(entry)
    return entry
