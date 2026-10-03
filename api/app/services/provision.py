"""
تأسيس جمعية جديدة — **المالك الوحيد لسقالة المنظمة** (و-٢١).

وُجد هذا الملفّ لأن `seed.py` كان الكاتب الوحيد في المشروع كلّه لـ`Org` و
`User`، وهو **يرفض الإنتاج صراحةً** (حارس و-٢٠). فقاعدةٌ منشورة جديدة كانت
بلا جمعية ولا مشرف ولا أيّ طريق لإنشائهما: شاشة الدخول تردّ ٤٠١ للأبد.

**ولماذا تُشارِكه البذرة بدل أن تكرّره:** سقالةُ الإنتاج التي لا تمرّ عليها
عينٌ كل يوم تفترق عن سقالة التطوير بأوّل صفّ يُضاف لإحداهما — فيُختبَر
المشروع على أوزان وعتبات ليست التي ستُنشَر. نفس درس `_plan_rows` في و-٢٠:
مسارَان يحسبان الشيء نفسه حرّان في أن يفترقا.

**وكل القيم أوّلية تُعاد معايرتها** (ف-٨): المشرف يضبطها من شاشتَي الأوزان
والعتبات، والصفر مشروع. وجودُها هنا يمنع شاشاتٍ مبنيّة من أن تُفتح على فراغ
(درس و-١٢)، لا يقرّر شيئًا نهائيًّا.
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from ..extensions import db
from ..models import (
    EntryDefault,
    MasteryMultiplier,
    Membership,
    Org,
    RankThreshold,
    Team,
    User,
    Weight,
    WeightVersion,
)
from .auth import generate_pin, hash_pin

# سُلّم `SCOPE.md` §٤ — أربع رتب، وإضافة رتبة صفٌّ لا هجرة.
RANK_LADDER = [
    ("trainee", "طيار", 1, "0"),
    ("pilot1", "طيار أول", 2, "400"),
    ("squadron", "رائد سرب", 3, "900"),
    ("commander", "قائد", 4, "1500"),
]

# الثمانية كاملةً لا الأربعة الأولى: غيابُ وزنٍ يُسقط اعتماد التحضير بـ٤٢٢
# ويجعل استيراد راصد يتخطّى فئات القرآن **صامتًا** (و-١٢).
INITIAL_WEIGHTS = [
    ("memorize", "2.5"),
    ("review", "0.6"),
    ("reading", "0.15"),
    ("attendance", "3.0"),
    ("tahdir", "2.0"),
    ("quran_hifz", "0.2"),
    ("quran_thabat", "0.15"),
    ("quran_muraja3a", "0.1"),
]

MASTERY_MULTIPLIERS = [("mastered", "1.5"), ("accepted", "1.0"), ("repeat", "0.5")]

# أسماء أعمدة ملفّ راصد — بها يتعرّف المستورِد على الأعمدة (الأولوية العليا
# المعلَنة: «سهولة ودقّة أخذ البيانات من ملفّ راصد»). بلا هذه الصفوف يرى
# المشرف ملفًّا صحيحًا يُستورَد فارغًا.
RASD_ENTRY_DEFAULTS = [
    ("quran_hifz_target", "مستهدف الحفظ"),
    ("quran_hifz_achieved", "منجز الحفظ"),
    ("quran_thabat_target", "المستهدف تثبيت"),
    ("quran_thabat_achieved", "المنجز تثبيت"),
    ("quran_muraja3a_target", "المستهدف مراجعة"),
    ("quran_muraja3a_achieved", "المنجز مراجعة"),
    ("attendance", "الحضور"),
    ("tasmi3_days", "أيام التسميع"),
]

# إصدار الأوزان يسري **من الماضي البعيد**: حدثٌ بلا إصدار سارٍ وقت وقوعه
# يُرفض صراحةً (ث-١١)، فاستيرادُ شهرٍ ماضٍ بعد التأسيس يجب أن يجد وزنًا.
WEIGHTS_EFFECTIVE_FROM = datetime(2020, 1, 1, tzinfo=UTC)


class ProvisionError(Exception):
    """خطأ تأسيس — يعرفه الأمر والمسار، ولا يعرف HTTP (نمط `TeamsError`)."""


def org_exists() -> bool:
    return db.session.scalar(select(db.func.count(Org.id))) > 0


def provision_org(*, name: str, timezone: str, team_name: str, team_code: str) -> tuple[Org, Team]:
    """
    سقالة الجمعية: رتب + إصدار أوزان + مُضاعِفات + افتراضات راصد + أوّل سرب.

    **بلا `commit`** — المستدعي يُتمّ المعاملة، فالسقالة وما يُبنى عليها
    (أوّل مشرف، أو بذرةٌ كاملة) ذرّيّةٌ معًا. سقالةٌ بلا مشرف لا يدخلها أحد،
    والنصف أسوأ من الصفر هنا.
    """
    org = Org(name=name.strip(), timezone=timezone.strip())
    db.session.add(org)
    db.session.flush()

    for key, rank_name, tier, at_hours in RANK_LADDER:
        db.session.add(
            RankThreshold(
                org_id=org.id, key=key, name=rank_name, tier=tier, at_hours=Decimal(at_hours)
            )
        )

    version = WeightVersion(
        org_id=org.id,
        effective_from=WEIGHTS_EFFECTIVE_FROM,
        note="أوزان أوّلية — تُعاد معايرتها من شاشة الأوزان بعد بيانات حقيقية",
    )
    db.session.add(version)
    db.session.flush()
    for activity_type, per_unit in INITIAL_WEIGHTS:
        db.session.add(
            Weight(
                version_id=version.id,
                activity_type=activity_type,
                hours_per_unit=Decimal(per_unit),
            )
        )
    for grade, multiplier in MASTERY_MULTIPLIERS:
        db.session.add(
            MasteryMultiplier(version_id=version.id, grade=grade, multiplier=Decimal(multiplier))
        )
    for activity_type, label in RASD_ENTRY_DEFAULTS:
        db.session.add(EntryDefault(org_id=org.id, activity_type=activity_type, label=label))

    team = Team(org_id=org.id, name=team_name.strip(), code=team_code.strip())
    db.session.add(team)
    db.session.flush()
    return org, team


def provision_first_admin(
    org: Org, team: Team, *, full_name: str, student_no: str, pin: str | None = None
) -> tuple[User, str]:
    """
    أوّل مشرف. الرمز يُولَّد إن لم يُعطَ، ويُعاد **نصًّا مرّةً واحدة** ولا
    يُخزَّن أبدًا (نفس عقد `auth.reset_pin`). بلا `commit`.

    والدور على العضوية لا على المستخدم — وصلاحيته على مستوى الجمعية لا السرب
    (`AGENTS.md` ٩)، فالسرب هنا مكانُ انتسابٍ لا حدُّ سلطة.
    """
    issued = pin if pin is not None else generate_pin()
    admin = User(
        org_id=org.id,
        full_name=full_name.strip(),
        student_no=student_no.strip(),
        pin_hash=hash_pin(issued),
    )
    db.session.add(admin)
    db.session.flush()
    db.session.add(Membership(org_id=org.id, user_id=admin.id, team_id=team.id, role="admin"))
    return admin, issued


def bootstrap(
    *,
    name: str,
    timezone: str,
    team_name: str,
    team_code: str,
    admin_name: str,
    admin_student_no: str,
    admin_pin: str | None = None,
) -> tuple[Org, Team, User, str]:
    """
    التأسيس الكامل في **معاملة واحدة** — مدخل `flask bootstrap-org`.

    **ويرفض الثانية صراحةً:** `auth.default_org_id()` يختار أوّل جمعية، فجمعيةٌ
    ثانيةٌ تُنشأ سهوًا تصير غير قابلة للدخول وغير مرئية — عطلٌ صامت.

    **وبلا سطر تدقيق:** `audit_log.actor_id` يُشير إلى `users`، ولا فاعل يسبق
    أوّل مشرف. وتأسيسُ الجمعية يُرى في وجودها نفسها لا في سطرٍ عنها.
    """
    if org_exists():
        raise ProvisionError(
            "توجد جمعية في هذه القاعدة أصلًا — التأسيس لا يُشغَّل إلا على قاعدة فارغة."
        )
    org, team = provision_org(
        name=name, timezone=timezone, team_name=team_name, team_code=team_code
    )
    admin, pin = provision_first_admin(
        org, team, full_name=admin_name, student_no=admin_student_no, pin=admin_pin
    )
    db.session.commit()
    return org, team, admin, pin
