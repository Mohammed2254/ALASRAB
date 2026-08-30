"""مخططات Marshmallow: شكل الطلب والردّ والتحقّق. لا منطق أعمال ولا وصول للقاعدة."""

from .auth import LoginSchema, SessionSchema

__all__ = ["LoginSchema", "SessionSchema"]
