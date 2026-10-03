"""
تأسيس الجمعية — و-٢١.

**العطل الذي وُجد هذا الملفّ لأجله:** قبل و-٢١ لم يكن في المشروع مسارٌ واحد
يُنشئ `Org` أو `User` إلا `seed.py` — وهو يرفض الإنتاج صراحةً. فقاعدةٌ منشورة
جديدة كانت بلا جمعية ولا مشرف ولا طريق إليهما: شاشة الدخول تردّ ٤٠١ للأبد.

@covers ق-٢٦٤, ق-٢٦٥, ق-٢٦٦, ق-٢٦٧
"""

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import EntryDefault, Membership, Org, RankThreshold, User, Weight, WeightVersion
from app.services import provision

from conftest import TABLES

ORIGIN = {"Origin": "http://localhost:5173"}

ARGS = {
    "name": "جمعية التأسيس",
    "timezone": "Asia/Riyadh",
    "team_name": "السرب الأول",
    "team_code": "SQ1",
    "admin_name": "مشرف أوّل",
    "admin_student_no": "9001",
}


@pytest.fixture
def empty(app):
    """قاعدةٌ بلا جمعية إطلاقًا — حالة الخادم لحظة أوّل نشر، لا حالة `seeded`."""
    db.session.execute(db.text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
    db.session.commit()
    return app


# ═══ ق-٢٦٤ — التأسيس يُنتج جمعيةً يُدخَل إليها فعلًا ═══


def test_bootstrap_produces_a_loginable_org(client, empty):
    """
    **الفحص الحقيقيّ ليس وجود الصفوف بل الدخول.** جمعيةٌ كاملة الصفوف ومشرفٌ
    لا يدخل بها هي بعينها الحالة التي كانت قائمة قبل و-٢١.

    @covers ق-٢٦٤
    """
    org, team, admin, pin = provision.bootstrap(**ARGS)

    assert org.id and team.id and admin.id
    assert len(pin) == 4 and pin.isdigit()

    r = client.post(
        "/api/auth/login", json={"student_no": "9001", "pin": pin}, headers=ORIGIN
    )
    assert r.status_code == 200, r.get_json()
    # والدور **مشرف** — لا جمعيةً يفتحها طيّار بلا لوحة إدارة.
    assert r.get_json()["user"]["role"] == "admin"


def test_bootstrap_lays_the_full_scaffold(empty):
    """
    سُلّم الرتب وإصدار الأوزان وافتراضات راصد — **الثلاثة أو لا شيء**.

    بلا سُلّم رتب تنكسر بطاقة الطيار، وبلا وزنٍ سارٍ **يسقط اعتماد أي تحضير
    بـ٤٢٢** ويتخطّى استيراد راصد فئات القرآن صامتًا (درس و-١٢ حرفيًّا)، وبلا
    افتراضات راصد يُستورَد ملفٌّ صحيح فارغًا.

    @covers ق-٢٦٥
    """
    org, _, _, _ = provision.bootstrap(**ARGS)

    ladder = db.session.scalars(
        select(RankThreshold).where(RankThreshold.org_id == org.id).order_by(RankThreshold.tier)
    ).all()
    assert [r.tier for r in ladder] == [1, 2, 3, 4]
    assert [r.at_hours for r in ladder] == [Decimal(h) for h in ("0", "400", "900", "1500")]

    version = db.session.scalar(select(WeightVersion).where(WeightVersion.org_id == org.id))
    weights = db.session.scalars(
        select(Weight).where(Weight.version_id == version.id)
    ).all()
    # الثمانية كاملةً — لا الأربعة الأولى وحدها (و-١٢).
    assert {w.activity_type for w in weights} == {
        "memorize",
        "review",
        "reading",
        "attendance",
        "tahdir",
        "quran_hifz",
        "quran_thabat",
        "quran_muraja3a",
    }

    defaults = db.session.scalars(
        select(EntryDefault).where(EntryDefault.org_id == org.id)
    ).all()
    assert len(defaults) == len(provision.RASD_ENTRY_DEFAULTS)


# ═══ ق-٢٦٦ — لا جمعية ثانية ═══


def test_second_bootstrap_is_refused(empty):
    """
    `auth.default_org_id()` يختار **أوّل** جمعية، فجمعيةٌ ثانيةٌ تُنشأ سهوًا
    تصير غير قابلة للدخول وغير مرئية — عطلٌ صامت أسوأ من الرفض الصاخب.

    @covers ق-٢٦٦
    """
    provision.bootstrap(**ARGS)

    with pytest.raises(provision.ProvisionError):
        provision.bootstrap(**{**ARGS, "admin_student_no": "9002", "team_code": "SQ2"})

    assert db.session.scalar(select(db.func.count(Org.id))) == 1


def test_refusal_leaves_nothing_behind(empty):
    """
    الرفض **قبل أيّ كتابة** لا بعدها: جمعيةٌ ثانيةٌ نصفُ مكتوبةٍ ثمّ مرفوضة
    تترك سربًا ومشرفًا يتيمَين يظهران في كل استعلامٍ لا يُرشِّح `org_id`.

    @covers ق-٢٦٦
    """
    provision.bootstrap(**ARGS)
    users_before = db.session.scalar(select(db.func.count(User.id)))

    with pytest.raises(provision.ProvisionError):
        provision.bootstrap(**{**ARGS, "admin_student_no": "9002", "team_code": "SQ2"})
    db.session.rollback()

    assert db.session.scalar(select(db.func.count(User.id))) == users_before


# ═══ ق-٢٦٧ — الرمز ═══


def test_generated_pin_is_not_stored_in_cleartext(empty):
    """
    الرمز يُعاد مرّةً ولا يُخزَّن — نفس عقد `auth.reset_pin` (§٧.٥).

    @covers ق-٢٦٧
    """
    _, _, admin, pin = provision.bootstrap(**ARGS)
    assert pin not in admin.pin_hash
    assert admin.pin_hash.startswith("$argon2")


def test_generated_pins_differ_across_orgs(empty):
    """مولِّدٌ ثابت القيمة أسوأ من لا مولِّد: رمزٌ واحدٌ لكل جمعية يُنشَر مرّة."""
    pins = set()
    for index in range(12):
        db.session.execute(db.text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
        db.session.commit()
        db.session.remove()  # خريطة الهوية تحمل `User(1)` من الدورة السابقة
        _, _, _, pin = provision.bootstrap(
            **{**ARGS, "admin_student_no": f"90{index:02d}"}
        )
        pins.add(pin)
    # اثنا عشر سحبًا من عشرة آلاف: التطابق الكامل احتمالٌ لا يُقاس.
    assert len(pins) > 1


def test_explicit_pin_is_honoured(empty):
    """
    الرمز الصريح مخرجٌ للاختبار والتهيئة غير التفاعلية — ويجب أن **يعمل
    فعلًا**، لا أن يُتجاهَل بصمت لحساب المولَّد.

    @covers ق-٢٦٧
    """
    _, _, _, pin = provision.bootstrap(**{**ARGS, "admin_pin": "4242"})
    assert pin == "4242"


def test_admin_membership_is_org_wide_not_team_scoped(empty):
    """الدور على العضوية لا على المستخدم، وصلاحيته على الجمعية (`AGENTS.md` ٩)."""
    org, team, admin, _ = provision.bootstrap(**ARGS)
    membership = db.session.scalar(select(Membership).where(Membership.user_id == admin.id))
    assert membership.role == "admin"
    assert membership.team_id == team.id
    assert membership.left_at is None
