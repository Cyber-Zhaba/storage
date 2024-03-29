from flask import jsonify
from flask_restful import Resource, reqparse

from data import db_session
from models.users import User


class UserResource(Resource):
    def __init__(self):
        self.session = db_session.create_session()
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('login')
        self.parser.add_argument('email')
        self.parser.add_argument('password')
        self.parser.add_argument('admin')

    def get(self, user_id):
        user = self.session.query(User).get(user_id)
        return jsonify({'user': user.to_dict()})

    def delete(self, user_id):
        self.session.delete(self.session.query(User).get(user_id))
        self.session.commit()
        return jsonify({'status': 'OK'})

    def put(self, user_id: int):
        args = self.parser.parse_args()
        user = self.session.query(User).get(user_id)
        if args['login'] != '':
            setattr(user, 'login', args['login'])
        if args['email'] != '':
            setattr(user, 'email', args['email'])
        if args['admin'] != '':
            setattr(user, 'admin', args['admin'])
        self.session.commit()
        return jsonify({'status': 'OK'})


class UserListResource(Resource):
    def __init__(self):
        self.session = db_session.create_session()
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('login', required=True)
        self.parser.add_argument('email', required=True)
        self.parser.add_argument('password', required=True)
        self.parser.add_argument('admin', required=True)

    def get(self):
        return jsonify({'users': [user.to_dict(rules=("-user", "-user")) for user in self.session.query(User).all()]})

    def post(self):
        args = self.parser.parse_args()
        users = User(
            login=args['login'],
            email=args['email'],
            admin=args['admin'],
            documents=''
        )
        users.set_password(args['password'])
        self.session.add(users)
        self.session.commit()
        return jsonify({'user': users.to_dict()})
