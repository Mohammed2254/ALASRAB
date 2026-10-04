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

from flask import current_app

from app import create_app
from app.extensions import db
from app.models import (
    DailyQuestion,
    FuelCriterion,
    Membership,
    PointEvent,
    User,
)
from app.rules.engine import Achievement, ruleset_at
from app.services import engagement, fuel, ledger, provision, reading, week
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

# ← `RANKS` انتقلت إلى `services/provision.py` — السقالة واحدة (و-٢١).

# ← `WEIGHTS` و`MULTIPLIERS` انتقلت إلى `services/provision.py` — السقالة واحدة (و-٢١).

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

# سؤال اليوم. والإدراج المباشر هنا لا يتجاوز شيئًا: البذرة تصف حالةً ابتدائية،
# **ومسار المشرف بُني في و-٢١** (`services/daily_question.py` · `FR-097`) —
# بخلاف الساعات التي تمرّ بالمحرّك دائمًا.
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

# ← `ENTRY_DEFAULTS` انتقلت إلى `services/provision.py` — السقالة واحدة (و-٢١).

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
    today = reading.local_today(org)

    # **الأيام المتاحة فعلًا لا المفترَضة:** نافذة التحضير أربعة أيام
    # (الأحد–الأربعاء)، فمنها ما مضى وحده صالح — و`reading.submit` يرفض
    # المستقبل صراحةً. البذرة كانت تكتب `week_start + 1` دائمًا، **فتنكسر كل
    # أحدٍ** (أوّل يوم النافذة، وما بعده لم يأتِ بعد). عطلٌ يظهر يومًا في
    # الأسبوع ويختفي ستّة — وهو أسوأ أنواع هشاشة البذرة.
    days = [
        week_start + timedelta(days=offset)
        for offset in range(4)
        if (week_start + timedelta(days=offset)) <= today
    ]

    # الأخير يبقى معلَّقًا دائمًا — فيُفتح طابور المشرف على بندٍ حقيقيّ لا على
    # فراغ، وهو الغرض المعلَن من هذه البذرة. والاعتماد يقع على ما قبله إن وُجد:
    # يوم الأحد لا تملك النافذة إلا يومًا واحدًا، فالطابور أولى به من الاعتماد.
    for index, day in enumerate(days):
        submission = reading.submit(
            org, user.id, day, 9 - index, "قصص الأنبياء", activity_type="tahdir"
        )
        if index < len(days) - 1:
            reading.approve(org, [submission.id], reviewer_id=1)


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


class SeedRefused(RuntimeError):
    """رفضٌ معلَن — لا بذرة على قاعدةٍ ليست فارغةً أو تبدو إنتاجًا."""


def _guard(force: bool) -> None:
    """
    **البذرة تبدأ بـ`TRUNCATE` لكل الجداول.** تشغيلها على قاعدةٍ حيّة يمحو
    كل شيء — والرمز `1234` للجميع يجعل ما يبقى بعدها مفتوحًا للجميع.
    و`docs/DEPLOY.md` يقول إنها للتطوير وحده، **لكن وثيقةً لا توقف يدًا**.

    حارسان لخطأين مختلفين:
    · بيئةٌ تبدو إنتاجًا (`SESSION_COOKIE_SECURE`، ولا تُضبط إلا خلف HTTPS).
    · قاعدةٌ فيها مستخدمون أصلًا — أيًّا كانت البيئة.

    و`--force` مخرجٌ صريح لمن يعرف ما يفعل، لا افتراضٌ صامت.
    """
    if force:
        return
    if current_app.config.get("SESSION_COOKIE_SECURE"):
        raise SeedRefused(
            "البيئة تبدو إنتاجًا (SESSION_COOKIE_SECURE=true) — البذرة تمحو كل "
            "الجداول وتضع الرمز 1234 للجميع. استعمل `--force` إن كنت متأكّدًا."
        )
    existing = db.session.scalar(db.select(db.func.count(User.id)))
    if existing:
        raise SeedRefused(
            f"القاعدة فيها {existing} مستخدمًا — البذرة تمحوهم جميعًا. "
            "استعمل `--force` إن كنت متأكّدًا."
        )


def run(force: bool = False):
    app = create_app()
    with app.app_context():
        _guard(force)
        db.session.execute(db.text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
        db.session.commit()

        # **السقالة من `services/provision.py` لا مكرَّرةً هنا** (و-٢١):
        # سقالةُ الإنتاج التي لا تمرّ عليها عينٌ كل يوم تفترق عن سقالة
        # التطوير بأوّل صفّ يُضاف لإحداهما — فيُختبَر المشروع على أوزان
        # وعتبات ليست التي ستُنشَر.
        org, team = provision.provision_org(
            name="جمعية الأسراب",
            timezone="Asia/Riyadh",
            team_name="سرب الفرقان",
            team_code="FRQ",
        )
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
    import sys

    try:
        run(force="--force" in sys.argv)
    except SeedRefused as exc:
        print(f"⛔ البذرة مرفوضة: {exc}")
        raise SystemExit(2) from exc
