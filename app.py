import asyncio
import os
import shutil
from math import ceil

from werkzeug.exceptions import BadRequestKeyError
from werkzeug.utils import secure_filename

from data import db_session
import configparser
import datetime
import logging
from os import getcwd

import matplotlib.dates as dates
import matplotlib.pyplot as plt
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, url_for
from flask import render_template, redirect
from flask_login import login_user, LoginManager, login_required, logout_user, current_user
from flask_restful import Api, abort
from gevent import monkey
from gevent.pywsgi import WSGIServer
from models.users import User
from models.logs import Log
from models.documents import Document
from models.servers import Server
from forms.FileForm import AddDocumentsForm
from requests import get, post, delete, put
from forms.SignUpForm import SignUpForm, LoginForm, EditUserForm
from forms.ServerForm import AddServerForm
from data.user_service import UserResource, UserListResource
from data.logs_service import LogResource, LogsListResource
from data.document_service import DocumentResource, DocumentListResource
from storage_communication import *
from data.server_service import ServerResource, ServerListResource

app = Flask(__name__)
api = Api(app)
login_manager = LoginManager(app)
login_manager.init_app(app)
app.config['SECRET_KEY'] = 'prev_prof_lovers_secret_key'
app.config['UPLOAD_FOLDER'] = './files'


@app.errorhandler(404)
def not_found(error):
    if current_user.is_anonymous == 0 and current_user.admin == 1:
        return render_template(
            'admin_pages/admin_404.html',
            username=current_user.login
        )
    else:
        return render_template('user_pages/user_404.html')


@app.route('/logout')
@login_required
def logout():
    """Logout url"""
    session = db_session.create_session()
    post('http://localhost:5000/api/log', json={
        'type': 3,
        'time': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
        'object_id': current_user.get_id(),
        'owner_id': current_user.get_id()},
         timeout=(2, 20))
    session.close()
    logout_user()
    return redirect("/")


@login_manager.user_loader
def load_user(user_id):
    """Load user"""
    session = db_session.create_session()
    result = session.get(User, user_id)
    session.close()
    return session.get(User, user_id)


@app.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    message, form = '', SignUpForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            session = db_session.create_session()
            if session.query(User).filter(User.login == f'{form.login.data}').first():
                message = "Этот логин уже существует"
            elif session.query(User).filter(User.email == f'{form.email.data}').first():
                message = "Этот email уже привязан к аккаунту"
            else:
                post('http://localhost:5000/api/users', json={
                    'login': form.login.data,
                    'email': form.email.data,
                    'password': form.password.data},
                     timeout=(2, 20))
                user = session.query(User).filter(User.login == f'{form.login.data}').first()
                login_user(user, remember=form.remember_me.data)
                post('http://localhost:5000/api/log', json={
                    'type': 0,
                    'time': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                    'object_id': user.get_id(),
                    'owner_id': user.get_id()},
                     timeout=(2, 20))
                return redirect("/", 301)
            session.close()
    return render_template(
        'sign_up.html',
        title='Регистрация',
        form=form,
        message=message
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    message, form = '', LoginForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            session = db_session.create_session()
            user = session.query(User).filter(User.login == form.login.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                post('http://localhost:5000/api/log', json={
                    'type': 1,
                    'time': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                    'object_id': user.get_id(),
                    'owner_id': user.get_id()},
                     timeout=(2, 20))
                return redirect(f"/user_profile/{user.id}", 301)
            message = "Неправильный логин или пароль"
            if user:
                post('http://localhost:5000/api/log', json={
                    'type': 2,
                    'time': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                    'object_id': user.get_id(),
                    'owner_id': user.get_id()},
                    timeout=(2, 20))
            session.close()
    return render_template(
        'login.html',
        title='Логин',
        form=form,
        message=message
    )


@app.route('/', methods=['GET', 'POST'])
def main_page():
    user_id = 0
    if not current_user.is_anonymous:
        user_id = current_user.id
    return render_template(
        'main.html',
        title='Главная страница',
        is_anonymous=current_user.is_anonymous,
        user_id=user_id
    )


@app.route('/user_profile/<int:user_id>', methods=['GET', 'POST'])
@login_required
def user_profile(user_id):
    if current_user.id != user_id:
        abort(404)
    message, form = '', EditUserForm()
    user = get(f'http://localhost:5000/api/users/{user_id}').json()['user']
    form.email.data, form.login.data = user['email'], user['login']
    if request.method == 'POST':
        if form.validate_on_submit() and (form.login.data != '' or form.email.data != ''):
            session = db_session.create_session()
            put(f'http://localhost:5000/api/users/{current_user.id}', json={
                'login': form.login.data,
                'email': form.email.data},
                timeout=(2, 20))
            post('http://localhost:5000/api/log', json={
                'type': 4,
                'time': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                'object_id': user.get_id(),
                'owner_id': user.get_id()},
                 timeout=(2, 20))
            session.close()
            return redirect(f"/user_profile/{user_id}", 301)
    if current_user.admin == 0:
        return render_template(
            '/user_pages/user_profile.html',
            title='Главная страница',
            form=form,
            user_id=user_id,
            username=current_user.login,
        )
    return render_template(
        '/admin_pages/admin_profile.html',
        title='Главная страница',
        form=form,
        user_id=user_id,
        username=current_user.login,
    )


@app.route('/user_table_files/<int:user_id>', methods=['GET', 'POST'])
@login_required
def user_table_files(user_id):
    if current_user.id != user_id:
        abort(404)

    session = db_session.create_session()

    if request.method == 'POST':
        try:
            document = request.files['file']
            name_of_document = secure_filename(document.filename)
            document.save(f'./files/{name_of_document}')
            with open(f'./files/{name_of_document}') as file:
                doc = post('http://localhost:5000/api/documents', json={
                    'name': name_of_document,
                    'owner_id': user_id,
                    'size': os.path.getsize(f'./files/{name_of_document}'),
                    'number_of_lines': len(file.readlines())},
                           timeout=(2, 20)).json()['document']
                post('http://localhost:5000/api/log', json={
                    'type': 5,
                    'time': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                    'object_id': doc['id'],
                    'owner_id': user_id},
                     timeout=(2, 20))
            asyncio.run(manage(
                "add",
                doc['id'],
                name_of_document,
                get('http://localhost:5000/api/servers').json()['servers'],
                file_folder="./files/"
            ))
            os.remove(f'./files/{name_of_document}')
        except PermissionError:
            pass

    if current_user.admin == 1:
        documents = session.query(Document).all()
    else:
        documents = session.query(Document).filter(Document.owner_id == user_id)
    if documents is None:
        documents = []

    documents = list(documents)
    pagination = request.args.get("pag")
    if pagination is None:
        pagination = 10
    else:
        pagination = int(pagination)
    total = len(documents)
    page = int(request.args.get('page', 1))
    documents = documents[(page - 1) * pagination: min(total, page * pagination)]
    next_p = min(page + 1, ceil(total / pagination))
    prev_p = max(page - 1, 1)

    session.close()
    if current_user.admin == 0:
        return render_template(
            '/user_pages/user_table_files.html',
            title='Главная страница',
            documents=documents,
            user_id=user_id,
            current_page=page,
            pagination=pagination,
            total_docs=total,
            pages=list(range(1, ceil(total / pagination) + 1)),
            selected=pagination,
            next=next_p,
            prev=prev_p,
            username=current_user.login,
        )
    return render_template(
        '/admin_pages/admin_table_files.html',
        title='Главная страница',
        documents=documents,
        user_id=user_id,
        current_page=page,
        pagination=pagination,
        total_docs=total,
        pages=list(range(1, ceil(total / pagination) + 1)),
        selected=pagination,
        next=next_p,
        prev=prev_p,
        username=current_user.login,
    )


@app.route('/admin_server_table')
@login_required
def server_table():
    if current_user.admin == 1:
        servers = get(f'http://localhost:5000/api/servers').json()['servers']

        servers = list(servers)
        pagination = request.args.get("pag")
        if pagination is None:
            pagination = 10
        else:
            pagination = int(pagination)
        total = len(servers)
        page = int(request.args.get('page', 1))
        servers = servers[(page - 1) * pagination: min(total, page * pagination)]
        next_p = min(page + 1, ceil(total / pagination))
        prev_p = max(page - 1, 1)

        return render_template(
            '/admin_pages/admin_table_serv.html',
            user_id=current_user.id,
            servers=servers,
            current_page=page,
            pagination=pagination,
            total_docs=total,
            pages=list(range(1, ceil(total / pagination) + 1)),
            selected=pagination,
            next=next_p,
            prev=prev_p,
            total=total,
            username=get(f'http://localhost:5000/api/users/{current_user.id}').json()["user"]["login"],
        )
    return abort(404)


@app.route('/delete_document/<int:file_id>')
@login_required
def delete_file(file_id):
    document = get(f'http://localhost:5000/api/documents/{file_id}').json()
    if document['document']['owner_id'] == current_user.id or current_user.admin == 1:
        session = db_session.create_session()
        post('http://localhost:5000/api/log', json={
            'type': 7,
            'time': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            'object_id': file_id,
            'owner_id': current_user.get_id()},
             timeout=(2, 20))
        session.close()
        delete(f'http://localhost:5000/api/documents/{file_id}')
        asyncio.run(manage(
            "delete",
            file_id,
            document['document']['name'],
            get('http://localhost:5000/api/servers').json()['servers']
        ))
        return redirect(f'/user_table_files/{current_user.id}', 200)
    abort(404)


@app.route('/add_server', methods=['GET', 'POST'])
@login_required
def add_server():
    if current_user.admin == 1:
        form = AddServerForm()
        if request.method == 'POST':
            if form.validate_on_submit():
                t, _, f = shutil.disk_usage("/")
                serv = post('http://localhost:5000/api/servers', json={
                    'name': form.name.data,
                    'host': form.address.data,
                    'port': form.port.data,
                    'capacity': t // (2 ** 30),
                    'ended_capacity': f // (2 ** 30)
                }, timeout=(2, 20))
                session = db_session.create_session()
                post('http://localhost:5000/api/log', json={
                    'type': 8,
                    'time': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                    'object_id': serv['id'],
                    'owner_id': current_user.get_id()},
                     timeout=(2, 20))
                session.close()
                return redirect('/admin_server_table')
        return render_template(
            '/admin_pages/add_server.html',
            form=form
        )
    return abort(404)


@app.route('/delete_server/<int:server_id>', methods=['GET', 'POST'])
@login_required
def delete_server(server_id):
    if current_user.admin == 1:
        storage = get(f'http://localhost:5000/api/servers/{server_id}').json()['server']
        asyncio.run(manage(
            "end", -1, "", [], storage=storage
        ))
        session = db_session.create_session()
        post('http://localhost:5000/api/log', json={
            'type': 9,
            'time': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            'object_id': server_id,
            'owner_id': current_user.get_id()},
             timeout=(2, 20))
        session.close()
        delete(f'http://localhost:5000/api/servers/{server_id}')
        return redirect(f'/admin_server_table', 200)
    abort(404)


if __name__ == '__main__':
    api.add_resource(UserListResource, '/api/users')
    api.add_resource(LogsListResource, '/api/log')
    api.add_resource(UserResource, '/api/users/<int:user_id>')
    api.add_resource(DocumentListResource, '/api/documents')
    api.add_resource(DocumentResource, '/api/documents/<int:document_id>')
    api.add_resource(ServerListResource, '/api/servers')
    api.add_resource(ServerResource, '/api/servers/<int:server_id>')
    db_session.global_init("data/data.db")
    app.run(debug=True, host='0.0.0.0')
