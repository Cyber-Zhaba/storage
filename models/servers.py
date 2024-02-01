import sqlalchemy
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin
from data.db_session import SqlAlchemyBase


class Server(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'servers'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    host = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    port = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    ended_capacity = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    capacity = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)