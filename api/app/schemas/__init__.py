"""مخططات Marshmallow: شكل الطلب والردّ والتحقّق. لا منطق أعمال ولا وصول للقاعدة."""

from .auth import LoginSchema, SessionSchema
from .me import DeckSchema

__all__ = ["DeckSchema", "LoginSchema", "SessionSchema"]
