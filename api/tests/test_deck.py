"""
`GET /me/deck` — المسار الكامل: أحداث القاعدة → المحرّك → حالة مشتقّة → ردّ.

**بلا محاكاة.** كل اختبار هنا يُلحق أحداثًا حقيقية عبر `ledger`، ويقرأ الردّ
عبر تطبيق Flask حقيقي. اختبارٌ يزرع الساعات جاهزةً يثبت أن الصياغة صحيحة، لا
أن الرقم مشتقّ — والاشتقاق هو المنتج.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.extensions import db
from app.models import Org
from app.rules.engine import Achievement, ruleset_at
from app.services import ledger

ORIGIN = {"Origin": "http://localhost:5173"}
CREDS = {"student_no": "1001", "pin": "1234"}
DECK = "/api/me/deck"


def _achieve(org_id, user_id, pages, days_ago=1, mastery="mastered", activity="memorize"):
    """
    الإنجاز يمرّ بالمحرّك — لا `delta` مكتوبة يدويًّا.

    هذا ما يجعل الاختبار يغطّي السلسلة كلّها: لو انكسر اختيار الإصدار أو حساب
    المضاعف، تكشفه أرقام البطاقة لا اختبار المحرّك وحده.
    """
    at = datetime.now(UTC) - timedelta(days=days_ago)
    ach = Achievement(
        user_id=user_id,
        occurred_at=at,
        activity_type=activity,
        quantity=Decimal(pages),
        mastery=mastery,
    )
    hours = ruleset_at(org_id, at).hours_for(ach)
    ledger.append(
        [
            ledger.EventSpec(
                org_id=org_id, kind="quran", delta=hours, user_id=user_id, occurred_at=at
            )
        ]
    )
    return hours


def _auth(client):
    client.post("/api/auth/login", json=CREDS, headers=ORIGIN)


# ═══ المسار الكامل — أهمّ اختبار في الملفّ ═══


def test_full_path_from_events_through_engine_to_response(client, seeded):
    """
    @covers ق-٥

    ١٠٠ صفحة × ٢.٥ (وزن اليوم) × ٢.٠ (متقن) = ٥٠٠ ساعة.

    السلسلة كلّها في تأكيد واحد: الحدث في القاعدة، والوزن من الإصدار الساري
    وقت وقوعه، والمضاعف من نفس الإصدار، والمجموع من `SUM(delta)`، والرتبة من
    `rank_thresholds`، والتقدّم داخل الشريحة.
    """
    hours = _achieve(seeded["org_id"], seeded["users"]["1001"], 100)
    assert hours == Decimal("500.00")

    _auth(client)
    body = client.get(DECK).json

    assert body["hours"] == "500.00"
    assert body["rank"] == {"name": "طيار أول", "tier": 2}  # ٤٠٠ ≤ ٥٠٠ < ٩٠٠
    assert body["next_rank"]["name"] == "رائد سرب"
    assert body["next_rank"]["at_hours"] == "900.00"
    # داخل الشريحة: (٥٠٠−٤٠٠)/(٩٠٠−٤٠٠) = ٢٠٪ — لا ٥٥.٦٪ المطلقة.
    assert body["next_rank"]["progress_pct"] == 20.0
    assert body["next_rank"]["remaining"] == "400.00"


def test_hours_are_summed_from_events_not_stored(client, seeded):
    """رصيدان يُجمعان، وتصحيحٌ سالب يُخصم — بلا عمود رصيد في أي مكان."""
    org_id, uid = seeded["org_id"], seeded["users"]["1001"]
    _achieve(org_id, uid, 100)
    first = ledger.append(
        [
            ledger.EventSpec(
                org_id=org_id,
                kind="quran",
                delta=Decimal("100.00"),
                user_id=uid,
                occurred_at=datetime.now(UTC),
            )
        ]
    )[0]
    ledger.reverse(first, "خطأ في التصدير", actor_id=uid)

    _auth(client)
    assert client.get(DECK).json["hours"] == "500.00"


# ═══ ق-١٠ · ٩ — القواعد التاريخية ═══


def test_historical_event_uses_historical_rules_in_the_deck(client, seeded):
    """
    @covers ق-١٠

    حدثٌ قبل الإصدار الجديد: ١٠٠ × ١.٠ × ١.٥ = ١٥٠ لا ٥٠٠.

    لو اختار المحرّك `now()` لظهر الطالب في رتبة لم يبلغها — والخطأ يظهر **في
    البطاقة** لا في المحرّك، وهذا ما يجعل اختباره هنا ضروريًّا.
    """
    days = (datetime.now(UTC) - datetime(2025, 3, 1, tzinfo=UTC)).days
    _achieve(seeded["org_id"], seeded["users"]["1001"], 100, days_ago=days)

    _auth(client)
    body = client.get(DECK).json
    assert body["hours"] == "150.00"
    assert body["rank"]["name"] == "طيار"  # ٠ ≤ ١٥٠ < ٤٠٠


def test_current_event_uses_current_rules(client, seeded):
    _achieve(seeded["org_id"], seeded["users"]["1001"], 100, days_ago=1)
    _auth(client)
    assert client.get(DECK).json["hours"] == "500.00"


# ═══ ق-٦ — الحالة الفارغة ═══


def test_student_with_no_events_gets_designed_empty_state(client, seeded):
    """@covers ق-٦"""
    _auth(client)
    body = client.get(DECK).json

    assert body["hours"] == "0.00"
    assert body["rank"]["tier"] == 1
    assert body["next_rank"]["progress_pct"] == 0.0
    assert body["flight"] == {"grounded": False, "last_activity_on": None}


# ═══ ق-٧ — أعلى رتبة ═══


def test_max_rank_returns_null_next_rank(client, seeded):
    """@covers ق-٧ — `null` لا شريط ممتلئ: شريط ١٠٠٪ يوحي بأن هناك ما بعده."""
    _achieve(seeded["org_id"], seeded["users"]["1001"], 400)  # ٢٠٠٠ ساعة
    _auth(client)
    body = client.get(DECK).json

    assert body["hours"] == "2000.00"
    assert body["rank"] == {"name": "قائد", "tier": 4}
    assert body["next_rank"] is None


# ═══ حدود العتبات ═══


def test_exactly_at_threshold_is_the_higher_rank(client, seeded):
    """
    ٤٠٠ بالضبط ⇒ «طيار أول» لا «طيار». الحدّ شامل، والغموض هنا يعني طالبين
    برصيد متطابق في رتبتين مختلفتين بحسب ترتيب الصفوف.
    """
    _achieve(seeded["org_id"], seeded["users"]["1001"], 80)  # ٤٠٠.٠٠
    _auth(client)
    body = client.get(DECK).json
    assert body["hours"] == "400.00"
    assert body["rank"]["tier"] == 2
    assert body["next_rank"]["progress_pct"] == 0.0


def test_one_cent_below_threshold_stays_in_lower_rank(client, seeded):
    org_id, uid = seeded["org_id"], seeded["users"]["1001"]
    ledger.append(
        [
            ledger.EventSpec(
                org_id=org_id,
                kind="quran",
                delta=Decimal("399.99"),
                user_id=uid,
                occurred_at=datetime.now(UTC),
            )
        ]
    )
    _auth(client)
    assert client.get(DECK).json["rank"]["tier"] == 1


def test_negative_balance_does_not_break_the_card(client, seeded):
    """تصحيحٌ يتجاوز الرصيد: `progress_pct` صفر لا سالب يقلب الشريط."""
    org_id, uid = seeded["org_id"], seeded["users"]["1001"]
    e = ledger.append(
        [
            ledger.EventSpec(
                org_id=org_id,
                kind="quran",
                delta=Decimal("10.00"),
                user_id=uid,
                occurred_at=datetime.now(UTC),
            )
        ]
    )[0]
    ledger.reverse(e, "خطأ", actor_id=uid)
    ledger.reverse(e, "خطأ مكرّر", actor_id=uid)

    _auth(client)
    body = client.get(DECK).json
    assert body["hours"] == "-10.00"
    assert body["rank"]["tier"] == 1
    assert body["next_rank"]["progress_pct"] == 0.0


# ═══ ق-٨ — حالة الطيران ═══


def test_recent_activity_is_flying(client, seeded):
    _achieve(seeded["org_id"], seeded["users"]["1001"], 10, days_ago=3)
    _auth(client)
    assert client.get(DECK).json["flight"]["grounded"] is False


def test_old_activity_is_grounded(client, seeded):
    """@covers ق-٨"""
    _achieve(seeded["org_id"], seeded["users"]["1001"], 10, days_ago=30)
    _auth(client)
    body = client.get(DECK).json
    assert body["flight"]["grounded"] is True
    assert body["flight"]["last_activity_on"] is not None


def test_grounded_boundary_uses_org_setting_not_a_constant(client, seeded):
    """
    العتبة عمود إعداد (ف-٢): تغييرها إلى يومين يجعل نشاط الأمس طائرًا ونشاط
    أربعة أيام أرضيًّا — **صفٌّ لا نشر**.
    """
    org = db.session.get(Org, seeded["org_id"])
    org.grounded_after_days = 2
    db.session.commit()

    _achieve(seeded["org_id"], seeded["users"]["1001"], 10, days_ago=4)
    _auth(client)
    assert client.get(DECK).json["flight"]["grounded"] is True


def test_attendance_alone_does_not_lift_the_plane(client, seeded):
    """
    الحالة تُحسب من القرآن والقراءة معًا — لا من الحضور. حضورُ حصّةٍ بلا تسميع
    ولا قراءة ليس النشاط الذي تقيسه هذه الحالة.
    """
    org_id, uid = seeded["org_id"], seeded["users"]["1001"]
    old = datetime.now(UTC) - timedelta(days=30)
    ledger.append(
        [
            ledger.EventSpec(
                org_id=org_id, kind="quran", delta=Decimal("10"), user_id=uid, occurred_at=old
            )
        ]
    )
    ledger.append(
        [
            ledger.EventSpec(
                org_id=org_id,
                kind="attendance",
                delta=Decimal("3"),
                user_id=uid,
                occurred_at=datetime.now(UTC),
            )
        ]
    )
    _auth(client)
    assert client.get(DECK).json["flight"]["grounded"] is True


def test_grounded_is_not_stored_on_the_user_row(client, seeded):
    """ث-١٤ من زاوية الـAPI: لا مصدر ثانٍ يمكن أن يفترق عن الحساب."""
    cols = db.session.execute(
        db.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='users' AND column_name='grounded'"
        )
    ).all()
    assert cols == []


# ═══ التخويل — الهوية من الجلسة لا من الطلب ═══


def test_unauthenticated_request_is_401(client, seeded):
    assert client.get(DECK).status_code == 401


def test_deck_belongs_to_the_session_owner(client, seeded):
    """الطالبان يرصدان رصيدين مختلفين، وكلٌّ يرى رصيده هو."""
    _achieve(seeded["org_id"], seeded["users"]["1001"], 100)
    _achieve(seeded["org_id"], seeded["users"]["1002"], 20)

    _auth(client)
    assert client.get(DECK).json["hours"] == "500.00"

    client.post("/api/auth/logout", headers=ORIGIN)
    client.post("/api/auth/login", json={"student_no": "1002", "pin": "1234"}, headers=ORIGIN)
    assert client.get(DECK).json["hours"] == "100.00"


def test_client_cannot_target_another_student(client, seeded):
    """
    لا معرّف في المسار ولا في الاستعلام ولا في الجسم — **فلا يوجد ما يُتلاعب
    به أصلًا**. وهذا أقوى من التحقّق من الملكية: يُلغي المسارَ الذي يحتاج تحقّقًا.
    """
    _achieve(seeded["org_id"], seeded["users"]["1001"], 100)
    _achieve(seeded["org_id"], seeded["users"]["1002"], 20)
    _auth(client)

    victim = seeded["users"]["1002"]
    for attempt in (f"?user_id={victim}", f"?student_no=1002&org_id=1&id={victim}"):
        assert client.get(DECK + attempt).json["hours"] == "500.00", attempt


def test_session_of_deleted_user_yields_401_not_a_crash(client, seeded):
    """حالة حافّة نادرة يجب أن تُردّ لا أن تُسقط الخادم."""
    _auth(client)
    db.session.execute(db.text("UPDATE users SET is_active = false WHERE student_no='1001'"))
    db.session.commit()
    assert client.get(DECK).status_code == 401


# ═══ العقد — API.md §٤ ═══


def test_response_shape_matches_the_contract_exactly(client, seeded):
    _achieve(seeded["org_id"], seeded["users"]["1001"], 100)
    _auth(client)
    body = client.get(DECK).json

    assert set(body) == {"rank", "hours", "next_rank", "flight", "team"}
    assert set(body["rank"]) == {"name", "tier"}
    assert set(body["next_rank"]) == {"name", "at_hours", "progress_pct", "remaining"}
    assert set(body["flight"]) == {"grounded", "last_activity_on"}
    assert set(body["team"]) == {"name", "rank_in_org"}


def test_decimals_are_strings_and_percentage_is_a_number(client, seeded):
    """
    الساعات نصّ عشري (§١): `float` في JSON يفقد الدقّة في جافاسكربت، والساعات
    تُقارَن بعتبات. والنسبة رقم — ليست مبلغًا ولا تُقارَن بشيء.
    """
    _achieve(seeded["org_id"], seeded["users"]["1001"], 100)
    _auth(client)
    body = client.get(DECK).json

    assert isinstance(body["hours"], str)
    assert isinstance(body["next_rank"]["at_hours"], str)
    assert isinstance(body["next_rank"]["remaining"], str)
    assert isinstance(body["next_rank"]["progress_pct"], float)
    assert body["hours"].count(".") == 1 and len(body["hours"].split(".")[1]) == 2


def test_rank_in_org_matches_boards_teams(client, seeded):
    """
    و-٩ب — FR-051: `rank_in_org` يساوي موضع السرب في `GET /boards/teams`
    نفسه، لا حسابًا موازيًا. سربٌ واحد في البذرة ⇒ رتبته ١ حتمًا.
    """
    _auth(client)
    assert client.get(DECK).json["team"]["rank_in_org"] == 1


def test_team_is_null_when_membership_is_absent(client, seeded):
    """منقولٌ بين الأسراب يرى بطاقته لا شاشة عطل — `SCOPE.md` ط-٢."""
    _auth(client)
    db.session.execute(db.text("DELETE FROM memberships"))
    db.session.commit()
    body = client.get(DECK).json
    assert body["team"] is None
    assert body["hours"] == "0.00"


def test_internal_errors_are_not_exposed(client, seeded, app, monkeypatch):
    """
    استثناءٌ **غير متوقَّع** لا يصل نصُّه ولا أثرُ تنفيذه إلى المستخدم —
    تفصيلٌ داخليّ في ردّ خطأ خريطةٌ للمهاجم (`API.md §١`).

    **وبُدِّلت وسيلةُ هذا الاختبار في و-٢٢، لا قصدُه.** كان يستعمل «سُلّم رتب
    مفقود» وسيلةً، ويؤكّد أن الردّ ٥٠٠ وأن «سُلّم رتب» **لا** يظهر — أي أنه
    **كان يُقنّن عطلًا سلوكًا مقصودًا**: ذاك عطلُ **إعداد** يملك المشرف
    إصلاحه، فإخفاؤه خلف «حدث خلل في الخادم» يُرسله يبحث في السجلّات عن خطأٍ
    ليس فيها. صار ٤٢٢ برسالةٍ صريحة (ق-٢٩٢).

    فالوسيلةُ الآن استثناءٌ **حقيقيُّ المفاجأة** يُحقَن في الخدمة — وهو ما
    كان يُقصَد قياسه أصلًا.
    """

    def boom(*_a, **_k):
        raise RuntimeError('تفصيلٌ داخليّ: relation "point_events" لا يمكن قراءتها')

    monkeypatch.setattr("app.services.deck.build", boom)
    _auth(client)

    # وضع الاختبار يمرّر الاستثناء افتراضيًّا؛ نقيس سلوك الإنتاج الفعلي.
    app.config["PROPAGATE_EXCEPTIONS"] = False
    r = client.get(DECK)

    assert r.status_code == 500
    body = r.get_data(as_text=True)
    assert "Traceback" not in body
    assert "point_events" not in body
    assert "تفصيلٌ داخليّ" not in body
    assert r.json["message"] == "حدث خلل في الخادم. حاول بعد قليل."


# ═══ و-٢٢ — جمعيةٌ بلا سُلّم رتب: ٤٢٢ لا ٥٠٠ (ق-٢٩٢) ═══


def test_org_without_a_rank_ladder_gets_a_clear_422_not_a_500(client, seeded):
    """
    **كان `deck.py` الخدمةَ الوحيدة التي ترفع `ValueError` عاريًا**،
    و`routes/me.py` ينادي `build` بلا `try` — فيلتقطه معالجُ التطبيق العامّ
    ويردّ **٥٠٠ بـ«حدث خلل في الخادم»** على الشاشة الرئيسية للطالب.

    وعطلُ إعدادٍ يُقرَأ عطلَ خادم يُرسل المشرفَ يبحث في السجلّات عن خطأٍ
    ليس فيها — والرسالة تقول الآن ما الناقص وأين يُضبَط.

    ومُقاسٌ حيًّا قبل الإصلاح: `GET /me/deck → 500`. وبعده: `422`.

    @covers ق-٢٩٢
    """
    db.session.execute(db.text("DELETE FROM rank_thresholds"))
    db.session.commit()
    client.post("/api/auth/login", json=CREDS, headers=ORIGIN)

    r = client.get(DECK, headers=ORIGIN)
    assert r.status_code == 422
    assert "سُلّم رتب" in r.get_json()["message"]
    # ولا رسالةَ الخادم العامّة — تلك تعني أن الاستثناء أفلت.
    assert "حدث خلل" not in r.get_json()["message"]
