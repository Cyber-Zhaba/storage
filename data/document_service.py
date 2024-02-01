from flask_restful import Resource, reqparse
from flask import jsonify
from data import db_session
from models.documents import Document


class DocumentResource(Resource):
    def __init__(self):
        self.session = db_session.create_session()
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('name', required=True)
        self.parser.add_argument('owner_id', required=True)
        self.parser.add_argument('size', required=True)
        self.parser.add_argument('number_of_lines', required=True)

    def get(self, document_id):
        document = self.session.query(Document).get(document_id)
        return jsonify({'document': document.to_dict()})

    def delete(self, document_id):
        self.session.delete(self.session.query(Document).get(document_id))
        self.session.commit()
        return jsonify({'status': 'OK'})

    def put(self, document_id: int):
        args = self.parser.parse_args()
        user = self.session.query(Document).get(document_id)
        self.session.commit()
        return jsonify({'status': 'OK'})

    def patch(self, document_id: int):
        args = self.parser.parse_args()
        self.session.query(Document).filter(Document.id == document_id).update(args)
        self.session.commit()
        return jsonify({'status': 'OK'})


class DocumentListResource(Resource):
    def __init__(self):
        self.session = db_session.create_session()
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('name', required=True)
        self.parser.add_argument('owner_id', required=True)
        self.parser.add_argument('size', required=True)
        self.parser.add_argument('number_of_lines', required=True)

    def get(self):
        return jsonify({'documents': [user.to_dict(rules=("-document", "-document")) for user in self.session.query(Document).all()]})

    def post(self):
        args = self.parser.parse_args()
        document = Document(
            name=args['name'],
            owner_id=args['owner_id'],
            size=args['size'],
            number_of_lines=args['number_of_lines'],
        )
        self.session.add(document)
        self.session.commit()
        return jsonify({'document': document.to_dict()})
