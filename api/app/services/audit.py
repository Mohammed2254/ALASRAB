"""
سجلّ التدقيق: المالك الوحيد للكتابة في `audit_log`.

**نفس مبدأ `ledger`:** ثلاثة كتّاب قادمون — إعادة تعيين PIN (FR-004)، والتصحيح
القرآني (FR-037)، وتغيير الأوزان (و-٧). وثلاث نسخ من «الكتابة الصحيحة» تعني أن
الثالثة ستنسى شيئًا: الفاعل، أو الملخّص المقروء، أو ألّا تتسرّب قيمة سرّية.

**والفاعل هو المشرف لا الطالب.** سجلٌّ ينسب الفعل لضحيّته يقلب معنى التدقيق —
وهو التعويض الوحيد عن دمج الدورين (`SCOPE.md` §٣.٣).

@implements FR-084
"""

from typing import Any

from sqlalchemy import select

from ..extensions import db
from ..models import AuditEntry, User


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


def list_for_org(org_id: int) -> list[tuple[AuditEntry, str]]:
    """
    كل السطور — **مفتوح لكل المشرفين بلا حدّ `team_id`** (FR-084 · §٧.٣).

    الأحدث أوّلًا: التغيير الجديد هو ما يريد المشرف رؤيته أوّلًا عند فتح
    الصفحة. اسم الفاعل مُلحَق بلا N+1 — قائمة تُقرَأ لا تُفكَّك سطرًا سطرًا.
    """
    return db.session.execute(
        select(AuditEntry, User.full_name)
        .join(User, User.id == AuditEntry.actor_id)
        .where(AuditEntry.org_id == org_id)
        .order_by(AuditEntry.at.desc(), AuditEntry.id.desc())
    ).all()
