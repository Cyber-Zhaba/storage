from flask_restful import Resource, reqparse
from flask import jsonify
from data import db_session
from models.users import User


class UserResource(Resource):
    def __init__(self):
        self.session = db_session.create_session()
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('login')
        self.parser.add_argument('email')
        self.parser.add_argument('password')

    def get(self, user_id):
        user = self.session.query(User).get(user_id)
        return jsonify({'user': user.to_dict()})

    def delete(self, user_id):
        self.session.delete(self.session.query(User).get(user_id))
        self.session.commit()
        return jsonify({'status': 'OK'})


class UserListResource(Resource):
    def __init__(self):
        self.session = db_session.create_session()
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('login', required=True)
        self.parser.add_argument('email', required=True)
        self.parser.add_argument('password', required=True)

    def get(self):
        return jsonify({'users': [user.to_dict(rules=("-user", "-user")) for user in self.session.query(User).all()]})

    def post(self):
        args = self.parser.parse_args()
        users = User(
            login=args['login'],
            email=args['email'],
            documents='',
            admin=0
        )
        users.set_password(args['password'])
        self.session.add(users)
        self.session.commit()
        print(users)
        return jsonify({'status': 'OK'})

