from flask_restful import Resource, reqparse
from flask import jsonify
from data import db_session
from models.servers import Server


class ServerResource(Resource):
    def __init__(self):
        self.session = db_session.create_session()
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('name', required=True)
        self.parser.add_argument('host', required=True)
        self.parser.add_argument('port', required=True)
        self.parser.add_argument('ended_capacity', required=True)
        self.parser.add_argument('capacity', required=True)

    def get(self, server_id):
        server = self.session.query(Server).get(server_id)
        return jsonify({'server': server.to_dict()})

    def delete(self, server_id):
        self.session.delete(self.session.query(Server).get(server_id))
        self.session.commit()
        return jsonify({'status': 'OK'})

    def put(self, server_id: int):
        args = self.parser.parse_args()
        server = self.session.query(Server).get(server_id)
        self.session.commit()
        return jsonify({'status': 'OK'})


class ServerListResource(Resource):
    def __init__(self):
        self.session = db_session.create_session()
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('name', required=True)
        self.parser.add_argument('host', required=True)
        self.parser.add_argument('port', required=True)
        self.parser.add_argument('ended_capacity', required=True)
        self.parser.add_argument('capacity', required=True)

    def get(self):
        return jsonify({'servers': [user.to_dict(rules=("-server", "-server")) for user in self.session.query(Server).all()]})

    def post(self):
        args = self.parser.parse_args()
        server = Server(
            name=args['name'],
            host=args['host'],
            port=args['port'],
            ended_capacity=args['ended_capacity'],
            capacity=args['capacity'],
        )
        self.session.add(server)
        self.session.commit()
        return jsonify({'server': server.to_dict()})
