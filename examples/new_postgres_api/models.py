from nzrapi.db.fields import IntegerColumn, StringColumn
from nzrapi.db.models import Model


class Item(Model):
    __tablename__ = "items"
    id = IntegerColumn(primary_key=True, index=True)
    name = StringColumn(index=True)
    description = StringColumn(nullable=True)
