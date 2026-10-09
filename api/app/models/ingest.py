from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class RawRow(db.Model):
    """
    الحمولة الخام كما وصلت من راصد، قبل أي اشتقاق (FR-033 · `RULES.md` §٦).

    **بلا `raw_row_id` على `point_events`** — الربط بالحدث منطقيّ عبر
    `external_ref`/`batch_id` لا عمود FK (`docs/archive/slices/و-٥.md` §٢.١أ): تجريدٌ
    لمشكلة لم تقع بعد، ونفس منطق ADR-005 في رفض طبقة لا يحتاجها كود قائم.

    **صفٌّ واحد لكل صفّ طالب حقيقيّ** — صفوف التذييل («الإجمالي»/«المتوسط»)
    مُستبعَدة قبل الوصول هنا. تُكتب **قبل** أي حدث، ودائمًا، حتى لو استُبعد
    الصفّ لاحقًا من الإلحاق لأنه سبق استيراده (FR-034) — فالخام يبقى مرجعًا
    كاملًا لإعادة الحساب المستقبلية (FR-086) بصرف النظر عمّا فعله المحرّك به.
    """

    __tablename__ = "raw_rows"
    __table_args__ = (
        # حارس تكرار الملفّ بالمجموع الاختباري (checksum، قرار #٩): استعلامٌ
        # واحد يجيب «هل استُورد هذا بالضبط من قبل؟» — batch_id مُشتقّ من محتوى
        # الدفعة نفسها لا معرّفًا عشوائيًّا، فنفس الملفّ لنفس التاريخ ⇒ نفس القيمة.
        Index("ix_raw_rows_batch", "org_id", "batch_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), nullable=False)

    batch_id: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="rasd")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    imported_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EntryDefault(db.Model):
    """
    مرادفات ترويسة الاستيراد والقيم الافتراضية — **بيانات لا كود**
    (`DATABASE.md` §٣.١ · `docs/archive/slices/و-٥.md` §٢.٢).

    صفٌّ واحد **لكلّ عمود مصدر** لا لكلّ فئة: فئة «حفظ» مثلًا تُمثَّل بصفَّين
    (`quran_hifz_target`، `quran_hifz_achieved`) لا صفٍّ واحد، لأن كلًّا منهما
    ترويسة CSV مستقلّة قد تتغيّر اسمها في تصدير راصد مستقبليّ. `activity_type`
    الحقيقيّ الذي يصل `Achievement` (`quran_hifz` بلا لاحقة) يُشتقّ في
    `services/paste.py` بإزالة `_target`/`_achieved` — اصطلاحٌ في الكود لا
    عمود إضافي، فالمخطط يبقى بالأعمدة الستّة المُعلَنة سلفًا بلا زيادة.

    **مستقبل تغيّر ترويسة راصد صفٌّ في `aliases` لا نشرًا جديدًا.**
    """

    __tablename__ = "entry_defaults"
    __table_args__ = (
        UniqueConstraint("org_id", "activity_type", name="uq_entry_default_activity"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), nullable=False)

    activity_type: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    # القيمة حين تغيب الخليّة أو العمود كلّه من الملفّ — عادة صفر (FR-040 يعمّم
    # على كل عمود لا الحضور وحده: «ترويسة بلا عمود ⇒ لا شيء يُكسر»).
    quantity: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    aliases: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
