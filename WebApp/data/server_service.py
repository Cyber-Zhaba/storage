from flask import jsonify
from flask_restful import Resource, reqparse

from data import db_session
from models.documents import Document
from models.servers import Server
from models.versions import Versions


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
        server = self.session.query(Server).get(server_id)
        for v in self.session.query(Versions).filter(Versions.server_id == server.id).all():
            self.session.delete(v)
        self.session.delete(server)
        self.session.commit()
        return jsonify({'status': 'OK'})

    def put(self, server_id: int):
        args = self.parser.parse_args()
        server = self.session.query(Server).get(server_id)
        if args['name'] != '':
            setattr(server, 'name', args['name'])
        if args['host'] != '':
            setattr(server, 'host', args['host'])
        if args['port'] != '':
            setattr(server, 'port', args['port'])
        self.session.commit()
        return jsonify({'status': 'OK'})


class ServerListResource(Resource):
    def __init__(self):
        self.session = db_session.create_session()
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('name', required=False)
        self.parser.add_argument('host', required=False)
        self.parser.add_argument('port', required=False)
        self.parser.add_argument('ended_capacity', required=False)
        self.parser.add_argument('capacity', required=False)
        self.parser.add_argument('file_id', required=False)

    def get(self):
        args = self.parser.parse_args()
        if args.get('file_id', None) is None:
            return jsonify(
                {'servers': [user.to_dict(rules=("-server", "-server"))
                             for user in self.session.query(Server).all()]})
        if args['file_id'] != "-1":
            doc = self.session.query(Document).filter(Document.id == args['file_id']).first()
            versions = self.session.query(Versions).filter(Versions.file_id == args['file_id']).filter(Versions.current_version == doc.version).all()
            servers = [
                self.session.query(Server).filter(Server.id == v.server_id).first().to_dict()
                for v in versions
            ]
            return jsonify({'servers': servers})
        servers = []
        for s in self.session.query(Server).all():
            versions = self.session.query(Versions).filter(Versions.server_id == s.id).all()
            for v in versions:
                d = self.session.query(Document).get(v.file_id)
                if d is None:
                    continue
                if d.version != v.current_version:
                    break
            else:
                servers.append(s.to_dict())
        return jsonify({
            'servers': servers
        })

    def post(self):
        args = self.parser.parse_args()
        if args.get('file_id', None) is None:
            server = Server(
                name=args['name'],
                host=args['host'],
                port=args['port'],
                ended_capacity=args['ended_capacity'],
                capacity=args['capacity'],
            )
            self.session.add(server)
            doc = self.session.query(Document).all()
            for d in doc:
                ver = Versions(
                    server_id=server.id,
                    file_id=d.id,
                    current_version=d.version
                )
                self.session.add(ver)
            self.session.commit()
            return jsonify({'server': server.to_dict()})
        server = self.session.query(Server).filter(Server.host == args['host']).filter(Server.port == args['port']).first()
        doc = self.session.query(Document).filter(Document.id == args['file_id']).first()
        ver = self.session.query(Versions).filter(Versions.file_id == args['file_id']).filter(Versions.server_id == server.id).first()
        if ver is None:
            ver = Versions(
                server_id=server.id,
                file_id=args['file_id'],
                current_version=0
            )
            self.session.add(ver)
        ver.current_version = doc.version
        self.session.commit()
