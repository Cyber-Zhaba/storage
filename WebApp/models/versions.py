import sqlalchemy
from flask_login import UserMixin
from sqlalchemy_serializer import SerializerMixin
from data.db_session import SqlAlchemyBase


class Versions(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'versions'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    server_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("servers.id"))
    file_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey("documents.id"))
    current_version = sqlalchemy.Column(sqlalchemy.Integer)
