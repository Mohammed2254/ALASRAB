"""
بذرة تطوير حتمية.

**تصف إنجازات لا ساعات.** الساعة تُشتقّ من صفحاتٍ بوزنٍ سارٍ وقت وقوعها — وهذا
هو المنتج نفسه: طبقة تنافس **فوق إنجاز**. بذرةٌ تكتب `delta` رقمًا تتجاوز
`rules/engine`، أي تتجاوز القاعدة التي وُجد المشروع لأجلها، وتترك المحرّك كودًا
لا يستدعيه أحد.

المسار الفعلي هنا هو المسار المصمَّم:
    Achievement → ruleset_at(occurred_at) → hours_for → EventSpec → ledger → point_events

TRUNCATE ... RESTART IDENTITY: المعرّفات تبدأ من ١ في كل تشغيل، فتصير الأخطاء
قابلة لإعادة الإنتاج. ولا يُطلق مشغّل ث-٢ لأنه لا يُطلق مشغّلات الصفوف —
مُختبَرًا في `test_invariants.py`.

**كل الأوزان هنا مؤلَّفة** (ف-٨ و ف-٩): وحدة القياس غير محسومة حتى تصل عيّنة
راصد (س-١). تُعاد المعايرة بعد شهر بيانات حقيقية، وسجلّ الأحداث يجعل إعادة
الحساب الكاملة ممكنة.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import (
    DailyQuestion,
    EntryDefault,
    FuelCriterion,
    MasteryMultiplier,
    Membership,
    Org,
    PointEvent,
    RankThreshold,
    Team,
    User,
    Weight,
    WeightVersion,
)
from app.rules.engine import Achievement, ruleset_at
from app.services import engagement, fuel, ledger, reading, week
from app.services.auth import hash_pin

TABLES = [
    "reading_submissions",
    "audit_log",
    "answers",
    "daily_questions",
    "notes",
    "pilot_of_week",
    "raw_rows",
    "fuel_scores",
    "fuel_assessments",
    "fuel_criteria",
    "fuel_activities",
    "point_events",
    "login_attempts",
    "sessions",
    "memberships",
    "weights",
    "mastery_multipliers",
    "weight_versions",
    "rank_thresholds",
    "users",
    "teams",
    "orgs",
]

# سُلّم `SCOPE.md` §٤ — أربع رتب اليوم، وإضافة رتبة صفٌّ لا هجرة.
RANKS = [
    ("trainee", "طيار", 1, 0),
    ("pilot1", "طيار أول", 2, 400),
    ("squadron", "رائد سرب", 3, 900),
    ("commander", "قائد", 4, 1500),
]

# و-١٢: الأوزان الأربعة الأولى كانت وحدها مبذورة، والأربعة الباقية «مؤجَّلة
# عمدًا» — فكان أثرُ التأجيل أن **اعتماد أي تحضير يسقط بـ٤٢٢** («لا وزن سارٍ»)
# وأن استيراد راصد يتخطّى فئات القرآن الثلاث بصمت، على كل قاعدة تطوير نظيفة.
# التأجيل كان لانتظار معايرة حقيقية، والمعايرة لا تمنع وجود قيمة أوّلية تُعاد
# (ف-٨) — فغيابُها عطّل شاشات مبنيّة، ووجودُها لا يقرّر شيئًا نهائيًّا.
WEIGHTS = [
    ("memorize", "2.5"),
    ("review", "0.6"),
    ("reading", "0.15"),
    ("attendance", "3.0"),
    ("tahdir", "2.0"),
    ("quran_hifz", "0.2"),
    ("quran_thabat", "0.15"),
    ("quran_muraja3a", "0.1"),
]
MULTIPLIERS = [("mastered", "1.5"), ("accepted", "1.0"), ("repeat", "0.5")]

# نشاط وقود واحد ببنوده — أوزانه تجمع ١٠٠٪ بالضبط (ث-١٠أ، وتُفحص في الخدمة
# وفي القاعدة). بدونه تُفتح «محطة التزوّد» وشاشتا الوقود على فراغ، فلا يقيس
# القياس البصري شيئًا (الدرس ٣).
FUEL_ACTIVITY = {
    "key": "ashaa",
    "name": "العشاء",
    "litres_full": Decimal("120.00"),
    "criteria": [
        {"key": "taste", "name": "الطعم", "weight_pct": Decimal("35")},
        {"key": "creativity", "name": "الإبداع", "weight_pct": Decimal("20")},
        {"key": "presentation", "name": "الشكل", "weight_pct": Decimal("18")},
        {"key": "announcement", "name": "الإعلان", "weight_pct": Decimal("17")},
        {"key": "cleanup", "name": "النظافة وتغسيل الأواني", "weight_pct": Decimal("10")},
    ],
}
# درجاتٌ لا تبلغ الكامل — فتُرى نسبةٌ حقيقية على العدّاد لا ١٠٠٪ مسطّحة.
FUEL_SCORES = ["27", "13", "12", "11", "8"]

# سؤال اليوم: **بلا مسار إنشاء إداريّ** (`SCOPE.md` ط-٦ فجوة معلَنة)، فالإدراج
# المباشر هنا هو المسار المصمَّم لا تجاوزًا له — بخلاف الساعات التي تمرّ بالمحرّك.
QUESTION = {
    "prompt": "كم عدد أجزاء القرآن الكريم؟",
    "choices": [
        {"id": 1, "text": "عشرون جزءًا"},
        {"id": 2, "text": "ثلاثون جزءًا"},
        {"id": 3, "text": "مئة وأربعة عشر جزءًا"},
    ],
    "correct_id": 2,
    "note": "القرآن ثلاثون جزءًا، وتقسيمه إليها اصطلاحٌ للتيسير على الحافظ لا توقيف.",
    "reward_hours": Decimal("1.00"),
}

# و-٥ — مرادفات ترويسة استيراد راصد (نسخة اليوم بلا مرادفات بديلة بعد؛ صفٌّ
# جديد في `aliases` يكفي عند تغيّر تسمية عمود مستقبلًا، بلا كود جديد).
# أوزان الفئات الثلاث مبذورةٌ أعلاه بقيمٍ أوّلية (٠.٢٠ · ٠.١٥ · ٠.١٠)، ويضبطها
# المشرف عبر `/admin/weights` — لم تعد TBD (و-٢٠، `RULES.md` §٤).
ENTRY_DEFAULTS = [
    ("quran_hifz_target", "مستهدف الحفظ"),
    ("quran_hifz_achieved", "منجز الحفظ"),
    ("quran_thabat_target", "المستهدف تثبيت"),
    ("quran_thabat_achieved", "المنجز تثبيت"),
    ("quran_muraja3a_target", "المستهدف مراجعة"),
    ("quran_muraja3a_achieved", "المنجز مراجعة"),
    ("attendance", "الحضور"),
    ("tasmi3_days", "أيام التسميع"),
]

# أربعة طلاب يغطّون الحالات التي تكسر بطاقة الطيار عادةً.
# الكمّيات تُختار لتقع على العتبات المقصودة **بعد** الحساب لا قبله:
#   ١٦٣ صفحة × ٢.٥ × ١.٥ = ٦١١.٢٥ ساعة ⇒ «طيار أول» وتقدّم ٤٢.٢٪ داخل الشريحة
#   ٤١٦ صفحة × ٢.٥ × ١.٥ = ١٥٦٠.٠٠      ⇒ «قائد» — أعلى رتبة (ق-٧)
#    ٣٥ صفحة × ٢.٥ × ١.٠ =   ٨٧.٥٠      ⇒ «طيار» وآخر نشاط قبل ٣٠ يومًا (ق-٨)
PEOPLE = [
    ("بندر الشمري", "1001", "admin", [("memorize", 163, "mastered", 2)]),
    ("سالم العتيبي", "1002", "pilot", []),  # ق-٦ الحالة الفارغة
    ("ماجد القحطاني", "1003", "pilot", [("memorize", 416, "mastered", 2)]),
    ("فهد الدوسري", "1004", "pilot", [("memorize", 35, "accepted", 30)]),
]


def _award(org_id: int, user_id: int, student_no: str, entries: list) -> None:
    """
    إنجازات طالب واحد ⇒ ساعات ⇒ أحداث.

    القواعد تُحمَّل مرّة لكل لحظة وقوع لا لكل إنجاز: دفعةٌ تشترك في اللحظة نفسها
    تكلّف ثلاثة استعلامات لا ثلاثة × العدد.
    """
    now = datetime.now(UTC)
    specs = []
    for activity, quantity, mastery, days_ago in entries:
        occurred_at = now - timedelta(days=days_ago)
        achievement = Achievement(
            user_id=user_id,
            occurred_at=occurred_at,
            activity_type=activity,
            quantity=Decimal(quantity),
            mastery=mastery,
            external_ref=f"seed:{student_no}:{activity}:{days_ago}",
        )
        hours = ruleset_at(org_id, occurred_at).hours_for(achievement)
        specs.append(
            ledger.EventSpec(
                org_id=org_id,
                kind="quran",
                delta=hours,
                user_id=user_id,
                occurred_at=occurred_at,
                external_ref=achievement.external_ref,
            )
        )
    if specs:
        ledger.append(specs)


def _seed_readings(org, user) -> None:
    """
    طلبات قراءة بالحالات الثلاث — فتُفتح شاشتا و-٤ على بيانات لا على فراغ.

    وتمرّ بالخدمة لا بإدخال مباشر: البذرة التي تتجاوز القواعد تخفي كسرها.
    """
    if user is None:
        return
    today = reading.local_today(org)
    reading.submit(org, user.id, today - timedelta(days=1), 25, "الرحيق المختوم")
    approved = reading.submit(org, user.id, today - timedelta(days=3), 40, "زاد المعاد")
    rejected = reading.submit(org, user.id, today - timedelta(days=5), 12, "كتاب غير معتمد")
    reading.approve(org, [approved.id], reviewer_id=1)
    reading.reject(org, rejected.id, reviewer_id=1, reason="الكتاب خارج القائمة المعتمدة")


def _seed_tahdir(org, user) -> None:
    """
    تحضيرات داخل نافذة الأحد–الأربعاء الحالية، واحدٌ منها معتمَد.

    **تمرّ بـ`reading.submit` لا بإدراج مباشر** — فيُفحص يوم الأسبوع والحدّ
    الأدنى (ث-١٨ وفحص الخدمة) على البذرة نفسها. وبذرةٌ تتجاوزهما تُنتج صفوفًا
    لا يستطيع المنتج إنتاجها.
    """
    if user is None:
        return
    week_start = week.week_start_local(org, datetime.now(UTC))
    first = reading.submit(org, user.id, week_start, 9, "قصص الأنبياء", activity_type="tahdir")
    reading.approve(org, [first.id], reviewer_id=1)
    # الثاني يبقى معلَّقًا — فيُفتح طابور المشرف على بندٍ حقيقيّ لا على فراغ.
    reading.submit(
        org, user.id, week_start + timedelta(days=1), 8, "رياض الصالحين", activity_type="tahdir"
    )


def _seed_fuel(org, team, actor_id: int) -> None:
    """نشاط وقود مُقيَّم — فتُفتح محطة التزوّد على رصيد مشتقّ من بنود موزونة."""
    activity = fuel.create_activity(
        org,
        key=FUEL_ACTIVITY["key"],
        name=FUEL_ACTIVITY["name"],
        litres_full=FUEL_ACTIVITY["litres_full"],
        criteria=FUEL_ACTIVITY["criteria"],
    )
    criteria = db.session.scalars(
        db.select(FuelCriterion)
        .where(FuelCriterion.activity_id == activity.id)
        .order_by(FuelCriterion.position)
    ).all()
    fuel.assess(
        org,
        team_id=team.id,
        activity_id=activity.id,
        occurred_on=reading.local_today(org),
        scores={c.id: Decimal(s) for c, s in zip(criteria, FUEL_SCORES, strict=True)},
        note="تقييم أوّلي مبذور — يُعاد بعد بيانات حقيقية.",
        actor_id=actor_id,
    )


def _seed_engagement(org, actor_id: int, pilot) -> None:
    """سؤال اليوم وملاحظة مجهولة وطيار أسبوع — شاشات و-٩ بلا فراغ."""
    db.session.add(
        DailyQuestion(
            org_id=org.id,
            day=reading.local_today(org),
            prompt=QUESTION["prompt"],
            choices=QUESTION["choices"],
            correct_id=QUESTION["correct_id"],
            note=QUESTION["note"],
            reward_hours=QUESTION["reward_hours"],
        )
    )
    db.session.commit()

    engagement.submit_note(org, "ما ظهر لي زرّ تحضير القراءة يوم الخميس — هل هذا مقصود؟")
    if pilot is not None:
        engagement.choose_week_pilot(
            org,
            actor_id=actor_id,
            user_id=pilot.id,
            reason="أعلى التزامًا بالتحضير هذا الأسبوع، وساعد اثنين من سربه على اللحاق.",
        )


def _seed_correction(user) -> None:
    """
    تصحيحٌ واحد — فيُفتح سجلّ الساعات على السلوك الذي يوجبه ط-٤ لا على أحداث
    موجبة وحدها.

    **وهو ما يجعل الفحص البصري ذا معنى:** السالب بإشارته وسببه بالأحمر سلوكٌ
    يُرى، ووجودُه في اختبار لا يثبت ظهوره — وهذا درسُ رمز `⛔` في و-١.
    """
    if user is None:
        return
    event = db.session.scalar(
        db.select(PointEvent).where(PointEvent.user_id == user.id).order_by(PointEvent.id)
    )
    if event is not None:
        ledger.reverse(event, "خطأ في تصدير راصد — صفحات مضاعفة", actor_id=1)


def run():
    app = create_app()
    with app.app_context():
        db.session.execute(db.text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
        db.session.commit()

        org = Org(name="جمعية الأسراب", timezone="Asia/Riyadh")
        db.session.add(org)
        db.session.flush()
        for key, name, tier, hours in RANKS:
            db.session.add(
                RankThreshold(org_id=org.id, key=key, name=name, tier=tier, at_hours=Decimal(hours))
            )

        team = Team(org_id=org.id, name="سرب الفرقان", code="FRQ")
        db.session.add(team)
        db.session.flush()

        # سارٍ من الماضي البعيد: حدثٌ بلا إصدار سارٍ وقت وقوعه يُرفض صراحةً
        # (ث-١١)، فالبذرة يجب أن تسبق كل حدث تنشئه.
        version = WeightVersion(
            org_id=org.id,
            effective_from=datetime(2020, 1, 1, tzinfo=UTC),
            note="أوزان أوّلية مؤلَّفة — تُعاد بعد بيانات حقيقية",
        )
        db.session.add(version)
        db.session.flush()
        for activity, per_unit in WEIGHTS:
            db.session.add(
                Weight(
                    version_id=version.id, activity_type=activity, hours_per_unit=Decimal(per_unit)
                )
            )
        for grade, mult in MULTIPLIERS:
            db.session.add(
                MasteryMultiplier(version_id=version.id, grade=grade, multiplier=Decimal(mult))
            )
        for activity_type, label in ENTRY_DEFAULTS:
            db.session.add(EntryDefault(org_id=org.id, activity_type=activity_type, label=label))
        db.session.commit()

        for full_name, student_no, role, entries in PEOPLE:
            user = User(
                org_id=org.id, full_name=full_name, student_no=student_no, pin_hash=hash_pin("1234")
            )
            db.session.add(user)
            db.session.flush()
            db.session.add(Membership(org_id=org.id, user_id=user.id, team_id=team.id, role=role))
            db.session.commit()
            _award(org.id, user.id, student_no, entries)

        # بعد إنشاء الطلاب: البذرة تحتاج مستخدمًا قائمًا.
        student = db.session.scalar(db.select(User).where(User.student_no == "1002"))
        _seed_readings(org, student)
        _seed_tahdir(org, student)
        _seed_correction(db.session.scalar(db.select(User).where(User.student_no == "1004")))

        # المشرف (`1001`) فاعلُ كل ما يوجب نسبةً — لا معرّف مكتوب رقمًا.
        admin = db.session.scalar(db.select(User).where(User.student_no == "1001"))
        _seed_fuel(org, team, actor_id=admin.id)
        _seed_engagement(
            org,
            actor_id=admin.id,
            pilot=db.session.scalar(db.select(User).where(User.student_no == "1003")),
        )

        print(f"✅ بذرة: منظمة {org.id} · سرب {team.id} · {len(PEOPLE)} طلاب · رمز الجميع 1234")
        for full_name, student_no, _, _ in PEOPLE:
            total = db.session.scalar(
                db.text(
                    "SELECT COALESCE(SUM(delta),0) FROM point_events pe "
                    "JOIN users u ON u.id = pe.user_id WHERE u.student_no = :no"
                ),
                {"no": student_no},
            )
            print(f"   {full_name}: {total} ساعة — مشتقّة من المحرّك")


if __name__ == "__main__":
    run()
