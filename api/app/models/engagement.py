from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class DailyQuestion(db.Model):
    """
    سؤال يومٌ واحد لكل منظمة — FR-060.

    **`reward_hours` عمود مباشر لا وزن في `rules/engine`** (قرار Reconcile
    و-٩ب/ج): المكافأة خاصّية *هذا السؤال بعينه* لا نشاطًا عامًّا يُعاد وزنه
    مع الزمن — والخلط بينهما ترك `seed.py` يحمل وزن `daily_question` شاذًّا
    لم يستعمله كود قطّ (`docs/slices/و-٩.md`).

    **ومسار الإنشاء الإداريّ بُني في و-٢١** (`FR-097`) — كان غائبًا وفجوةً
    معلَنة في `SCOPE.md` ط-٦، والصفوف تُدرَج «بذرة أو SQL». وأثرُ ذلك على
    خادمٍ منشور أن الجمعية الجديدة تبقى بلا سؤالٍ واحد إلى الأبد.

    **وسؤالٌ أُجيب لا يُعدَّل ولا يُحذَف** (`services/daily_question.py`):
    ث-١٧ أدناه يربط `correct` بـ`point_event_id`، فتغييرُ `correct_id` بعد
    الإجابة يجعل إجابةً صحيحةً تبدو خاطئة وقد دُفعت ساعاتُها.
    """

    __tablename__ = "daily_questions"
    __table_args__ = (UniqueConstraint("org_id", "day", name="uq_daily_questions_org_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    prompt: Mapped[str] = mapped_column(String, nullable=False)
    # [{"id": 1, "text": "..."}, ...] — لا جدول بنود منفصل: خيارات سؤال لا
    # تُستعلَم أو تُقارَن عبر صفوف، فتطبيعها تعقيدٌ بلا فائدة.
    choices: Mapped[list] = mapped_column(JSONB, nullable=False)
    correct_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # يظهر دائمًا — صحّت الإجابة أم لا (FR-060، ط-٦).
    note: Mapped[str] = mapped_column(String, nullable=False)
    reward_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)


class Answer(db.Model):
    """
    إجابة طالب على سؤال — **واحدة لكل (طالب، سؤال)** (ث-٨).

    القيد **في القاعدة لا بإخفاء الزرّ** (SCOPE.md ط-٦ الحرفي): إجابة ثانية
    تُرفض بـ`409` من قيد `UNIQUE`، لا من تعطيل عنصر واجهة يمكن تجاوزه بطلب
    مباشر.

    **ث-١٧ — `correct` و`point_event_id` لا يفترقان** (دفاعٌ مزدوج، نمط
    ث-١٣ب): الخدمة تكتب الاثنين في معاملة واحدة (`ledger.append_pending`)،
    والقيد هنا يمنع أي مسار مستقبليّ — تعديلٌ ساهٍ أو إدراج مباشر — من ترك
    إجابة صحيحة بلا حدث دفتر يدفعها، أو إجابة خاطئة بحدث لم تستحقّه.
    """

    __tablename__ = "answers"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_answers_user_question"),
        CheckConstraint(
            "(correct = false AND point_event_id IS NULL)"
            " OR (correct = true AND point_event_id IS NOT NULL)",
            name="answers_correct_matches_point_event",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(ForeignKey("daily_questions.id"), nullable=False)
    choice_id: Mapped[int] = mapped_column(Integer, nullable=False)
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # `null` ⟺ إجابة خاطئة — لا مكافأة فلا حدث (ث-١٧ أعلاه).
    point_event_id: Mapped[int | None] = mapped_column(ForeignKey("point_events.id"), nullable=True)


class Note(db.Model):
    """
    ملاحظة مجهولة — FR-061 (و-٩د).

    **الجهالة بنية الجدول لا سياسة** (ث-١٢): لا `user_id` ولا `ip` ولا أي
    عمود يعود إلى المرسِل — عمودٌ «للطوارئ» يُستعمل يومًا فينكشف طالب كتب
    شكوى، ومعه تموت القناة كلّها (`DATABASE.md`).

    **`day` لا `sent_at` بدقّة الثانية** (ط-٩ الحرفي): الثانية تكشف المرسِل
    بمقارنة سجلّ الدخول — تفصيلٌ زمنيّ واحد كافٍ لفكّ الجهالة.
    """

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    body: Mapped[str] = mapped_column(String, nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    # `null` = لم تُقرأ بعد. تعليمٌ أحاديّ الاتّجاه — لا "unread" (م-٥: تعليم
    # كمقروءة لا حذف، نمط أرشفة السرب).
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PilotOfWeek(db.Model):
    """
    طيار الأسبوع — FR-062 (و-٩د). **واحدٌ لكل أسبوع** (ث-٩).

    `week_start` بنفس تعريف نافذة `services/standings` تمامًا
    (`orgs.week_starts_on`) — نافذة اجتماعية واحدة عبر كل مشهد و-٩، لا
    تعريفين متوازيين لـ«الأسبوع».
    """

    __tablename__ = "pilot_of_week"
    __table_args__ = (UniqueConstraint("org_id", "week_start", name="uq_pilot_of_week_per_week"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    # نصّ حرّ إلزاميّ — القيمة كلّها في «لماذا» لا في الاسم (ط-١٠ الحرفي).
    reason: Mapped[str] = mapped_column(String, nullable=False)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # «وزن الاختيار» في النموذج المعتمد — ساعاتٌ إضافية تُمنَح للمختار
    # **بتاريخ الأسبوع بالضبط** لا بتاريخ الاختيار. صفرٌ اختيارٌ مشروع:
    # تكريمٌ بلا ساعات.
    bonus_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, server_default="0")
    # العدم حين تكون الساعات صفرًا — لا حدث يُكتب أصلًا، فلا مرجع له.
    point_event_id: Mapped[int | None] = mapped_column(ForeignKey("point_events.id"), nullable=True)
