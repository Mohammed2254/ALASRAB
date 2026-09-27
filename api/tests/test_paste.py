"""
استيراد راصد — و-٥ · FR-030..034/040.

يستعمل عيّنتَي راصد الحقيقيّتين في `fixtures/` حيث يُطلب ذلك صراحةً (مستهدف=٠،
تجاوز ٤٠٦.٥٪، استبعاد التذييل، مسافة زائدة في الاسم)، وملفّات مُركَّبة بمساعد
`_csv_bytes` لبقية المعايير المعزولة. بلا محاكاة: تطبيق Flask حقيقي وقاعدة
حقيقية.
"""

import csv
import io
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from app.extensions import db
from app.ingest import rasd
from app.models import (
    AuditEntry,
    Membership,
    PointEvent,
    RawRow,
    User,
    Weight,
)

ORIGIN = {"Origin": "http://localhost:5173"}
PIN = "1234"
PREVIEW = "/api/admin/paste/preview"
COMMIT = "/api/admin/paste/commit"

FIXTURES = Path(__file__).parent / "fixtures"
SPARSE = FIXTURES / "تقرير_الإنجاز_جميع_الحلقات_١٤٤٨-٠٣-٢٢.csv"
RICH = FIXTURES / "تقرير_الإنجاز_جميع_الحلقات_١٤٤٨-٠٣-٢٥.csv"

# ٢٠٢٦-٠٨-٠٢ أحد — ماضٍ بأمان نسبةً إلى تاريخ تشغيل هذه الاختبارات (٢٠٢٦-٠٩+).
OCCURRED_ON = date(2026, 8, 2)


def _login(client, student_no="1001"):
    return client.post(
        "/api/auth/login", json={"student_no": student_no, "pin": PIN}, headers=ORIGIN
    )


def _make_admin(user_id):
    m = db.session.scalar(select(Membership).where(Membership.user_id == user_id))
    m.role = "admin"
    db.session.commit()


def _add_weight(seeded, activity_type, hours="1.00"):
    """
    إصدارات `conftest.seeded` تحمل `memorize`/`quran_progress`/`reading` وحدها —
    فئات راصد والحضور تُضاف محليًّا هنا بأوزانٍ صريحة، فيبقى كل اختبار يعلن
    الوزن الذي يحتسب به (بخلاف `seed.py` التشغيليّ الذي يبذرها بقيمٍ أوّلية).
    """
    db.session.add(
        Weight(
            version_id=seeded["versions"]["new"],
            activity_type=activity_type,
            hours_per_unit=Decimal(hours),
        )
    )
    db.session.commit()


def _add_all_weights(seeded, quran_hours="1.00", attendance_hours="3.00"):
    for cat in ("quran_hifz", "quran_thabat", "quran_muraja3a"):
        _add_weight(seeded, cat, quran_hours)
    _add_weight(seeded, "attendance", attendance_hours)


def _add_student(seeded, full_name, student_no):
    u = User(org_id=seeded["org_id"], full_name=full_name, student_no=student_no, pin_hash="x")
    db.session.add(u)
    db.session.flush()
    db.session.add(
        Membership(org_id=seeded["org_id"], user_id=u.id, team_id=seeded["team_id"], role="pilot")
    )
    db.session.commit()
    return u.id


def _balance(user_id):
    return db.session.scalar(
        select(db.func.coalesce(db.func.sum(PointEvent.delta), 0)).where(
            PointEvent.user_id == user_id
        )
    )


def _row(name, **overrides):
    base = dict.fromkeys(rasd.CANONICAL_HEADER, "0")
    base[rasd.STUDENT_COLUMN] = name
    base.update(overrides)
    return base


def _csv_bytes(rows: list[dict], header: list[str] | None = None) -> bytes:
    header = header or rasd.CANONICAL_HEADER
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return ("﻿" + buf.getvalue()).encode("utf-8")


def _upload(client, path, file_bytes, occurred_on=OCCURRED_ON, filename="rasd.csv", **extra_form):
    data = {
        "file": (io.BytesIO(file_bytes), filename),
        "occurred_on": occurred_on.isoformat(),
        **extra_form,
    }
    return client.post(path, data=data, content_type="multipart/form-data", headers=ORIGIN)


# ═══ ق-١٧٥ — ترويسة ناقصة/بترتيب مختلف ⇒ رفض صريح ═══


def test_missing_header_column_is_rejected(client, seeded):
    """@covers ق-١٧٥"""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    bad_header = [c for c in rasd.CANONICAL_HEADER if c != "الحضور"]
    body = _csv_bytes([_row("طالب", **{})], header=bad_header)
    r = _upload(client, PREVIEW, body)
    assert r.status_code == 422
    assert "ترويسة" in r.json["message"]


def test_reordered_header_is_rejected(client, seeded):
    """@covers ق-١٧٥ — لا يُخمَّن ترتيب الأعمدة حتى لو تطابقت الأسماء."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    swapped = list(rasd.CANONICAL_HEADER)
    swapped[1], swapped[2] = swapped[2], swapped[1]  # تبديل «أيام التسميع» و«الحضور»
    body = _csv_bytes([_row("طالب")], header=swapped)
    r = _upload(client, PREVIEW, body)
    assert r.status_code == 422


def test_valid_header_is_accepted(client, seeded):
    """@covers ق-١٧٥ — الحدّ الآخر: القيد ليس مفرطًا."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    body = _csv_bytes([_row("طالب واحد")])
    r = _upload(client, PREVIEW, body)
    assert r.status_code == 200


# ═══ ق-١٧٦ — استبعاد صفّي التذييل في كلا الملفّين الحقيقيّين ═══


def test_footer_rows_excluded_in_both_real_files(client, seeded):
    """@covers ق-١٧٦"""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    for fixture, expected_count in [(SPARSE, 2), (RICH, 24)]:
        r = _upload(client, PREVIEW, fixture.read_bytes())
        assert r.status_code == 200
        names = {row["name"] for row in r.json["rows"]}
        assert "الإجمالي" not in names
        assert "المتوسط" not in names
        assert len(r.json["rows"]) == expected_count


# ═══ ق-١٧٧ — BOM يُزال، أسطر LF تُقرأ ═══


def test_bom_and_lf_only_lines_parse_correctly(client, seeded):
    """@covers ق-١٧٧"""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    raw_bytes = RICH.read_bytes()
    assert raw_bytes[:3] == b"\xef\xbb\xbf"  # تأكيد أن العيّنة تحمل BOM فعلًا
    assert b"\r\n" not in raw_bytes  # وأسطرها LF فقط فعلًا
    r = _upload(client, PREVIEW, raw_bytes)
    assert r.status_code == 200
    first_name = r.json["rows"][0]["name"]
    assert not first_name.startswith("﻿")
    assert first_name == "ابراهيم الشميري"


# ═══ ق-١٧٨ — مسافات زائدة تُقصّ فتُطابَق تامًّا (الاسم الحقيقيّ) ═══


def test_trailing_whitespace_name_matches_after_trim(client, seeded):
    """@covers ق-١٧٨ — «صالح الجريش» الحقيقيّ في كلا الملفّين بمسافة زائدة."""
    _add_student(seeded, "صالح الجريش", "9001")
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = _upload(client, PREVIEW, RICH.read_bytes())
    assert r.status_code == 200
    # الاسم المُطبَّع مقصوصٌ دائمًا (`rasd.parse` يقصّه) — المسافة الزائدة
    # تبقى في `raw_rows.payload` وحده للأرشفة، لا في اسم المطابقة.
    row = next(row for row in r.json["rows"] if row["name"] == "صالح الجريش")
    assert row["match_status"] == "matched"


# ═══ ق-١٧٩ — اسم بلا تطابق ⇒ حلّ يدويّ، لا تخمين ═══


def test_unmatched_name_is_flagged_not_guessed(client, seeded):
    """@covers ق-١٧٩"""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = _upload(client, PREVIEW, _csv_bytes([_row("لا أحد بهذا الاسم")]))
    assert r.status_code == 200
    row = r.json["rows"][0]
    assert row["match_status"] == "unmatched"
    assert row["user_id"] is None


def test_unmatched_name_creates_no_event_on_commit(client, seeded):
    """@covers ق-١٧٩ — الامتداد الطبيعي: الالتزام لا يخترع مطابقة."""
    _add_all_weights(seeded)
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = _upload(client, COMMIT, _csv_bytes([_row("لا أحد بهذا الاسم", **{"الحضور": "2"})]))
    assert r.status_code == 201
    assert r.json["rows"][0]["status"] == "unmatched"
    assert r.json["events_created"] == 0


# ═══ ق-١٨٠ — تطابق متعدّد ⇒ يُعامَل كعدم تطابق ═══


def test_ambiguous_name_is_treated_as_unmatched(client, seeded):
    """@covers ق-١٨٠ — طالبان بنفس الاسم بعد القصّ."""
    _add_student(seeded, "محمد أحمد", "9001")
    _add_student(seeded, "محمد أحمد", "9002")
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = _upload(client, PREVIEW, _csv_bytes([_row("محمد أحمد")]))
    row = r.json["rows"][0]
    assert row["match_status"] == "ambiguous"
    assert len(row["candidate_ids"]) == 2


# ═══ ق-١٨١ — مستهدف=٠ ⇒ نسبة=٠ صراحةً (الحالة الحقيقيّة في العيّنة الصغيرة) ═══


def test_zero_target_yields_zero_percent_not_error(client, seeded):
    """@covers ق-١٨١ — كلا صفّي العيّنة الصغيرة الحقيقيّة مستهدفهما صفر بالكامل."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = _upload(client, PREVIEW, SPARSE.read_bytes())
    assert r.status_code == 200
    for row in r.json["rows"]:
        assert row["percentages"] == {"hifz": "0.0", "thabat": "0.0", "muraja3a": "0.0"}


def test_zero_target_row_commits_without_crashing(client, seeded):
    """@covers ق-١٨١ — الحدّ الآخر: الالتزام لا يسقط بخطأ قسمة على صفر."""
    _add_student(seeded, "ثابت المقحم", "9001")
    _add_all_weights(seeded)
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = _upload(client, COMMIT, SPARSE.read_bytes())
    assert r.status_code == 201
    row = next(x for x in r.json["rows"] if x["name"] == "ثابت المقحم")
    assert row["categories"]["hifz"]["hours"] == "0.00"


# ═══ ق-١٩٦ — تحصيل صفريّ حقيقيّ لا يُنشئ حدثًا (نمط `services/entry.record`) ═══


def test_zero_achievement_creates_no_point_event(client, seeded):
    """
    @covers ق-١٩٦ — «صالح الجريش» في العيّنة الصغيرة الحقيقيّة: صفر في كل شيء
    **بما فيها الحضور** (خلاف «ثابت المقحم» بنفس الملفّ، حضوره=١).
    """
    uid = _add_student(seeded, "صالح الجريش", "9001")
    _add_all_weights(seeded)
    _make_admin(seeded["users"]["1001"])
    _login(client)

    r = _upload(client, COMMIT, SPARSE.read_bytes())
    assert r.status_code == 201
    row = next(x for x in r.json["rows"] if x["name"] == "صالح الجريش")
    assert all(c["status"] == "skipped_zero" for c in row["categories"].values())
    assert (
        db.session.scalar(select(db.func.count(PointEvent.id)).where(PointEvent.user_id == uid))
        == 0
    )


# ═══ ق-١٨٢ — النسبة داخليّة، عمود «نسبة X» يُتجاهَل ═══


def test_rasd_percentage_column_is_ignored(client, seeded):
    """
    @covers ق-١٨٢ — عمود «نسبة الحفظ» يُصرَّح بقيمة مضلِّلة (٩٩٪) بينما
    مستهدف/منجز الحقيقيّان يفرضان ٥٠٪ — المحسوب داخليًّا هو ما يصل، لا ٩٩.
    """
    _add_student(seeded, "طالب", "9001")
    _add_all_weights(seeded)
    _make_admin(seeded["users"]["1001"])
    _login(client)
    body = _csv_bytes(
        [_row("طالب", **{"مستهدف الحفظ": "10", "منجز الحفظ": "5", "نسبة الحفظ": "99%"})]
    )
    r = _upload(client, PREVIEW, body)
    assert r.json["rows"][0]["percentages"]["hifz"] == "50.0"


# ═══ ق-١٨٣ — تجاوز الهدف لا يُقصَّص (الصفّ الحقيقيّ ٤٠٦.٥٪) ═══


def test_over_100_percent_achievement_is_not_capped(client, seeded):
    """@covers ق-١٨٣ — سلمان الغفيص الحقيقيّ: تثبيت مستهدف=١.٢٣ منجز=٥ ⇒ ٤٠٦.٥٪."""
    _add_student(seeded, "سلمان الغفيص", "9001")
    _add_all_weights(seeded, quran_hours="1.00")
    _make_admin(seeded["users"]["1001"])
    _login(client)

    r = _upload(client, PREVIEW, RICH.read_bytes())
    row = next(x for x in r.json["rows"] if x["name"] == "سلمان الغفيص")
    assert row["percentages"]["thabat"] == "406.5"

    commit = _upload(client, COMMIT, RICH.read_bytes())
    assert commit.status_code == 201
    result_row = next(x for x in commit.json["rows"] if x["name"] == "سلمان الغفيص")
    # وزن ١.٠٠ × نسبة ٤٠٦.٥٠٤٠٦٥٠٤٠٦٥٠٤٠٦... (كامل الدقّة قبل التقريب النهائيّ).
    assert result_row["categories"]["thabat"]["hours"] == "406.50"


# ═══ ق-١٨٤ — وزنٌ مستقلّ لكلّ فئة ═══


def test_each_category_has_independent_weight(client, seeded):
    """@covers ق-١٨٤"""
    _add_student(seeded, "طالب", "9001")
    _add_weight(seeded, "quran_hifz", "1.00")
    _add_weight(seeded, "quran_thabat", "5.00")
    _add_weight(seeded, "quran_muraja3a", "0.10")
    _add_weight(seeded, "attendance", "3.00")
    _make_admin(seeded["users"]["1001"])
    _login(client)

    body = _csv_bytes(
        [
            _row(
                "طالب",
                **{
                    "مستهدف الحفظ": "10",
                    "منجز الحفظ": "10",  # ١٠٠٪
                    "المستهدف تثبيت": "10",
                    "المنجز تثبيت": "10",  # ١٠٠٪
                    "المستهدف مراجعة": "10",
                    "المنجز مراجعة": "10",  # ١٠٠٪
                },
            )
        ]
    )
    r = _upload(client, COMMIT, body)
    cats = r.json["rows"][0]["categories"]
    assert cats["hifz"]["hours"] == "100.00"  # ١٠٠٪ × ١.٠٠
    assert cats["thabat"]["hours"] == "500.00"  # ١٠٠٪ × ٥.٠٠
    assert cats["muraja3a"]["hours"] == "10.00"  # ١٠٠٪ × ٠.١٠


# ═══ ق-١٨٥ — عمود الحضور ⇒ kind='attendance' بوزن الحضور القائم ═══


def test_attendance_column_uses_attendance_kind_and_weight(client, seeded):
    """@covers ق-١٨٥"""
    uid = _add_student(seeded, "طالب", "9001")
    _add_all_weights(seeded, attendance_hours="3.00")
    _make_admin(seeded["users"]["1001"])
    _login(client)

    r = _upload(client, COMMIT, _csv_bytes([_row("طالب", **{"الحضور": "2"})]))
    assert r.status_code == 201
    assert r.json["rows"][0]["categories"]["attendance"]["hours"] == "6.00"  # ٢ × ٣.٠٠

    event = db.session.scalar(
        select(PointEvent).where(PointEvent.user_id == uid, PointEvent.delta == Decimal("6.00"))
    )
    assert event.kind == "attendance"


# ═══ ق-١٨٦ — أيام التسميع لا يُنشئ حدثًا مطلقًا ═══


def test_tasmi3_days_never_creates_an_event(client, seeded):
    """
    @covers ق-١٨٦ — مقارنة رصيد لا تخمين توقيع: نفس الصفّ بقيمتَي «أيام
    التسميع» ٠ و٢ (كل شيء آخر ثابت، بما فيه الحضور=٠) يجب أن يترك **رصيدًا
    متطابقًا وعدد أحداث متطابقًا** — أيّ فرقٍ يعني تسرّبًا إلى المحرّك.
    """
    uid = _add_student(seeded, "طالب صفر", "9001")
    other_uid = _add_student(seeded, "طالب اثنان", "9002")
    _add_all_weights(seeded)
    _make_admin(seeded["users"]["1001"])
    _login(client)

    _upload(
        client,
        COMMIT,
        _csv_bytes(
            [
                _row("طالب صفر", **{"أيام التسميع": "0", "الحضور": "0"}),
                _row("طالب اثنان", **{"أيام التسميع": "2", "الحضور": "0"}),
            ]
        ),
    )
    zero_count = db.session.scalar(
        select(db.func.count(PointEvent.id)).where(PointEvent.user_id == uid)
    )
    two_count = db.session.scalar(
        select(db.func.count(PointEvent.id)).where(PointEvent.user_id == other_uid)
    )
    assert zero_count == two_count  # القيمة صفر أم اثنان — لا فرق في عدد الأحداث.
    assert _balance(uid) == _balance(other_uid) == Decimal("0.00")


# ═══ ق-١٨٧ — raw_rows تُكتب قبل أي حدث، لكل صفّ طالب حقيقيّ ═══


def test_raw_rows_written_for_every_real_student_row(client, seeded):
    """@covers ق-١٨٧ — حتى للأسماء غير المطابَقة، ولكلا الملفّين."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    for fixture, expected_count in [(SPARSE, 2), (RICH, 24)]:
        db.session.execute(db.text("TRUNCATE raw_rows RESTART IDENTITY CASCADE"))
        db.session.commit()
        r = _upload(client, COMMIT, fixture.read_bytes())
        assert r.status_code == 201
        assert db.session.scalar(select(db.func.count(RawRow.id))) == expected_count


def test_raw_rows_written_even_when_no_event_can_be_created(client, seeded):
    """@covers ق-١٨٧ — اسمٌ غير مطابَق: الخام يُحفظ رغم عدم وجود حدث ممكن."""
    _make_admin(seeded["users"]["1001"])
    _login(client)
    r = _upload(client, COMMIT, _csv_bytes([_row("لا أحد بهذا الاسم")]))
    assert r.status_code == 201
    assert db.session.scalar(select(db.func.count(RawRow.id))) == 1


# ═══ ق-١٨٨ — إعادة استيراد نفس الملفّ لنفس التاريخ ⇒ صفر أحداث جديدة ═══


def test_reimporting_identical_file_creates_zero_new_events(client, seeded):
    """@covers ق-١٨٨"""
    uid = _add_student(seeded, "سلمان الغفيص", "9001")
    _add_all_weights(seeded)
    _make_admin(seeded["users"]["1001"])
    _login(client)

    first = _upload(client, COMMIT, RICH.read_bytes())
    assert first.json["events_created"] > 0
    balance_after_first = _balance(uid)

    second = _upload(client, COMMIT, RICH.read_bytes())
    assert second.json["events_created"] == 0
    assert _balance(uid) == balance_after_first


# ═══ ق-١٨٩ — إعادة استيراد ملفّ معدَّل جزئيًّا: الجديد فقط يُلحَق ═══


def test_partially_new_reimport_only_appends_the_new_student(client, seeded):
    """
    @covers ق-١٨٩ — لا تفشل الدفعة كاملةً بسبب تصادم صفّ واحد قائم.

    اسمان مختلفان عمدًا عن مستخدمَي `seeded` الافتراضيَّين («طالب أول»/«طالب
    ثانٍ») — تطابقهما الحرفيّ كان سيجعل الاسم الثاني هنا **متعدّد المطابقة**
    (ق-١٨٠) لا مطابقًا، فيُفسد هذا الاختبار بعينه.
    """
    _add_student(seeded, "زيد الأحمد", "9001")
    _add_student(seeded, "عمر السالم", "9002")
    _add_all_weights(seeded)
    _make_admin(seeded["users"]["1001"])
    _login(client)

    first_batch = _csv_bytes([_row("زيد الأحمد", **{"الحضور": "1"})])
    r1 = _upload(client, COMMIT, first_batch)
    assert r1.json["events_created"] == 1

    second_batch = _csv_bytes(
        [_row("زيد الأحمد", **{"الحضور": "1"}), _row("عمر السالم", **{"الحضور": "1"})]
    )
    r2 = _upload(client, COMMIT, second_batch)
    assert r2.status_code == 201
    first_row = next(x for x in r2.json["rows"] if x["name"] == "زيد الأحمد")
    second_row = next(x for x in r2.json["rows"] if x["name"] == "عمر السالم")
    assert first_row["categories"]["attendance"]["status"] == "already_imported"
    assert second_row["categories"]["attendance"]["status"] == "created"
    assert r2.json["events_created"] == 1


# ═══ ق-١٩٠ — تحذير تكرار (checksum) يظهر ولا يمنع ═══


def test_duplicate_checksum_warns_but_does_not_block(client, seeded):
    """@covers ق-١٩٠"""
    _add_student(seeded, "طالب", "9001")
    _add_all_weights(seeded)
    _make_admin(seeded["users"]["1001"])
    _login(client)

    body = _csv_bytes([_row("طالب", **{"الحضور": "1"})])
    first_preview = _upload(client, PREVIEW, body)
    assert first_preview.json["duplicate_warning"] is False

    _upload(client, COMMIT, body)

    second_preview = _upload(client, PREVIEW, body)
    assert second_preview.json["duplicate_warning"] is True

    second_commit = _upload(client, COMMIT, body)
    assert second_commit.status_code == 201  # لم يُحظَر رغم التحذير


# ═══ ق-١٩١ — المسار السالب الإلزامي ═══


def test_paste_routes_require_admin(client, seeded):
    """@covers ق-١٩١"""
    _login(client)
    body = _csv_bytes([_row("طالب")])
    assert _upload(client, PREVIEW, body).status_code == 403
    assert _upload(client, COMMIT, body).status_code == 403


def test_paste_routes_require_session(client, seeded):
    """@covers ق-١٩١"""
    body = _csv_bytes([_row("طالب")])
    assert _upload(client, PREVIEW, body).status_code == 401
    assert _upload(client, COMMIT, body).status_code == 401


# ═══ ق-١٩٢ — المعاينة بلا كتابة إطلاقًا ═══


def test_preview_writes_nothing(client, seeded):
    """@covers ق-١٩٢"""
    _add_student(seeded, "سلمان الغفيص", "9001")
    _make_admin(seeded["users"]["1001"])
    _login(client)
    _upload(client, PREVIEW, RICH.read_bytes())
    assert db.session.scalar(select(db.func.count(RawRow.id))) == 0
    assert db.session.scalar(select(db.func.count(PointEvent.id))) == 0
    assert db.session.scalar(select(db.func.count(AuditEntry.id))) == 0


# ═══ ق-١٩٣ — تعديل المشرف قبل الاعتماد يُستعمَل ويُسجَّل ═══


def test_admin_value_override_is_used_and_audited(client, seeded):
    """@covers ق-١٩٣"""
    _add_student(seeded, "طالب", "9001")
    _add_all_weights(seeded)
    _make_admin(seeded["users"]["1001"])
    _login(client)

    body = _csv_bytes([_row("طالب", **{"مستهدف الحفظ": "10", "منجز الحفظ": "2"})])
    r = _upload(
        client,
        COMMIT,
        body,
        value_overrides=json.dumps({"طالب": {"hifz_achieved": "8"}}),
    )
    assert r.status_code == 201
    # ٨/١٠×١٠٠ = ٨٠٪ × وزن ١.٠٠ = ٨٠.٠٠ — لا ٢/١٠×١٠٠=٢٠٪ الأصليّة.
    assert r.json["rows"][0]["categories"]["hifz"]["hours"] == "80.00"

    entry = db.session.scalar(select(AuditEntry).where(AuditEntry.kind == "rasd_import"))
    assert entry is not None
    overrides = entry.after["overrides"]
    assert overrides[0] == {
        "name": "طالب",
        "field": "hifz_achieved",
        "original": "2",
        "override": "8",
    }


# ═══ ق-٢٤١ — المعاينة هي الخطّة نفسها التي يُنفّذها الاستيراد (و-٢٠) ═══


def test_footer_labels_are_reported_not_silently_dropped(client, seeded):
    """
    @covers ق-٢٤١

    مشرفٌ يرى ٢٤ صفًّا في ملفٍّ فيه ٢٦ سطرًا يحتاج أن يعرف أنّ الفارق صفّا
    تذييل — لا طالبَين ضائعَين. الاستبعاد الصامت يُقرَأ كعطل.
    """
    _make_admin(seeded["users"]["1001"])
    _login(client)

    r = _upload(client, PREVIEW, RICH.read_bytes())
    assert r.json["excluded_labels"] == ["الإجمالي", "المتوسط"]
    assert r.json["totals"]["rows"] == 24


def test_preview_totals_equal_what_commit_actually_writes(client, seeded):
    """
    @covers ق-٢٤١

    **الضمانة المركزية:** ما تَعِد به المعاينة هو ما يكتبه التنفيذ بالضبط —
    عددًا وساعاتٍ. كانا مسارَي كودٍ منفصلَين، فكان انحرافُهما مسألةَ وقت.
    """
    _add_student(seeded, "سلمان الغفيص", "9001")
    _add_student(seeded, "مهنا العليان", "9002")
    _add_all_weights(seeded, quran_hours="1.00")
    _make_admin(seeded["users"]["1001"])
    _login(client)

    preview = _upload(client, PREVIEW, RICH.read_bytes()).json
    committed = _upload(client, COMMIT, RICH.read_bytes()).json

    assert preview["totals"]["events_new"] == committed["events_created"]

    # ومجموع الساعات المُعلَن = مجموع ما دخل الدفتر فعلًا.
    written = db.session.scalar(select(db.func.coalesce(db.func.sum(PointEvent.delta), 0)))
    assert Decimal(preview["totals"]["hours_total"]) == written


def test_preview_hours_per_category_equal_committed_hours(client, seeded):
    """@covers ق-٢٤١ — لا على المجموع فقط، بل فئةً فئة."""
    _add_student(seeded, "سلمان الغفيص", "9001")
    _add_all_weights(seeded, quran_hours="1.00")
    _make_admin(seeded["users"]["1001"])
    _login(client)

    previewed = next(
        x
        for x in _upload(client, PREVIEW, RICH.read_bytes()).json["rows"]
        if x["name"] == "سلمان الغفيص"
    )
    committed = next(
        x
        for x in _upload(client, COMMIT, RICH.read_bytes()).json["rows"]
        if x["name"] == "سلمان الغفيص"
    )
    assert previewed["categories"] == committed["categories"]


def test_preview_after_import_marks_every_category_already_imported(client, seeded):
    """
    @covers ق-٢٤١

    إعادة رفع الملفّ نفسه: المعاينة تقول **قبل** الضغط إنّ لا شيء سيُكتب،
    بدل أن يكتشف المشرف ذلك من ردّ التنفيذ.
    """
    _add_student(seeded, "سلمان الغفيص", "9001")
    _add_all_weights(seeded, quran_hours="1.00")
    _make_admin(seeded["users"]["1001"])
    _login(client)

    _upload(client, COMMIT, RICH.read_bytes())

    again = _upload(client, PREVIEW, RICH.read_bytes()).json
    assert again["totals"]["events_new"] == 0
    assert again["totals"]["events_already_imported"] > 0
    assert again["duplicate_warning"] is True

    row = next(x for x in again["rows"] if x["name"] == "سلمان الغفيص")
    assert {c["status"] for c in row["categories"].values()} == {"already_imported"}


def test_preview_without_a_ruleset_warns_instead_of_failing(client, seeded):
    """
    @covers ق-٢٤١

    غيابُ نسخة أوزان سارية **لا يمنع النظر في الملفّ** — المعاينة تُحذّر
    وتترك الاحتساب فارغًا، فيعرف المشرف أن يضبط الأوزان أوّلًا. (التنفيذ
    وحده يرفض صراحةً.)
    """
    _add_student(seeded, "سلمان الغفيص", "9001")
    _make_admin(seeded["users"]["1001"])
    _login(client)

    # تاريخٌ يسبق كلّ إصدارات الأوزان في `conftest` ⇒ لا مجموعة قواعد سارية.
    before_any_version = date(2020, 1, 1)

    r = _upload(client, PREVIEW, RICH.read_bytes(), occurred_on=before_any_version)
    assert r.status_code == 200
    assert r.json["weights_missing"] is True
    assert r.json["totals"]["events_new"] == 0

    # والتنفيذ بنفس التاريخ يرفض بوضوح لا بـ٥٠٠.
    c = _upload(client, COMMIT, RICH.read_bytes(), occurred_on=before_any_version)
    assert c.status_code == 422


def test_category_without_a_weight_is_reported_not_a_server_error(client, seeded):
    """
    @covers ق-٢٤١

    فئةٌ بلا وزن في الإصدار السارّي كانت ترفع `ValueError` من المحرّك فتصير
    ٥٠٠. الآن حالةٌ معروضة: المشرف يرى أيّ فئة لن تُحتسب ولماذا.
    """
    _add_student(seeded, "سلمان الغفيص", "9001")
    # الحفظ وحده موزون — التثبيت والمراجعة والحضور بلا وزن.
    _add_weight(seeded, "quran_hifz", "1.00")
    _make_admin(seeded["users"]["1001"])
    _login(client)

    r = _upload(client, PREVIEW, RICH.read_bytes())
    assert r.status_code == 200
    row = next(x for x in r.json["rows"] if x["name"] == "سلمان الغفيص")
    assert row["categories"]["hifz"]["status"] == "created"
    assert row["categories"]["thabat"]["status"] == "no_weight"
    assert row["categories"]["attendance"]["status"] == "no_weight"

    # والتنفيذ يكتب الموزون ويتجاوز غيره بلا انفجار.
    c = _upload(client, COMMIT, RICH.read_bytes())
    assert c.status_code == 201
