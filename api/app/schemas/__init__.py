"""مخططات Marshmallow: شكل الطلب والردّ والتحقّق. لا منطق أعمال ولا وصول للقاعدة."""

from .audit import ResetPinSchema
from .auth import LoginSchema, SessionSchema
from .me import DeckSchema, EventsSchema
from .reading import (
    ApproveSchema,
    MyReadingsSchema,
    QueueSchema,
    RejectSchema,
    ReviewResultsSchema,
    SubmitReadingSchema,
    SubmittedSchema,
)
from .report import ReportSchema

__all__ = [
    "ApproveSchema",
    "DeckSchema",
    "EventsSchema",
    "LoginSchema",
    "MyReadingsSchema",
    "QueueSchema",
    "RejectSchema",
    "ResetPinSchema",
    "ReportSchema",
    "ReviewResultsSchema",
    "SessionSchema",
    "SubmitReadingSchema",
    "SubmittedSchema",
]
