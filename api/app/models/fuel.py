from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class FuelActivity(db.Model):
    """نشاط جماعي يُقيَّم ببنود موزونة. لا تعديل بعد الإنشاء — إنشاءٌ جديد فقط."""

    __tablename__ = "fuel_activities"
    __table_args__ = (
        UniqueConstraint("org_id", "key", name="uq_fuel_activity_key"),
        CheckConstraint("litres_full > 0", name="fuel_activities_litres_full_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    key: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    litres_full: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FuelCriterion(db.Model):
    """
    بند تقييم داخل نشاط. **مجموع `weight_pct` لكل بنود نشاط واحد = ١٠٠٪ بالضبط**
    (ث-١٠أ) — مفروضٌ في `services/fuel.py` وبمشغّل `fuel_criteria_sum_100`.
    """

    __tablename__ = "fuel_criteria"
    __table_args__ = (
        UniqueConstraint("activity_id", "key", name="uq_fuel_criterion_key"),
        CheckConstraint("weight_pct > 0 AND weight_pct <= 100", name="fuel_criteria_weight_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("fuel_activities.id"), nullable=False)
    key: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    weight_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)


class FuelWeek(db.Model):
    """
    أسبوع وقودٍ واحد — **مسوّدةٌ حتى يُعتمد**، والاعتماد وحده يكتب في الدفتر.

    وُجد لأن التقييم قد يتأخّر: المشرف يرجع إلى أسبوعٍ مضى ويقيّمه **بتاريخه
    هو** لا بتاريخ اليوم (قرار المستخدم، و-٢٠)، فلا يُزحزح ترتيبٌ ماضٍ بلا
    سبب. و`approved_at` هو الفارق المرئيّ بين «مسوّدة» و«مُعتمَد».
    """

    __tablename__ = "fuel_weeks"
    __table_args__ = (UniqueConstraint("org_id", "week_start", name="uq_fuel_week"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FuelWeekTask(db.Model):
    """
    مهمّة أسبوعٍ واحد — نشاطٌ من القائمة الافتراضية أو مضافٌ لهذا الأسبوع.

    القائمة الافتراضية (`fuel_activities`) تُنسَخ مهامَّ عند فتح الأسبوع، ثم
    **يُضيف المشرف ويُزيل لذلك الأسبوع وحده** (قرار المستخدم) — فإزالةُ مهمّة
    لا تمسّ أسبوعًا آخر ولا الأرشيف.

    **و`team_id` بلا قيد تفرّد على (أسبوع، سرب) عمدًا:** «لكل سرب مهمّة واحدة»
    في النموذج **إرشادٌ لا قيد** (قرار المستخدم) — فالمشرف حرّ، والنصّ توجيهٌ
    في الواجهة لا منعٌ في القاعدة.
    """

    __tablename__ = "fuel_week_tasks"
    __table_args__ = (UniqueConstraint("week_id", "activity_id", name="uq_fuel_week_task"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    week_id: Mapped[int] = mapped_column(ForeignKey("fuel_weeks.id"), nullable=False)
    activity_id: Mapped[int] = mapped_column(ForeignKey("fuel_activities.id"), nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)


class FuelWeekScore(db.Model):
    """
    درجةُ بندٍ **مسوّدة** — قبل الاعتماد، فلا حدث دفتر لها بعد.

    وُجدت لتبقى ق-٦٧ صحيحة: لو حُفظت المسوّدة في `fuel_assessments` لَلَزِم أن
    يقبل `point_event_id` العدم، وذاك نقضٌ للقيد الذي وُجد لمنع «تقييمٍ يبدو
    مكتملًا وهو فارغ». فالمسوّدة هنا، والاعتماد ينسخها إلى
    `fuel_assessments`/`fuel_scores` **مع حدثها** في معاملةٍ واحدة.
    """

    __tablename__ = "fuel_week_scores"
    __table_args__ = (
        UniqueConstraint("task_id", "criterion_id", name="uq_fuel_week_score"),
        CheckConstraint("score_pct >= 0 AND score_pct <= 100", name="fuel_week_scores_score_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("fuel_week_tasks.id"), nullable=False)
    criterion_id: Mapped[int] = mapped_column(ForeignKey("fuel_criteria.id"), nullable=False)
    score_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)


class FuelAssessment(db.Model):
    """
    تقييم نشاطٍ لسربٍ في تاريخ وقوعه. **`point_event_id` لا يقبل العدم** — لا
    حالة معلَّقة للتقييم (خلافًا للقراءة)، فهو دومًا مُلحَق بحدث منذ إنشائه.

    **وق-٦٧ بقي كما هو في و-٢٠ رغم المسوّدة الأسبوعية.** النموذج يوجب مسوّدةً
    يعقبها اعتماد، وكان أقصرُ طريقٍ إليها جعلَ هذا العمود يقبل العدم — أي نقضَ
    ق-٦٧ حرفيًّا («تقييمٌ بلا حدث محتسَب يبدو مكتملًا وهو فارغ»)، وهو بعينه
    الخطر الذي وُجد القيدُ لأجله. فبقيت المسوّدة في جدولها
    (`fuel_week_scores`)، و**وجودُ صفٍّ هنا يعني دائمًا: اعتُمد ودخل الدفتر**.
    """

    __tablename__ = "fuel_assessments"
    __table_args__ = (
        UniqueConstraint(
            "team_id", "activity_id", "occurred_on", name="uq_fuel_assessment_per_day"
        ),
        UniqueConstraint("week_task_id", name="uq_fuel_assessment_per_week_task"),
        CheckConstraint("total_pct >= 0", name="fuel_assessment_total_pct_non_negative"),
        CheckConstraint("litres >= 0", name="fuel_assessment_litres_non_negative"),
        Index("ix_fuel_assessment_team_time", "org_id", "team_id", "occurred_on"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    activity_id: Mapped[int] = mapped_column(ForeignKey("fuel_activities.id"), nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    total_pct: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    litres: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # مهمّة الأسبوع التي اعتُمدت فأنتجت هذا التقييم — العدم للصفوف السابقة
    # لنموذج الأسبوع (و-٨) فتبقى مقروءةً كما هي. والتفرّد يمنع اعتماد المهمّة
    # مرّتين.
    week_task_id: Mapped[int | None] = mapped_column(
        ForeignKey("fuel_week_tasks.id"), nullable=True
    )

    # لا external_ref وحده: هذا العمود يثبت وجود الحدث فعلًا لا يمنع تكراره فقط.
    point_event_id: Mapped[int] = mapped_column(ForeignKey("point_events.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FuelScore(db.Model):
    """
    درجة بند واحد داخل تقييم — **مفصّلة عمدًا** ليُشرح الرقم بعد شهر
    («٨٠ × ٣٥٪ = ٢٨.٠٠»، FR-071).
    """

    __tablename__ = "fuel_scores"
    __table_args__ = (
        UniqueConstraint("assessment_id", "criterion_id", name="uq_fuel_score_per_criterion"),
        CheckConstraint("score_pct >= 0 AND score_pct <= 100", name="fuel_scores_score_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("fuel_assessments.id"), nullable=False)
    criterion_id: Mapped[int] = mapped_column(ForeignKey("fuel_criteria.id"), nullable=False)
    score_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
