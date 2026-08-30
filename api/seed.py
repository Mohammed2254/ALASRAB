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
    MasteryMultiplier,
    Membership,
    Org,
    RankThreshold,
    Team,
    User,
    Weight,
    WeightVersion,
)
from app.rules.engine import Achievement, ruleset_at
from app.services import ledger
from app.services.auth import hash_pin

TABLES = [
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

WEIGHTS = [
    ("memorize", "2.5"),
    ("review", "0.6"),
    ("reading", "0.15"),
    ("attendance", "3.0"),
    ("daily_question", "2.0"),
]
MULTIPLIERS = [("mastered", "1.5"), ("accepted", "1.0"), ("repeat", "0.5")]

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
