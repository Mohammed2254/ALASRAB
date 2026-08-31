from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class AuditEntry(db.Model):
    """
    سجلّ التدقيق — **التعويض عن دمج الدورين** (`SCOPE.md` §٣.٣).

    من يُدخل الدرجات هو نفسه من يضبط قواعد احتسابها، فالحماية تنتقل من *منع
    الصلاحية* إلى **كشف الاستعمال**. وقيمته **مشروطة بكونه مرئيًّا فعلًا** لكل
    المشرفين (FR-084) — سجلٌّ مدفون لا يحمي من شيء.

    **ثلاثة كتّاب بأشكال مختلفة**، والمخطط يستوعبهم بلا عمود إضافي:

    | الكاتب | `kind` | `before`/`after` |
    |---|---|---|
    | FR-004 إعادة تعيين PIN | `pin_reset` | **فارغان** — «بلا قيمة الـPIN» (§٧.٥) |
    | FR-037 تصحيح قرآني | `quran_correction` | مرجع الحدث |
    | تغيير الأوزان (و-٧) | `weights_version` | الإصدار قبل وبعد |

    **و`kind` نصّ مفتوح — صفوف لا كود**، كما `activity_type` في ADR-005.
    ورُفض `target_user_id` رغم ملاءمته لإعادة التعيين: يضيق عن تغيير الأوزان
    الذي لا هدف مفردًا له، ومكانه `after`.
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        # سطرٌ بلا نوع لا يُقرأ ولا يُفلتر — وسجلٌّ لا يُقرأ ليس تدقيقًا.
        CheckConstraint("length(trim(kind)) > 0", name="audit_kind_not_blank"),
        # وبلا ملخّص يصير السطر JSONB خامًّا يفكّه المشرف بعينه.
        CheckConstraint("length(trim(summary)) > 0", name="audit_summary_not_blank"),
        # مسار «صفحة سجلّ التغييرات» (FR-084): الأحدث أوّلًا داخل المنظمة.
        Index("ix_audit_org_time", "org_id", "at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), nullable=False)

    kind: Mapped[str] = mapped_column(String, nullable=False)
    # ما يقرؤه المشرف مباشرةً — فلا تحتاج الشاشة فكّ JSONB لعرض سطر.
    summary: Mapped[str] = mapped_column(String, nullable=False)

    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # **الفاعل لا الهدف.** سجلٌّ ينسب الفعل لضحيّته يقلب معنى التدقيق.
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
