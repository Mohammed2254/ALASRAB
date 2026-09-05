from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class PointEvent(db.Model):
    """
    سجلّ الأحداث. الرصيد = SUM(delta)، ولا عمود رصيد في أي مكان (ADR-001).

    ما نكسبه: تدقيق كامل (مَن منح؟ متى؟ لماذا؟) · تراجع بحدث معاكس بدل تعديل رقم
    فيضيع التاريخ · «الأكثر تحسّنًا هذا الأسبوع» بفلترة تاريخ بلا حقل إضافي ·
    صحّة تحت التزامن بلا أقفال.

    **لا يُنشأ صفٌّ هنا إلا عبر `services/ledger.py`** (AGENTS ٨). سبعة مسارات
    تُلحق أحداثًا، وسبع نسخ من مسؤولية «الإلحاق الصحيح» تعني أن السابعة ستنساها.
    """

    __tablename__ = "point_events"
    __table_args__ = (
        # ═══════════════════════════════════════════════════════════════
        # ث-١ — القيد الذي يحمل القاعدة المركزية للمنتج كلها:
        #   الساعات فردية · الوقود جماعي · ولا يلتقيان.
        #
        # نحرسها هنا لا في كود التطبيق لأن الكود يُنسى ويُلتفّ عليه بسكربت إداري
        # عاجل يوم ضغط، أو بمسار جديد يكتبه أحدهم بعد ستة أشهر ولم يقرأ الوثيقة.
        # القيد لا. مخالفة القاعدة تصير مستحيلة فيزيائيًّا لا ممنوعة أدبيًّا.
        # ═══════════════════════════════════════════════════════════════
        CheckConstraint(
            "(scope = 'individual' AND user_id IS NOT NULL AND team_id IS NULL"
            " AND currency = 'hours')"
            " OR "
            "(scope = 'team' AND team_id IS NOT NULL AND user_id IS NULL"
            " AND currency = 'fuel')",
            name="currency_scope_match",
        ),
        CheckConstraint("scope IN ('individual','team')", name="scope_valid"),
        CheckConstraint("currency IN ('hours','fuel')", name="currency_valid"),
        # ث-٧ — التصحيح أو الإدخال اليدوي بلا سبب يبدو تلاعبًا في بطاقة الطالب.
        # وُسِّع في و-٦ ليشمل 'manual' (FR-036 "بسبب إلزامي") — كان يغطّي
        # 'correction' وحده منذ و-١.
        CheckConstraint(
            "kind NOT IN ('correction', 'manual') OR reason IS NOT NULL",
            name="correction_or_manual_needs_reason",
        ),
        # ث-٣ — الـidempotency: إعادة استيراد نفس الأسبوع لا تمنح النقاط مرتين.
        # هذا تحديدًا ما يكسر أنظمة كهذه: أحدهم يعيد الرفع، تتضاعف النقاط، ويفقد
        # الطلاب الثقة في يوم واحد.
        Index(
            "uq_event_external_ref",
            "org_id",
            "external_ref",
            unique=True,
            postgresql_where=db.text("external_ref IS NOT NULL"),
        ),
        # رصيد الطالب وسجلّه والصدارة الفردية.
        Index(
            "ix_event_user_time",
            "org_id",
            "user_id",
            "occurred_at",
            postgresql_where=db.text("scope = 'individual'"),
        ),
        # وقود السرب ومحطة التزوّد.
        Index(
            "ix_event_team_time",
            "org_id",
            "team_id",
            "occurred_at",
            postgresql_where=db.text("scope = 'team'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), nullable=False)

    scope: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=False)

    # ليس INTEGER: وزن المراجعة 0.25، وخطأ float يتراكم عبر آلاف الصفوف حتى يظهر
    # في الترتيب — وترتيبٌ خاطئ في منصة تنافس يفقد الثقة كلها.
    delta: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)

    # 'quran' | 'reading' | 'attendance' | 'daily_question' | 'correction' | 'manual' | 'fuel'
    kind: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    external_ref: Mapped[str | None] = mapped_column(String, nullable=True)

    # occurred_at (متى وقع) ≠ created_at (متى سُجّل). الفرق هو ما يسمح بالتسجيل
    # المتأخّر، **وباختيار إصدار الأوزان الساري وقتها** (ث-١١).
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
