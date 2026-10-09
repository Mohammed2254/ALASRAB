"""
أسبوع المنظّمة — مالكٌ واحد (`RULES.md` §٩.١أ · و-١٢).

كانت الصيغة مكرَّرة حرفيًّا في أربع خدمات. وخطر التكرار ليس جماليًّا: نسختان
تتباعدان لا تُنتجان عطلًا بل **رقمين مختلفين لنفس الكلمة على شاشتين** — الطالب
يرى ترتيبه في الصدارة محسوبًا على أسبوع، وحضورَه على أسبوع آخر، ولا أحد يلاحظ.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.extensions import db
from app.models import Org
from app.services import engagement, entry, reading, week

SERVICES_DIR = Path(__file__).resolve().parent.parent / "app" / "services"
# رياض = UTC+3 بلا توقيت صيفيّ، فالحساب فيه حتميّ لا يتبع فصلًا.
RIYADH = ZoneInfo("Asia/Riyadh")


def test_week_formula_lives_in_exactly_one_module():
    """
    @covers ق-٢٠١

    حذفُ النسخ اليوم لا يمنع عودتها غدًا بنفس الحجّة التي كُتبت بها («مكرَّرة
    عمدًا لا مستوردة»، موثَّقة في نسختين من الأربع) — فالحارس نصٌّ لا نيّة.

    وفحصٌ نصّيّ لا AST بقصد: المطلوب منع **كتابة الصيغة**، لا تحليل معناها.
    وهي توقيعٌ حرفيّ لا يُكتب بالمصادفة.
    """
    formula = "org.week_starts_on) % 7"
    offenders = sorted(
        path.name
        for path in SERVICES_DIR.glob("*.py")
        if formula in path.read_text() and path.name != "week.py"
    )
    assert (
        not offenders
    ), f"صيغة بداية الأسبوع مكتوبة في {offenders} — مالكها `services/week.py` وحده."


def test_week_starts_on_the_configured_day_in_org_timezone():
    """
    @covers ق-٢٠٢

    ليلة الأحد في الرياض (٠٠:٣٠ محليًّا) هي **السبت ٢١:٣٠ بـUTC**. فحسابُ
    الأسبوع بـUTC يضع هذه اللحظة في الأسبوع **السابق** — أي يرى الطالب إنجازه
    في أسبوع لم يقع فيه (`RULES.md` §٩، نفس علّة `read_on`).
    """
    org = Org(name="x", timezone="Asia/Riyadh", week_starts_on=6)
    just_after_midnight_sunday = datetime(2026, 8, 2, 0, 30, tzinfo=RIYADH)

    assert week.week_start_local(org, just_after_midnight_sunday).isoformat() == "2026-08-02"

    start_utc = week.week_start_utc(org, just_after_midnight_sunday)
    local = start_utc.astimezone(RIYADH)
    assert local.weekday() == 6
    assert (local.hour, local.minute, local.second) == (0, 0, 0)
    # الدليل على أن التحويل وقع فعلًا: منتصف ليل الرياض ليس منتصف ليل UTC.
    assert start_utc.astimezone(UTC).hour == 21


def test_week_start_is_stable_across_the_week(seeded):
    """
    @covers ق-٢٠٢ — كل لحظة داخل الأسبوع تعطي البداية نفسها، لا انزلاقًا يوميًّا.
    """
    org = db.session.get(Org, seeded["org_id"])
    start = week.week_start_local(org, datetime(2026, 8, 2, 0, 30, tzinfo=RIYADH))
    for offset_days in range(7):
        moment = datetime(2026, 8, 2, 12, 0, tzinfo=RIYADH) + timedelta(days=offset_days)
        if week.week_start_local(org, moment) != start:
            # عبَرنا الحدّ — والأسبوع الجديد يجب أن يبدأ بعد الأوّل بسبعة أيام.
            assert week.week_start_local(org, moment) == start + timedelta(days=7)
            break


def test_all_four_consumers_report_the_same_week(client, seeded):
    """
    @covers ق-٢٠٣

    الاتّفاق **مُقاسٌ عبر الخدمات لا مفترَضًا من قراءة الكود**: الحضور
    (`entry`) وتحضير القراءة (`reading`) وطيار الأسبوع (`engagement`) كلّها
    تُعلن حدّ أسبوعها، والثلاثة يجب أن تطابق مالكها. والصدارة (`standings`)
    تستهلك نسخة UTC من نفس المالك — مُختبَرةً في `test_standings.py`.

    وهذا ما كان مستحيلًا إثباته قبل و-١٢: لم يكن هناك «مالك» تُقارَن به.
    """
    org = db.session.get(Org, seeded["org_id"])
    now = datetime.now(UTC)
    expected = week.week_start_local(org, now)

    assert entry.week_status(org, now=now)["week_start"] == expected
    assert reading.weekly_report(org, seeded["users"]["1001"], now=now)["week_start"] == expected

    engagement.choose_week_pilot(
        org,
        actor_id=seeded["users"]["1001"],
        user_id=seeded["users"]["1002"],
        reason="لإثبات أن أسبوع الاختيار هو أسبوع المالك نفسه.",
        now=now,
    )
    chosen = engagement.week_pilot(org, now=now)
    assert chosen is not None
    assert chosen.week_start == expected
