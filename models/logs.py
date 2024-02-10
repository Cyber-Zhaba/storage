import sqlalchemy
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin

from data.db_session import SqlAlchemyBase


class Log(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'logs'

    log_id = sqlalchemy.Column(sqlalchemy.Integer,
                               primary_key=True,
                               autoincrement=True)
    type = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    time = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    object_id = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    owner_id = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    description = sqlalchemy.Column(sqlalchemy.String, nullable=True)