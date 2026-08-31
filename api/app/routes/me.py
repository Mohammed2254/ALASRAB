"""
مسارات الطالب. **حدّ تنسيق لا مكان قواعد.**

المسار يفعل أربعة أشياء لا خامس: يتحقّق من المدخلات · يحلّ الهوية المصادَق عليها
· يستدعي الخدمة · يردّ الشكل الموثَّق. **لا حساب رتبة ولا ساعات ولا حالة طيران
هنا** — وكلٌّ منها له مالك واحد في `services/`.
"""

from flask import g, request
from flask.views import MethodView
from flask_smorest import Blueprint, abort

from ..extensions import db
from ..models import Org
from ..schemas import (
    DeckSchema,
    EventsSchema,
    MyReadingsSchema,
    SubmitReadingSchema,
    SubmittedSchema,
)
from ..security import login_required
from ..services import deck as deck_service
from ..services import reading as reading_service

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
        org = db.session.get(Org, g.user.org_id)
        card = deck_service.build(org, g.user.id)

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
            # rank_in_org مؤجَّل إلى و-٩ (FR-051) — ولا يُحسب هنا كحلٍّ مؤقّت.
            "team": None if card.team is None else {"name": card.team.name, "rank_in_org": None},
        }


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
        org = db.session.get(Org, g.user.org_id)
        try:
            submission = reading_service.submit(
                org, g.user.id, data["read_on"], data["pages"], data["book_title"]
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
