"""
مسارات الطالب. **حدّ تنسيق لا مكان قواعد.**

المسار يفعل أربعة أشياء لا خامس: يتحقّق من المدخلات · يحلّ الهوية المصادَق عليها
· يستدعي الخدمة · يردّ الشكل الموثَّق. **لا حساب رتبة ولا ساعات ولا حالة طيران
هنا** — وكلٌّ منها له مالك واحد في `services/`.
"""

from datetime import UTC, datetime

from flask import g, request
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from ..extensions import db
from ..models import Team, User
from ..schemas import (
    AnsweredSchema,
    AnswerSchema,
    DeckSchema,
    EventsSchema,
    FormationSchema,
    MyReadingsSchema,
    PilotsBoardSchema,
    StationSchema,
    SubmitNoteSchema,
    SubmitReadingSchema,
    SubmitTahdirSchema,
    SubmittedSchema,
    TahdirReportSchema,
    TeamsBoardSchema,
    TodayQuestionSchema,
    WeekPilotSchema,
)
from ..security import login_required
from ..services import deck as deck_service
from ..services import engagement as engagement_service
from ..services import fuel as fuel_service
from ..services import fuel_week as fuel_week_service
from ..services import reading as reading_service
from ..services import standings as standings_service
from ..services import week as week_service
from ._helpers import org_of_session

blp = Blueprint("me", __name__, url_prefix="/api", description="بطاقة الطيار")


@blp.route("/me/deck")
class Deck(MethodView):
    @login_required
    @blp.response(200, DeckSchema)
    def get(self):
        """
        بطاقة **الطالب المصادَق عليه**.

        الهوية من الجلسة لا من الطلب: لا معرّف في المسار ولا في الاستعلام، فلا
        يوجد ما يُتلاعب به أصلًا. وهذا أقوى من التحقّق من الملكية — يُلغي
        المسار الذي يحتاج تحقّقًا.
        """
        org = org_of_session()
        try:
            card = deck_service.build(org, g.user.id)
        except deck_service.DeckError as exc:
            # عطلُ إعدادٍ لا عطلُ خادم: رسالةٌ تقول ما الناقص بدل «حدث خلل».
            abort(exc.status, message=str(exc))

        team = None
        if card.team is not None:
            team = {
                "name": card.team.name,
                # FR-051 (و-٩ب) — نفس ترتيب `GET /boards/teams` تمامًا، لا حساب موازٍ.
                "rank_in_org": standings_service.team_rank(org, card.team.id),
            }

        return {
            "rank": {"name": card.rank.name, "tier": card.rank.tier},
            "hours": card.hours,
            "next_rank": None
            if card.next_rank is None
            else {
                "name": card.next_rank.name,
                "at_hours": card.next_rank.at_hours,
                "progress_pct": card.progress_pct,
                "remaining": card.remaining,
            },
            "flight": {
                "grounded": card.flight.grounded,
                "last_activity_on": card.flight.last_activity_on,
            },
            "team": team,
        }


@blp.route("/boards/pilots")
class PilotsBoard(MethodView):
    @login_required
    @blp.response(200, PilotsBoardSchema)
    def get(self):
        """صدارة الأفراد — نافذة الأسبوع الحالي (FR-050 · API.md §٥)."""
        org = org_of_session()
        return {"pilots": standings_service.pilots_board(org)}


@blp.route("/boards/teams")
class TeamsBoard(MethodView):
    @login_required
    @blp.response(200, TeamsBoardSchema)
    def get(self):
        """صدارة الأسراب بالمعدّل، فكّ التعادل بـ`code` (FR-051 · FR-052)."""
        org = org_of_session()
        return {"teams": standings_service.teams_board(org)}


@blp.route("/boards/formation")
class Formation(MethodView):
    @login_required
    @blp.response(200, FormationSchema)
    def get(self):
        """مشهد التشكيل — محكوم بف-١ (FR-053)."""
        scope = request.args.get("scope", "team")
        if scope not in ("team", "general"):
            abort(422, message="scope يجب أن يكون team أو general")
        org = org_of_session()
        return standings_service.formation(org, g.user.id, scope)


def _answered_payload(answered):
    """
    شكلُ الإجابة — **مبنيٌّ في موضعٍ واحد**.

    كان يُبنى يدويًّا مرّتين (سؤال اليوم وردُّ الإجابة)، فحقلٌ يُضاف إلى
    أحدهما يغيب عن الآخر بصمت — وقد وقع فعلًا مع `streak` في و-٢٠.
    """
    if answered is None:
        return None
    return {
        "choice_id": answered.choice_id,
        "correct": answered.correct,
        "correct_id": answered.correct_id,
        "note": answered.note,
        "awarded_hours": answered.awarded_hours,
        "streak": answered.streak,
    }


def _question_payload(question, answered):
    return {
        "id": question.id,
        "prompt": question.prompt,
        "choices": question.choices,
        "answered": _answered_payload(answered),
    }


@blp.route("/questions/today")
class TodayQuestion(MethodView):
    @login_required
    @blp.response(200, TodayQuestionSchema)
    def get(self):
        """سؤال اليوم — بتوقيت المنظمة (FR-060)."""
        org = org_of_session()
        question, answered = engagement_service.today(org, g.user.id)
        return {"question": None if question is None else _question_payload(question, answered)}


@blp.route("/questions/<int:question_id>/answer")
class AnswerQuestion(MethodView):
    @login_required
    @blp.arguments(AnswerSchema)
    @blp.response(200, AnsweredSchema)
    def post(self, data, question_id):
        """إجابة واحدة لكل سؤال — القيد في القاعدة لا بإخفاء الزرّ (FR-060 · ث-٨)."""
        org = org_of_session()
        try:
            result = engagement_service.answer(org, g.user.id, question_id, data["choice_id"])
        except engagement_service.EngagementError as exc:
            abort(exc.status, message=str(exc))
        return _answered_payload(result)


@blp.route("/notes")
class SubmitNote(MethodView):
    @login_required
    @blp.arguments(SubmitNoteSchema)
    @blp.response(201)
    def post(self, data):
        """ملاحظة مجهولة — بلا `id` في الردّ (FR-061 · ث-١٢)."""
        org = org_of_session()
        try:
            engagement_service.submit_note(org, data["body"])
        except engagement_service.EngagementError as exc:
            abort(exc.status, message=str(exc))


@blp.route("/week/pilot")
class WeekPilot(MethodView):
    @login_required
    @blp.response(200, WeekPilotSchema)
    def get(self):
        """طيار الأسبوع الحالي وسببه — `null` إن لم يُختَر بعد (FR-062)."""
        org = org_of_session()
        row = engagement_service.week_pilot(org)
        if row is None:
            return {"pilot": None}
        pilot = db.session.get(User, row.user_id)
        return {"pilot": {"full_name": pilot.full_name, "reason": row.reason}}


@blp.route("/me/readings")
class MyReadings(MethodView):
    @login_required
    @blp.response(200, MyReadingsSchema)
    def get(self):
        """
        طلبات **الطالب المصادَق عليه** وحده — الهوية من الجلسة لا من الطلب.

        و`hours` تأتي **من الحدث** لا من `pages × وزن`: الواجهة تعرض ولا تحسب،
        وحسابها في مكانين يعني نسختين تتباعدان.
        """
        rows = reading_service.list_for_user(g.user.id)
        return {
            "readings": [
                {
                    "id": s.id,
                    "read_on": s.read_on,
                    "pages": s.pages,
                    "book_title": s.book_title,
                    "status": s.status,
                    "review_reason": s.review_reason,
                    "reviewed_at": s.reviewed_at,
                    "hours": event.delta if event is not None else None,
                }
                for s, event in rows
            ]
        }

    @login_required
    @blp.arguments(SubmitReadingSchema)
    @blp.response(201, SubmittedSchema)
    def post(self, data):
        """طلبٌ معلَّق. **لا ساعات في الردّ** — لا يمنح شيئًا قبل الاعتماد (FR-021)."""
        org = org_of_session()
        try:
            submission = reading_service.submit(
                org, g.user.id, data["read_on"], data["pages"], data["book_title"]
            )
        except reading_service.ReadingError as exc:
            abort(exc.status, message=str(exc))
        return {"id": submission.id, "status": submission.status}


@blp.route("/me/tahdir")
class MyTahdir(MethodView):
    """تحضير القراءة — و-١١ · FR-090..093. نفس شكل `/me/readings` بقيود إضافية."""

    @login_required
    @blp.response(200, TahdirReportSchema)
    def get(self):
        org = org_of_session()
        rows = reading_service.list_for_user(g.user.id, activity_type=reading_service.TAHDIR)
        return {
            "submissions": [
                {
                    "id": s.id,
                    "read_on": s.read_on,
                    "pages": s.pages,
                    "book_title": s.book_title,
                    "status": s.status,
                    "review_reason": s.review_reason,
                    "reviewed_at": s.reviewed_at,
                    "hours": event.delta if event is not None else None,
                }
                for s, event in rows
            ],
            "week": reading_service.weekly_report(org, g.user.id),
        }

    @login_required
    @blp.arguments(SubmitTahdirSchema)
    @blp.response(201, SubmittedSchema)
    def post(self, data):
        """طلبٌ معلَّق **لا يمنح ساعات** (FR-091)."""
        org = org_of_session()
        try:
            submission = reading_service.submit(
                org,
                g.user.id,
                data["read_on"],
                data["pages"],
                data["book_title"],
                activity_type=reading_service.TAHDIR,
            )
        except reading_service.ReadingError as exc:
            abort(exc.status, message=str(exc))
        return {"id": submission.id, "status": submission.status}


@blp.route("/me/events")
class MyEvents(MethodView):
    @login_required
    @blp.response(200, EventsSchema)
    def get(self):
        """
        سجلّ ساعات **الطالب المصادَق عليه** (FR-012).

        الهوية من الجلسة: لا معرّف في المسار ولا في الاستعلام، **فلا يوجد ما
        يُتلاعب به** — وهذا أقوى من التحقّق من الملكية لأنه يُلغي المسار المحتاج
        إليه.
        """
        limit = min(max(request.args.get("limit", 20, type=int), 1), 100)
        return {
            "events": [
                {
                    "id": e.id,
                    "kind": e.kind,
                    "delta": e.delta,
                    "occurred_on": e.occurred_at.date(),
                    "reason": e.reason,
                }
                for e in deck_service.recent_events(g.user.org_id, g.user.id, limit)
            ]
        }


@blp.route("/station")
class Station(MethodView):
    @login_required
    @blp.response(200, StationSchema)
    def get(self):
        """
        محطة التزوّد — وقود سرب **الطالب المصادَق عليه** (FR-072 · و-٨).

        **شاشة طيّار لا مشرف** (`docs/slices/و-٨.md`): كل عضو سرب يراه، تمامًا
        كلوحات الصدارة، لا تقييمها الذي يملكه المشرف وحده. `team: null` لمن
        بلا عضوية سارية — حالة مصمَّمة لا عطل (`SCOPE.md` ط-٢)، نفس عقد
        `GET /me/deck`.
        """
        org = org_of_session()
        if g.membership is None:
            return {
                "team": None,
                "week_task": None,
                "tank_capacity_l": org.tank_capacity_l,
                "recent": [],
            }

        data = fuel_service.team_fuel(g.user.org_id, g.membership.team_id)
        team = db.session.get(Team, g.membership.team_id)
        week_start = week_service.week_start_local(org, datetime.now(UTC))
        return {
            "team": {"name": team.name, "litres": data["litres"]},
            # مهمّة هذا الأسبوع — يراها الطالب **قبل** الاعتماد لا بعده.
            "week_task": fuel_week_service.team_task_this_week(
                org, g.membership.team_id, week_start
            ),
            "tank_capacity_l": org.tank_capacity_l,
            "recent": data["recent"],
        }
