from flask_migrate import Migrate
from flask_smorest import Api
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# تُنشأ هنا وحدها: النماذج والمسارات تستوردها، ولو أنشأها create_app لصارت
# دورة استيراد بين التطبيق وما فيه.
db = SQLAlchemy(model_class=Base)
migrate = Migrate()
api = Api()
