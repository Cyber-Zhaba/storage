import sqlalchemy
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

from data.db_session import SqlAlchemyBase


class Document(SqlAlchemyBase, UserMixin, SerializerMixin):

    __tablename__ = 'documents'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    owner_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("users.id"))
    last_modified = sqlalchemy.Column(sqlalchemy.DATETIME, default=datetime.datetime.now, nullable=True)
    size = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    amount_of_lines = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    version = sqlalchemy.Column(sqlalchemy.String, nullable=True)