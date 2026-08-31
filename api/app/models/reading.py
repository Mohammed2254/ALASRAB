from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class ReadingSubmission(db.Model):
    """
    طلبات القراءة قبل اعتمادها.

    **لماذا جدول منفصل لا حالة في `point_events`؟** لأن سجلّ الأحداث **سجلّ
    حقائق**: كل صفّ فيه أثّر في رصيد. صفٌّ يقول «ربما» يعني أن كل استعلام رصيد
    في المشروع يجب أن يتذكّر استبعاده — و**أوّل استعلام ينساه يعطي أرقامًا خاطئة
    بصمت**. الفصل يجعل النسيان مستحيلًا (`DATABASE.md` §٣.١).

    والطلب يصير حدثًا **لحظة الاعتماد وحدها**، وبتاريخ القراءة لا تاريخ الاعتماد
    (FR-023 · `RULES.md` §٩).
    """

    __tablename__ = "reading_submissions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','approved','rejected')",
            name="reading_status_valid",
        ),
        CheckConstraint("pages > 0", name="reading_pages_positive"),
        # ═══════════════════════════════════════════════════════════════
        # ث-٥ — طلبٌ معتمد له حدث، وحدثٌ لا يكون إلا لمعتمد.
        #
        # يمنع الخطأين معًا: اعتمادٌ بلا ساعات (فيشتكي الطالب ولا يجد أثرًا)،
        # وساعاتٌ بلا اعتماد (فتُمنح بلا مراجعة). الحارس في القاعدة لا الخدمة
        # لأن الخدمة تُنسى ويُلتفّ عليها بسكربت إداري (ADR-002).
        # ═══════════════════════════════════════════════════════════════
        CheckConstraint(
            "(status = 'approved' AND point_event_id IS NOT NULL)"
            " OR (status <> 'approved' AND point_event_id IS NULL)",
            name="reading_approved_has_event",
        ),
        # ث-٦ — الرفض يوجب سببًا. رفضٌ صامت يقتل الثقة أسرع من غياب الميزة،
        # والطالب يرى السبب (FR-024).
        CheckConstraint(
            "status <> 'rejected' OR review_reason IS NOT NULL",
            name="reading_rejected_has_reason",
        ),
        # FR-020 — إرسال مزدوج بنقرتين. القيد في القاعدة لا في الواجهة:
        # التحقّق على الحدّ هو التحقّق الوحيد الموثوق.
        UniqueConstraint("user_id", "read_on", "book_title", name="uq_reading_per_day"),
        # طابور المشرف: الأقدم أوّلًا، والمعلَّق وحده (م-٢).
        Index(
            "ix_reading_pending",
            "org_id",
            "created_at",
            postgresql_where=db.text("status = 'pending'"),
        ),
        # قائمة الطالب: طلباته الأحدث أوّلًا (FR-024).
        Index("ix_reading_user", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # تاريخ لا طابع زمني: الطالب يختار يومًا في تقويمه. التحويل إلى لحظة يقع
    # عند الاعتماد وحده، بقاعدة `RULES.md` §٩.
    read_on: Mapped[date] = mapped_column(Date, nullable=False)
    pages: Mapped[int] = mapped_column(Integer, nullable=False)
    book_title: Mapped[str] = mapped_column(String, nullable=False)

    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # الرابط الوحيد بالسجلّ. يُملأ لحظة الاعتماد ولا يُفرَّغ بعدها (ث-٥).
    point_event_id: Mapped[int | None] = mapped_column(ForeignKey("point_events.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
