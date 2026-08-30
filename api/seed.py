"""
بذرة تطوير حتمية.

TRUNCATE ... RESTART IDENTITY: المعرّفات تبدأ من ١ في كل تشغيل، فتصير الاختبارات
مستقرّة والأخطاء قابلة لإعادة الإنتاج. وTRUNCATE لا يُطلق مشغّل ث-٢ لأنه لا يُطلق
مشغّلات الصفوف — مُختبَرًا لا مفترَضًا.

**كل الأرقام هنا مؤلَّفة** (ف-٨ و ف-٩): وحدة القياس نفسها غير محسومة حتى تصل
عيّنة راصد (س-١). تُعاد المعايرة بعد شهر بيانات حقيقية، وسجلّ الأحداث + الصفوف
الخام يجعلان إعادة الحساب الكاملة ممكنة.
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

        # إصدار أوزان سارٍ من الماضي البعيد: حدثٌ بلا إصدار سارٍ وقت وقوعه
        # يُرفض صراحةً (ث-١١)، فالبذرة يجب أن تسبق كل حدث تنشئه.
        version = WeightVersion(
            org_id=org.id,
            effective_from=datetime(2020, 1, 1, tzinfo=UTC),
            note="أوزان أوّلية مؤلَّفة — تُعاد بعد بيانات حقيقية",
        )
        db.session.add(version)
        db.session.flush()
        for activity, per_unit in [
            ("memorize", "2.5"),
            ("review", "0.6"),
            ("reading", "0.15"),
            ("attendance", "3.0"),
            ("daily_question", "2.0"),
        ]:
            db.session.add(
                Weight(
                    version_id=version.id, activity_type=activity, hours_per_unit=Decimal(per_unit)
                )
            )
        for grade, mult in [("mastered", "1.5"), ("accepted", "1.0"), ("repeat", "0.5")]:
            db.session.add(
                MasteryMultiplier(version_id=version.id, grade=grade, multiplier=Decimal(mult))
            )

        # ثلاثة طلاب يغطّون الحالات التي تكسر الواجهة عادةً: رصيد متوسّط،
        # وصفر مطلق، وأعلى رتبة. ورابع أرضي لاختبار ث-١٤.
        people = [
            ("بندر الشمري", "1001", "612.25", 2),
            ("سالم العتيبي", "1002", None, 2),
            ("ماجد القحطاني", "1003", "1560.00", 2),
            ("فهد الدوسري", "1004", "88.00", 30),
        ]
        now = datetime.now(UTC)
        for full_name, student_no, hours, days_ago in people:
            user = User(
                org_id=org.id, full_name=full_name, student_no=student_no, pin_hash=hash_pin("1234")
            )
            db.session.add(user)
            db.session.flush()
            db.session.add(
                Membership(
                    org_id=org.id,
                    user_id=user.id,
                    team_id=team.id,
                    role="admin" if student_no == "1001" else "pilot",
                )
            )
            db.session.commit()
            if hours is not None:
                ledger.append(
                    [
                        ledger.EventSpec(
                            org_id=org.id,
                            kind="quran",
                            delta=Decimal(hours),
                            user_id=user.id,
                            occurred_at=now - timedelta(days=days_ago),
                            external_ref=f"seed:{student_no}:quran",
                        )
                    ]
                )

        db.session.commit()
        print(f"✅ بذرة: منظمة {org.id} · سرب {team.id} · {len(people)} طلاب · رمز الجميع 1234")


if __name__ == "__main__":
    run()
