import asyncio
import os
import shutil

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
from models.documents import Document
from models.servers import Server
from forms.FileForm import AddDocumentsForm
from requests import get, post, delete, put
from forms.SignUpForm import SignUpForm, LoginForm, EditUserForm
from forms.ServerForm import AddServerForm
from data.user_service import UserResource, UserListResource
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
        return render_template('admin_pages/admin_404.html')
    else:
        return render_template('user_pages/user_404.html')


@app.route('/logout')
@login_required
def logout():
    """Logout url"""
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
                message = "Этот email уже привязан к акаунту"
            else:
                post('http://localhost:5000/api/users', json={
                    'login': form.login.data,
                    'email': form.email.data,
                    'password': form.password.data},
                     timeout=(2, 20))
                user = session.query(User).filter(User.login == f'{form.login.data}').first()
                login_user(user, remember=form.remember_me.data)
                return redirect("/", 301)
            session.close()
    return render_template('sign_up.html', title='Регистрация', form=form, message=message)


@app.route('/login', methods=['GET', 'POST'])
def login():
    message, form = '', LoginForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            session = db_session.create_session()
            user = session.query(User).filter(User.login == form.login.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                return redirect("/", 301)
            message = "Неправильный логин или пароль"
            session.close()
    return render_template('login.html', title='Логин', form=form, message=message)


@app.route('/', methods=['GET', 'POST'])
def main_page():
    user_id = 0
    if not current_user.is_anonymous:
        user_id = current_user.id
    return render_template('main.html', title='Главная страница', is_anonymous=current_user.is_anonymous,
                           user_id=user_id)


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
            session.close()
            return redirect(f"/user_profile/{user_id}", 301)
    if current_user.admin == 0:
        return render_template('/user_pages/user_profile.html', title='Главная страница', form=form, user_id=user_id)
    return render_template('/admin_pages/admin_profile.html', title='Главная страница', form=form, user_id=user_id)


@app.route('/user_table_files/<int:user_id>', methods=['GET', 'POST'])
@login_required
def user_table_files(user_id):
    if current_user.id != user_id:
        abort(404)
    session = db_session.create_session()
    documents = session.query(Document).filter(Document.owner_id == user_id)
    if documents is None:
        documents = []
    if request.method == 'POST':
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
        asyncio.run(
            manage("add", doc['id'], name_of_document, get('http://localhost:5000/api/servers').json()['servers'],
                   file_folder="./files/"))
        os.remove(f'./files/{name_of_document}')
    session.close()
    return render_template('/user_pages/user_table_files.html', title='Главная страница', documents=documents,
                           user_id=user_id)


@app.route('/delete_document/<int:file_id>')
@login_required
def delete_file(file_id):
    document = get(f'http://localhost:5000/api/documents/{file_id}').json()
    if document['document']['owner_id'] == current_user.id or current_user.admin == 1:
        delete(f'http://localhost:5000/api/documents/{file_id}')
        asyncio.run(
            manage("delete", file_id, document['document']['name'], get('http://localhost:5000/api/servers').json()['servers']))
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
                post('http://localhost:5000/api/servers', json={
                    'name': form.name.data,
                    'host': form.address.data,
                    'port': form.port.data,
                    'capacity': t // (2 ** 30),
                    'ended_capacity': f // (2 ** 30)
                }, timeout=(2, 20))
        return render_template('/admin_pages/add_server.html', form=form)
    return abort(404)


if __name__ == '__main__':
    api.add_resource(UserListResource, '/api/users')
    api.add_resource(UserResource, '/api/users/<int:user_id>')
    api.add_resource(DocumentListResource, '/api/documents')
    api.add_resource(DocumentResource, '/api/documents/<int:document_id>')
    api.add_resource(ServerListResource, '/api/servers')
    api.add_resource(ServerResource, '/api/servers/<int:server_id>')
    db_session.global_init("data/data.db")
    app.run(debug=True, host='0.0.0.0')
