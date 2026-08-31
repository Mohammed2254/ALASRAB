"""مخططات Marshmallow: شكل الطلب والردّ والتحقّق. لا منطق أعمال ولا وصول للقاعدة."""

from .auth import LoginSchema, SessionSchema
from .me import DeckSchema
from .reading import (
    ApproveSchema,
    MyReadingsSchema,
    QueueSchema,
    RejectSchema,
    ReviewResultsSchema,
    SubmitReadingSchema,
    SubmittedSchema,
)

__all__ = [
    "ApproveSchema",
    "DeckSchema",
    "LoginSchema",
    "MyReadingsSchema",
    "QueueSchema",
    "RejectSchema",
    "ReviewResultsSchema",
    "SessionSchema",
    "SubmitReadingSchema",
    "SubmittedSchema",
]
