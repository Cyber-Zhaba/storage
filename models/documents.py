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
    filename = sqlalchemy.Column(sqlalchemy.String, nullable=True, unique=True)
    last_change = sqlalchemy.Column(sqlalchemy.DATETIME, default=datetime.datetime.now)
