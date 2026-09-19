"""
اللوحات والتشكيل — و-٩ب · FR-050 · FR-051 · FR-052 · FR-053.

**قراءة خالصة**: لا `ledger` جديد ولا جدول جديد — كل رقم من `point_events`
الموجود، بنفس نمط `reports.py`/`deck.py`. أغلب الإثباتات تستدعي
`services/standings` مباشرةً بـ`now` صريح: نافذة الأسبوع حسّاسة للحظة
التشغيل، والاستدعاء المباشر يزيل هذه الحسّاسية عن الاختبار (لا عن الخدمة).
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.extensions import db
from app.models import Membership, Org, Team, User
from app.services import ledger, standings, week
from app.services.auth import hash_pin

ORIGIN = {"Origin": "http://localhost:5173"}
PILOTS = "/api/boards/pilots"
TEAMS = "/api/boards/teams"
FORMATION = "/api/boards/formation"
DECK = "/api/me/deck"

# أربعاء ٢٠٢٦-٠٨-٠٥ بتوقيت الرياض — بداية أسبوعه المحسوبة يدويًّا الأحد
# ٢٠٢٦-٠٨-٠٢ (تحقّق مستقلّ عبر `date(2026, 8, 2).strftime('%A')`), لا من
# `standings._week_start` نفسها — وإلا كان الإثبات دائريًّا.
NOW = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)
WEEK_START = datetime(2026, 8, 2, 0, 0, tzinfo=ZoneInfo("Asia/Riyadh")).astimezone(UTC)


def _login(client, student_no="1001"):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": "1234"}, headers=ORIGIN
    )


def _event(org_id, user_id, delta, occurred_at, kind="quran"):
    return ledger.append(
        [
            ledger.EventSpec(
                org_id=org_id,
                kind=kind,
                delta=Decimal(delta),
                user_id=user_id,
                occurred_at=occurred_at,
            )
        ]
    )[0]


def _team(org_id, name, code):
    t = Team(org_id=org_id, name=name, code=code)
    db.session.add(t)
    db.session.flush()
    return t


def _pilot(org_id, name, no, team_id):
    u = User(org_id=org_id, full_name=name, student_no=no, pin_hash=hash_pin("1234"))
    db.session.add(u)
    db.session.flush()
    db.session.add(Membership(org_id=org_id, user_id=u.id, team_id=team_id, role="pilot"))
    return u.id


# ═══ ق-٧٨ · ق-٨٣ — نافذة الأسبوع، لا التراكم ═══


def test_pilots_board_counts_this_week_only(client, seeded):
    """@covers ق-٧٨, ق-٨٣"""
    org = db.session.get(Org, seeded["org_id"])
    uid = seeded["users"]["1001"]
    _event(org.id, uid, "5.00", WEEK_START - timedelta(seconds=1))  # الأسبوع الماضي
    _event(org.id, uid, "3.00", WEEK_START + timedelta(seconds=1))  # هذا الأسبوع
    db.session.commit()

    board = standings.pilots_board(org, now=NOW)
    row = next(p for p in board if p["full_name"] == "طالب أول")
    assert row["hours"] == Decimal("3.00")


def test_week_start_matches_orgs_week_starts_on():
    """
    @covers ق-٨٣, ق-٢٠٢

    نمط `RULES.md` §٩.١أ: `week_starts_on=6` (الأحد) فعليًّا، وبداية اليوم
    **بتوقيت المنظمة** لا منتصف ليل UTC. انتقلت الدالّة من
    `standings._week_start` الخاصّة إلى `services/week.py` العامّة في و-١٢ —
    فصار الاختبار يُصيب مالكها لا مستعيرها.
    """
    org = Org(name="x", timezone="Asia/Riyadh", week_starts_on=6)
    start = week.week_start_utc(org, NOW)
    local = start.astimezone(ZoneInfo("Asia/Riyadh"))
    assert local.weekday() == 6
    assert (local.hour, local.minute, local.second) == (0, 0, 0)
    assert local.date().isoformat() == "2026-08-02"


# ═══ ق-٧٩ — فكّ تعادل الأفراد حتميّ ═══


def test_pilots_board_tie_break_is_stable_by_id(client, seeded):
    """@covers ق-٧٩ — بلا أحداث لكليهما: تعادل صفر⇔صفر، والترتيب بـid تصاعديًّا."""
    org = db.session.get(Org, seeded["org_id"])
    board = standings.pilots_board(org, now=NOW)
    names = [p["full_name"] for p in board]
    assert names.index("طالب أول") < names.index("طالب ثانٍ")


# ═══ ق-٨٠ — بالمعدّل لا بالمجموع ═══


def test_teams_board_ranks_by_average_not_sum(client, seeded):
    """
    @covers ق-٨٠ — سربٌ صغير بمعدّل أعلى يتصدّر سربًا أكبر مجموعه أعلى.
    فريق كبير: ١٠ أعضاء × ٥ = مجموع ٥٠. فريق صغير: عضوان × ٢٠ = مجموع ٤٠.
    بالمجموع يتصدّر الكبير (٥٠>٤٠)؛ بالمعدّل يتصدّر الصغير (٢٠>٥) — عكس الترتيبين.
    """
    org = db.session.get(Org, seeded["org_id"])
    big = _team(org.id, "سرب كبير", "BIG")
    small = _team(org.id, "سرب صغير", "SML")
    for i in range(10):
        uid = _pilot(org.id, f"عضو كبير {i}", f"9{i:03d}", big.id)
        _event(org.id, uid, "5.00", WEEK_START + timedelta(hours=1))
    for i in range(2):
        uid = _pilot(org.id, f"عضو صغير {i}", f"8{i:03d}", small.id)
        _event(org.id, uid, "20.00", WEEK_START + timedelta(hours=1))
    db.session.commit()

    board = standings.teams_board(org, now=NOW)
    names = [t["team"] for t in board]
    assert names.index("سرب صغير") < names.index("سرب كبير")
    small_row = next(t for t in board if t["team"] == "سرب صغير")
    big_row = next(t for t in board if t["team"] == "سرب كبير")
    assert small_row["avg_hours"] == Decimal("20.00")
    assert big_row["avg_hours"] == Decimal("5.00")


# ═══ ق-٨١ — فكّ التعادل بـcode، ومعروض دائمًا ═══


def test_teams_board_tie_break_by_code(client, seeded):
    """@covers ق-٨١ — تعادل تامّ (١٠ ساعات لكلّ سرب)؛ AAA يسبق ZZZ."""
    org = db.session.get(Org, seeded["org_id"])
    z = _team(org.id, "سرب ن", "ZZZ")
    a = _team(org.id, "سرب أ", "AAA")
    uid_z = _pilot(org.id, "طيّار ن", "7001", z.id)
    uid_a = _pilot(org.id, "طيّار أ", "7002", a.id)
    _event(org.id, uid_z, "10.00", WEEK_START + timedelta(hours=1))
    _event(org.id, uid_a, "10.00", WEEK_START + timedelta(hours=1))
    db.session.commit()

    board = standings.teams_board(org, now=NOW)
    codes = [t["code"] for t in board]
    assert codes.index("AAA") < codes.index("ZZZ")


def test_teams_board_exposes_code_field(client, seeded):
    """@covers ق-٨١ — «معلَن في الواجهة» يشترط ظهور الحقل في العقد نفسه."""
    org = db.session.get(Org, seeded["org_id"])
    board = standings.teams_board(org, now=NOW)
    assert board[0]["code"] == "TST"


# ═══ ق-٨٢ — الجاهزية المجمَّعة ═══


def test_teams_board_readiness_counts(client, seeded):
    """
    @covers ق-٨٢ — عضو حديث النشاط طائر، وآخر متأخّر ١٤ يومًا+ أرضيّ.
    ثلاثة أعضاء لا اثنان **عمدًا**: ٢ طائر + ١ أرضي غير متناظر — مبادلةُ
    الشرطين (طائر⇔أرضي) في مخالفة عدائية على تعادلٍ ١/١ كانت ستمرّ خطأً.
    """
    org = db.session.get(Org, seeded["org_id"])
    flying_uid = seeded["users"]["1001"]
    also_flying_uid = seeded["users"]["1002"]
    grounded_uid = _pilot(org.id, "طيّار ثالث", "6999", seeded["team_id"])
    _event(org.id, flying_uid, "1.00", NOW - timedelta(days=1))
    _event(org.id, also_flying_uid, "1.00", NOW - timedelta(days=2))
    _event(org.id, grounded_uid, "1.00", NOW - timedelta(days=20))
    db.session.commit()

    board = standings.teams_board(org, now=NOW)
    row = board[0]
    assert row["readiness"] == {"flying": 2, "grounded": 1}


# ═══ ق-٨٤ · ق-٨٥ — التشكيل محكوم بف-١ ═══


def test_formation_team_scope_shows_full_names_including_grounded(client, seeded):
    """@covers ق-٨٤"""
    org = db.session.get(Org, seeded["org_id"])
    flying_uid = seeded["users"]["1001"]
    grounded_uid = seeded["users"]["1002"]
    _event(org.id, flying_uid, "1.00", NOW - timedelta(days=1))
    _event(org.id, grounded_uid, "1.00", NOW - timedelta(days=20))
    db.session.commit()

    scene = standings.formation(org, flying_uid, "team", now=NOW)
    names = {a["name"] for a in scene["aircraft"]}
    assert names == {"طالب أول", "طالب ثانٍ"}
    grounded_row = next(a for a in scene["aircraft"] if a["name"] == "طالب ثانٍ")
    assert grounded_row["grounded"] is True


def test_formation_general_scope_hides_grounded_name(client, seeded):
    """@covers ق-٨٥ — إنجاز فقط لا اسم للساقط."""
    org = db.session.get(Org, seeded["org_id"])
    flying_uid = seeded["users"]["1001"]
    grounded_uid = seeded["users"]["1002"]
    _event(org.id, flying_uid, "1.00", NOW - timedelta(days=1))
    _event(org.id, grounded_uid, "1.00", NOW - timedelta(days=20))
    db.session.commit()

    scene = standings.formation(org, flying_uid, "general", now=NOW)
    grounded_row = next(a for a in scene["aircraft"] if a["grounded"] is True)
    assert grounded_row["name"] is None
    flying_row = next(a for a in scene["aircraft"] if a["grounded"] is False)
    assert flying_row["name"] == "طالب أول"


def test_formation_team_scope_without_membership_is_empty_not_error(client, seeded):
    """@covers ق-٩٣ — حالة مصمَّمة (نمط `team: null` في `GET /me/deck`)."""
    org = db.session.get(Org, seeded["org_id"])
    orphan = User(org_id=org.id, full_name="بلا سرب", student_no="6001", pin_hash=hash_pin("1234"))
    db.session.add(orphan)
    db.session.commit()

    scene = standings.formation(org, orphan.id, "team", now=NOW)
    assert scene == {"scope": "team", "aircraft": []}


# ═══ ق-٨٦ · ق-٨٧ — الحجم تراكميّ، والنسبة جاهزة ═══


def test_formation_size_is_cumulative_not_weekly(client, seeded):
    """@covers ق-٨٦ — عكس `pilots_board` تمامًا: حدث الأسبوع الماضي يُحتسب هنا."""
    org = db.session.get(Org, seeded["org_id"])
    uid = seeded["users"]["1001"]
    _event(org.id, uid, "50.00", WEEK_START - timedelta(days=30))
    db.session.commit()

    scene = standings.formation(org, uid, "team", now=NOW)
    row = next(a for a in scene["aircraft"] if a["name"] == "طالب أول")
    assert row["size"] == Decimal("50.00")


def test_formation_size_pct_is_relative_to_largest(client, seeded):
    """@covers ق-٨٧ — الأكبر = ١٠٠، والآخر نصفه = ٥٠."""
    org = db.session.get(Org, seeded["org_id"])
    uid1 = seeded["users"]["1001"]
    uid2 = seeded["users"]["1002"]
    _event(org.id, uid1, "100.00", NOW - timedelta(days=1))
    _event(org.id, uid2, "50.00", NOW - timedelta(days=1))
    db.session.commit()

    scene = standings.formation(org, uid1, "team", now=NOW)
    row1 = next(a for a in scene["aircraft"] if a["name"] == "طالب أول")
    row2 = next(a for a in scene["aircraft"] if a["name"] == "طالب ثانٍ")
    assert row1["size_pct"] == 100
    assert row2["size_pct"] == 50


# ═══ ق-٨٨ — rank_in_org موصول بـ`/me/deck` ═══


def test_deck_rank_in_org_matches_teams_board_position(client, seeded):
    """@covers ق-٨٨"""
    org = db.session.get(Org, seeded["org_id"])
    other = _team(org.id, "سرب أفضل", "AAA")
    uid = _pilot(org.id, "طيّار متفوّق", "5001", other.id)
    _event(org.id, uid, "999.00", NOW - timedelta(hours=1))
    db.session.commit()

    assert standings.team_rank(org, other.id, now=NOW) == 1
    assert standings.team_rank(org, seeded["team_id"], now=NOW) == 2


# ═══ ق-٨٩ · ق-٩٠ — تخويل ومدخلات ═══


def test_boards_require_login(client, seeded):
    """@covers ق-٨٩ — شاشة طيّار: بلا كوكي ⇒ ٤٠١ على المسارات الثلاثة."""
    assert client.get(PILOTS).status_code == 401
    assert client.get(TEAMS).status_code == 401
    assert client.get(FORMATION).status_code == 401


def test_pilot_can_read_boards_without_admin_role(client, seeded):
    """@covers ق-٨٩ — الحدّ الآخر: طيّار عاديّ لا يُرفض."""
    _login(client)
    assert client.get(PILOTS).status_code == 200
    assert client.get(TEAMS).status_code == 200
    assert client.get(FORMATION).status_code == 200


def test_formation_invalid_scope_is_422(client, seeded):
    """@covers ق-٩٠ — لا ٥٠٠ ولا تجاهل صامت."""
    _login(client)
    r = client.get(f"{FORMATION}?scope=bogus")
    assert r.status_code == 422
