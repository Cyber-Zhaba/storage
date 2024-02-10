from flask import jsonify
from flask_restful import Resource, reqparse

from data import db_session
from models.logs import Log


class LogResource(Resource):
    def __init__(self):
        self.session = db_session.create_session()
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('type')
        self.parser.add_argument('time')
        self.parser.add_argument('object_id')
        self.parser.add_argument('owner_id')

    def get(self, owner_id):
        user = self.session.query(Log).get(owner_id)
        return jsonify({'user': user.to_dict()})

    def put(self, log_id: int):
        args = self.parser.parse_args()
        log = self.session.query(Log).get(log_id)
        if args['type'] != '':
            setattr(log, 'type', args['type'])
        if args['time'] != '':
            setattr(log, 'time', args['time'])
        if args['object_id'] != '':
            setattr(log, 'object_id', args['object_id'])
        if args['owner_id'] != '':
            setattr(log, 'owner_id', args['owner_id'])
        self.session.commit()
        return jsonify({'status': 'OK'})


class LogsListResource(Resource):
    def __init__(self):
        self.session = db_session.create_session()
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('type', required=True)
        self.parser.add_argument('time', required=True)
        self.parser.add_argument('object_id', required=True)
        self.parser.add_argument('owner_id', required=True)
        self.parser.add_argument('description', required=True)

    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument('owner_id', required=True)
        args = parser.parse_args()
        if args['owner_id'] != '':
            return jsonify({'log': [log.to_dict(rules=("-log", "-log")) for log in
                                    self.session.query(Log).filter(Log.owner_id == args['owner_id']).all()]})
        return jsonify({'log': [log.to_dict(rules=("-log", "-log")) for log in self.session.query(Log).all()]})

    def post(self):
        args = self.parser.parse_args()
        log = Log(
            type=args['type'],
            time=args['time'],
            object_id=args['object_id'],
            owner_id=args['owner_id'],
            description=args['description']
        )
        self.session.add(log)
        self.session.commit()
        return jsonify({'log': log.to_dict()})
