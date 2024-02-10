"""Flask main app"""
import asyncio
import datetime
import logging
import math
import os
from fnmatch import fnmatch
from math import ceil

from flask import Flask, request
from flask import render_template, redirect
from flask_login import login_user, LoginManager, login_required, logout_user, current_user
from flask_restful import Api, abort
from gevent import monkey
from gevent.pywsgi import WSGIServer
from markupsafe import Markup
from requests import get, post, delete, put, patch
from werkzeug.utils import secure_filename

from data import db_session
from data.document_service import DocumentResource, DocumentListResource
from data.logs_service import LogsListResource
from data.server_service import ServerResource, ServerListResource
from data.user_service import UserResource, UserListResource
from forms.ServerForm import AddServerForm
from forms.SignUpForm import SignUpForm, LoginForm, EditUserForm, AdminEditUserForm
from models.users import User
from models.versions import Versions
from storage_communication import manage

monkey.patch_all()
app = Flask(__name__)
api = Api(app)
login_manager = LoginManager(app)
login_manager.init_app(app)
app.config['SECRET_KEY'] = 'prev_prof_lovers_secret_key'
app.config['UPLOAD_FOLDER'] = './files'


@app.errorhandler(404)
def not_found(error):
    """
    Navigates user to not found page
    """
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
    post('http://localhost:5000/api/log', json={
        'type': 3,
        'time': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
        'object_id': current_user.get_id(),
        'owner_id': current_user.get_id(),
        'description': 'Выход из аккаунта'},
         timeout=(2, 20))
    logout_user()
    return redirect("/")


@login_manager.user_loader
def load_user(user_id):
    """Load user"""
    session = db_session.create_session()
    result = session.get(User, user_id)
    session.close()
    return result


@app.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    """
    Route to create and authorize new users
    """
    message, form = '', SignUpForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            session = db_session.create_session()
            if session.query(User).filter(User.login == f'{form.login.data}').first():
                message = "Этот логин уже существует"
            elif session.query(User).filter(User.email == f'{form.email.data}').first():
                message = "Этот email уже привязан к аккаунту"
            else:
                admin = 0
                if len(get('http://localhost:5000/api/users').json()['users']) == 0:
                    admin = 1
                post('http://localhost:5000/api/users', json={
                    'login': form.login.data,
                    'email': form.email.data,
                    'password': form.password.data,
                    'admin': admin},
                     timeout=(2, 20))
                user = session.query(User).filter(User.login == f'{form.login.data}').first()
                print(user)
                login_user(user, remember=form.remember_me.data)
                post('http://localhost:5000/api/log', json={
                    'type': 0,
                    'time': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                    'object_id': user.get_id(),
                    'owner_id': user.get_id(),
                    'description': 'Регистрация'},
                     timeout=(2, 20))
                return redirect("/")
            session.close()
    return render_template(
        'sign_up.html',
        title='Регистрация',
        form=form,
        message=message
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Authorize page for users
    """
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
                    'owner_id': user.get_id(),
                    'description': 'Успешная авторизация'
                },
                     timeout=(2, 20))
                return redirect(f"/user_profile/{user.id}")
            message = "Неправильный логин или пароль"
            if user:
                post('http://localhost:5000/api/log', json={
                    'type': 2,
                    'time': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                    'object_id': user.get_id(),
                    'owner_id': user.get_id(),
                    'description': 'Попытка входа в аккаунт'},
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
    """
    Rendering main page of website
    """
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
    """
    Renders user profile page
    :param user_id: id of user in base
    """
    if current_user.id != user_id:
        return abort(404)
    form = EditUserForm()
    user = get(f'http://localhost:5000/api/users/{user_id}', timeout=(2, 20)).json()['user']
    if request.method == 'POST':
        if form.validate_on_submit() and (form.login.data != '' or form.email.data != ''):
            put(f'http://localhost:5000/api/users/{current_user.id}', json={
                'login': form.login.data,
                'email': form.email.data,
                'admin': current_user.admin},
                timeout=(2, 20))
            post('http://localhost:5000/api/log', json={
                'type': 4,
                'time': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                'object_id': current_user.id,
                'owner_id': current_user.id,
                'description': 'Изменение своих личных данных'},
                 timeout=(2, 20))
            return redirect(f"/user_profile/{user_id}")
    form.email.data, form.login.data = user['email'], user['login']
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
    def convert_size(size_bytes: int) -> str:
        """
        Convert size of file from bytes to human-readable format
        :param size_bytes: size of file in bytes
        """
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    """Render files of current user
    :param user_id: id of user in base
    """
    if current_user.id != user_id:
        return abort(404)

    if request.method == 'POST':
        try:
            document = request.files['file']
            name_of_document = secure_filename(document.filename)
            document.save(f'./files/{name_of_document}')
            with open(f'./files/{name_of_document}', 'r', encoding='utf-8') as file:
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
                    'owner_id': user_id,
                    'description': f'Добавление файла: {name_of_document}'},
                     timeout=(2, 20))
            result = asyncio.run(manage(
                "add",
                doc['id'],
                name_of_document,
                get('http://localhost:5000/api/servers', json={}, timeout=(2, 20)).json()['servers'],
                file_folder="./files/"
            ))
            for v, k in result.items():
                if k == "OK":
                    post('http://localhost:5000/api/servers', json={
                        "file_id": doc['id'],
                        "host": v.split(":")[0],
                        "port": int(v.split(":")[1])
                    }, timeout=(2, 20))
            os.remove(f'./files/{name_of_document}')
        except PermissionError:
            pass

    if current_user.admin == 1:
        documents = get('http://localhost:5000/api/documents',
                        json={
                            "owner_id": user_id,
                            "name": "",
                            "size": 0,
                            "number_of_lines": 0,
                        },
                        timeout=(2, 20)).json()['documents']
    else:
        documents = get('http://localhost:5000/api/documents',
                        json={
                            "owner_id": user_id,
                            "flag": "user_id",
                            "name": "",
                            "size": 0,
                            "number_of_lines": 0,
                        },
                        timeout=(2, 20)).json()["documents"]

    search = request.args.get("search", "*")
    search = "*" + search + "*"
    if not search:
        search = "*"

    logging.debug(search)

    documents = list(filter(lambda x: fnmatch(x["name"], search), iter(documents)))
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

    for doc in documents:
        doc['size'] = convert_size(int(doc['size']))

    template = '/admin_pages/admin_table_files.html'
    if current_user.admin == 0:
        template = '/user_pages/user_table_files.html'

    return render_template(
        template,
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
        search=search,
    )


@app.route('/admin_server_table')
@login_required
def server_table():
    """Administrator page"""
    if current_user.admin == 1:
        servers = get('http://localhost:5000/api/servers', json={}, timeout=(2, 20)).json()['servers']

        search = request.args.get("search", "*")
        search = "*" + search + "*"
        servers = list(filter(lambda x: fnmatch(x["name"], search), iter(servers)))
        servers_ping = asyncio.run(manage(
            "ping", storages=servers
        ))
        for server in servers:
            server["ping"] = str(servers_ping[f"{server['host']}:{server['port']}"]) + " ms"

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
            search=search,
            username=get(f'http://localhost:5000/api/users/{current_user.id}',
                         timeout=(2, 20)).json()["user"]["login"],
        )
    return abort(404)


@app.route('/admin_user_table')
@login_required
def user_table():
    def convert_size(size_bytes: int) -> str:
        """
        Convert size of file from bytes to human-readable format
        :param size_bytes: size of file in bytes
        """
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    """Administrator page"""
    if current_user.admin == 1:
        users = get('http://localhost:5000/api/users', timeout=(2, 20)).json()['users']

        users = list(users)
        for user in users:
            user['activity'] = \
                get('http://localhost:5000/api/log', json={'owner_id': user['id']}, timeout=(2, 20)).json()['log'][-1][
                    'time']
            docs = get('http://localhost:5000/api/documents',
                       json={
                           "owner_id": user['id'],
                           "flag": "user_id",
                           "name": "",
                           "size": 0,
                           "number_of_lines": 0
                       },
                       timeout=(2, 20)).json()["documents"]
            user['size'] = convert_size(sum([int(document['size']) for document in docs]))
        pagination = request.args.get("pag")
        if pagination is None:
            pagination = 10
        else:
            pagination = int(pagination)
        total = len(users)
        page = int(request.args.get('page', 1))
        search = request.args.get("search", "*")
        if not search:
            search = "*"
        users = users[(page - 1) * pagination: min(total, page * pagination)]
        users = list(filter(lambda x: fnmatch(str(x['id']), search), users))
        next_p = min(page + 1, ceil(total / pagination))
        prev_p = max(page - 1, 1)

        return render_template(
            '/admin_pages/admin_table_users.html',
            user_id=current_user.id,
            users=users,
            current_page=page,
            pagination=pagination,
            total_docs=total,
            pages=list(range(1, ceil(total / pagination) + 1)),
            selected=pagination,
            next=next_p,
            prev=prev_p,
            total=total,
            username=get(f'http://localhost:5000/api/users/{current_user.id}',
                         timeout=(2, 20)).json()["user"]["login"],
        )
    return abort(404)


@app.route('/delete_document/<int:file_id>')
@login_required
def delete_file(file_id):
    """
    Api route to delete document from servers
    :param file_id: id of file in base
    """
    document = get(f'http://localhost:5000/api/documents/{file_id}', timeout=(2, 20)).json()
    if document['document']['owner_id'] == current_user.id or current_user.admin == 1:
        post('http://localhost:5000/api/log', json={
            'type': 7,
            'time': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            'object_id': file_id,
            'owner_id': current_user.get_id(),
            'description': f'Удаление файла: {document["document"]["name"]}'},
             timeout=(2, 20))
        delete(f'http://localhost:5000/api/documents/{file_id}', timeout=(2, 20))
        asyncio.run(manage(
            "delete",
            file_id,
            document['document']['name'],
            get('http://localhost:5000/api/servers', json={}, timeout=(2, 20)).json()['servers']
        ))
        return redirect(f'/user_table_files/{current_user.id}')
    return abort(404)


@app.route('/add_server', methods=['GET', 'POST'])
@login_required
def add_server():
    """
    Api route to add/edit server
    """
    if current_user.admin == 1:
        form = AddServerForm()
        if request.method == 'POST':
            if form.validate_on_submit():
                free, total = asyncio.run(manage(
                    "info", 0, "", [],
                    storage={"host": form.address.data, "port": int(form.port.data)}
                ))

                serv = post('http://localhost:5000/api/servers', json={
                    'name': form.name.data,
                    'host': form.address.data,
                    'port': form.port.data,
                    'capacity': total // (2 ** 30),
                    'ended_capacity': free // (2 ** 30)
                }, timeout=(2, 20)).json()['server']

                asyncio.run(manage(
                    "copy",
                    storages=get('http://localhost:5000/api/servers',
                                 json={'file_id': -1}, timeout=(2, 20)).json()['servers'],
                    storage={"host": form.address.data, "port": int(form.port.data)}
                ))

                post('http://localhost:5000/api/log', json={
                    'type': 8,
                    'time': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                    'object_id': serv['id'],
                    'owner_id': current_user.get_id(),
                    'description': f'Добавление сервера: {form.name.data}'},
                     timeout=(2, 20))

                return redirect('/admin_server_table')
        return render_template(
            '/admin_pages/add_server.html',
            form=form
        )
    return abort(404)


@app.route('/delete_server/<int:server_id>', methods=['GET', 'POST'])
@login_required
def delete_server(server_id):
    """
    Delete server from base
    :param server_id: id of storage in base
    """
    if current_user.admin == 1:
        storage = get(f'http://localhost:5000/api/servers/{server_id}',
                      timeout=(2, 20)).json()['server']
        asyncio.run(manage(
            "end", -1, "", [], storage=storage
        ))
        post('http://localhost:5000/api/log', json={
            'type': 9,
            'time': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            'object_id': server_id,
            'owner_id': current_user.get_id(),
            'description': f"Удаление сервера: {storage['name']}"},
             timeout=(2, 20))
        delete(f'http://localhost:5000/api/servers/{server_id}', timeout=(2, 20))
        return redirect('/admin_server_table')
    return abort(404)


@app.route('/edit_server/<int:server_id>', methods=['GET', 'POST'])
@login_required
def edit_server(server_id):
    """
    Edit server
    :param server_id: id of storage in base
    """
    message, form = '', AddServerForm()
    if current_user.admin == 1:
        server = get(f'http://localhost:5000/api/servers/{server_id}',
                     timeout=(2, 20)).json()['server']
        if request.method == 'POST':
            put(f'http://localhost:5000/api/servers/{server_id}',
                json={'name': form.name.data,
                      'host': form.address.data,
                      'port': form.port.data,
                      'ended_capacity': '',
                      'capacity': ''},
                timeout=(2, 20))
            server = get(f'http://localhost:5000/api/servers/{server_id}',
                         timeout=(2, 20)).json()['server']
            post('http://localhost:5000/api/log', json={
                'type': 11,
                'time': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                'object_id': server['id'],
                'owner_id': current_user.id,
                'description': f'Изменение сервера: {server["name"]}'},
                 timeout=(2, 20))
        session = db_session.create_session()
        documents = list(get(f'http://localhost:5000/api/documents', json={
                            "owner_id": "",
                            "flag": "",
                            "name": "",
                            "size": 0,
                            "number_of_lines": 0,
                        }, timeout=(2, 20)).json()['documents'])
        for document in documents:
            document['version'] = session.query(Versions).filter(Versions.server_id == server['id']).filter(Versions.file_id == document['id']).first().to_dict()['current_version']
        session.close()
        form.name.data = server['name']
        form.address.data = server['host']
        form.port.data = server['port']
        search = '*' + request.args.get("search", "*") + '*'
        if not search:
            search = "*"

        logging.debug(search)

        documents = list(filter(lambda x: fnmatch(x["name"], search), iter(documents)))
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
        return render_template('/admin_pages/about_server.html',
                               form_1=form,
                               message=message,
                               documents=documents,
                               current_page=page,
                               pagination=pagination,
                               total_docs=total,
                               pages=list(range(1, ceil(total / pagination) + 1)),
                               selected=pagination,
                               next=next_p,
                               prev=prev_p,
                               )
    return abort(404)


@app.route('/delete_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def delete_user(user_id):
    """
    Delete user from base
    :param user_id: id of storage in base
    """
    if current_user.admin == 1:
        storages = get('http://localhost:5000/api/servers', json={}, timeout=(2, 20)).json()['servers']
        files = get('http://localhost:5000/api/documents',
                    json={
                        "owner_id": user_id,
                        "flag": "user_id",
                        "name": "",
                        "size": 0,
                        "number_of_lines": 0,
                    },
                    timeout=(2, 20)).json()["documents"]
        for file in files:
            delete(f'http://localhost:5000/api/documents/{file["id"]}', timeout=(2, 20))
        delete(f'http://localhost:5000/api/users/{user_id}', timeout=(2, 20))
        asyncio.run(manage(
            "remove", storages=storages, files=files
        ))
        return redirect('/admin_user_table')
    return abort(404)


@app.route('/edit_document/<int:file_id>', methods=['GET', 'POST'])
@login_required
def edit_document(file_id):
    doc = get(f'http://localhost:5000/api/documents/{file_id}', timeout=(2, 20)).json()['document']
    if doc["owner_id"] != current_user.id and current_user.admin != 1:
        return abort(404)
    lines = [-1]

    if request.method == 'POST':
        try:
            document = request.files['file']
            name_of_document = doc['name']
            document.save(f'./files/{name_of_document}')
            with open(f'./files/{name_of_document}') as file:
                patch(f'http://localhost:5000/api/documents/{file_id}', json={
                    'name': name_of_document,
                    'version': doc['version'] + 1,
                    'owner_id': current_user.id,
                    'size': os.path.getsize(f'./files/{name_of_document}'),
                    'number_of_lines': len(file.readlines())},
                      timeout=(2, 20))
            result = asyncio.run(manage(
                "add",
                doc['id'],
                name_of_document,
                get('http://localhost:5000/api/servers', json={}, timeout=(2, 20)).json()['servers'],
                file_folder="./files/"
            ))
            for v, k in result.items():
                if k == "OK":
                    post('http://localhost:5000/api/servers', json={
                        "file_id": doc['id'],
                        "host": v.split(":")[0],
                        "port": int(v.split(":")[1])
                    }, timeout=(2, 20))
            os.remove(f'./files/{name_of_document}')
        except PermissionError:
            pass
        except KeyError:
            text = request.form['text'].replace('\r', '')
            with open("./files/local/" + doc['name'], 'w') as file:
                file.write(text)
            with open("./files/local/" + doc['name'], 'r') as file:
                patch(f'http://localhost:5000/api/documents/{file_id}', json={
                    'name': doc['name'],
                    'version': doc['version'] + 1,
                    'owner_id': current_user.id,
                    'size': os.path.getsize(f'./files/local/{doc["name"]}'),
                    'number_of_lines': len(file.readlines())},
                      timeout=(2, 20))
            result = asyncio.run(manage(
                "add", doc['id'], doc['name'],
                get('http://localhost:5000/api/servers', json={}, timeout=(2, 20)).json()['servers'],
                file_folder="./files/local/"
            ))
            for v, k in result.items():
                if k == "OK":
                    post('http://localhost:5000/api/servers', json={
                        "file_id": doc['id'],
                        "host": v.split(":")[0],
                        "port": int(v.split(":")[1])
                    }, timeout=(2, 20))

    asyncio.run(manage(
        "get", file_id, doc['name'],
        get('http://localhost:5000/api/servers', json={'file_id': doc['id']}, timeout=(2, 20)).json()['servers'],
        destination_folder="./files/local/"
    ))

    with open(f'./files/local/{doc["name"]}') as file:
        text = file.read()

    if request.method == 'GET':
        if request.args.get("substr") is not None:
            substr = request.args.get("substr")
            find_result = asyncio.run(manage(
                "find",
                file_id,
                doc['name'],
                get('http://localhost:5000/api/servers', json={'file_id': doc['id']}, timeout=(2, 20)).json()[
                    'servers'],
                substring=substr,
                lines=doc['number_of_lines'],
            ))
            rows = sorted(find_result)
            with open(f'./files/local/{doc["name"]}') as file:
                lines = file.readlines()

            # Apply row mask
            lines = [[i, substr,
                      Markup(f'<mark>{substr}</mark>'.join(lines[i - 1].split(substr)))]
                     for i in rows]

    os.remove(f'./files/local/{doc["name"]}')

    page = '/admin_pages/admin_work_with_file.html' if current_user.admin == 1 \
        else '/user_pages/user_work_with_file.html'
    if lines == [-1]:
        showtable = 1
    elif lines:
        showtable = 2
    else:
        showtable = 3
    return render_template(
        page,
        filename=Markup(f"<b>{doc['name']}</b>"),
        user_id=current_user.id,
        username=current_user.login,
        findlines=lines,
        showtable=showtable,
        text=text,
    )


@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.admin == 1 and current_user.id != user_id:
        user = get(f'http://localhost:5000/api/users/{user_id}', timeout=(2, 20)).json()['user']
        message, form = '', AdminEditUserForm(admin=user['admin'])
        if request.method == 'POST':
            if current_user.check_password(form.password.data):
                session = db_session.create_session()
                if session.query(User).filter(User.login == f'{form.login.data}').first() and form.login.data != user[
                    'login']:
                    message = "Этот логин уже существует"
                elif session.query(User).filter(User.email == f'{form.email.data}').first() and form.email.data != user[
                    'email']:
                    message = "Этот email уже привязан к аккаунту"
                else:
                    put(f'http://localhost:5000/api/users/{user_id}', json={
                        'login': form.login.data,
                        'email': form.email.data,
                        'admin': form.admin.data},
                        timeout=(2, 20))
                    post('http://localhost:5000/api/log', json={
                        'type': 4,
                        'time': datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                        'object_id': user_id,
                        'owner_id': current_user.id,
                        'description': f'Изменение данных пользователя: {user["login"]}'},
                         timeout=(2, 20))
                    user = get(f'http://localhost:5000/api/users/{user_id}', timeout=(2, 20)).json()['user']
                session.close()
            else:
                message = 'Неверный пароль'
        form.login.data = user['login']
        form.email.data = user['email']
        documents = get('http://localhost:5000/api/documents',
                        json={
                            "owner_id": user_id,
                            "flag": "user_id",
                            "name": "",
                            "size": 0,
                            "number_of_lines": 0,
                        },
                        timeout=(2, 20)).json()['documents']
        documents = list(documents)
        search = '*' + request.args.get("search", "*") + '*'
        if not search:
            search = "*"

        logging.debug(search)

        documents = list(filter(lambda x: fnmatch(x["name"], search), iter(documents)))
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

        logs = get('http://localhost:5000/api/log', json={'owner_id': user_id}, timeout=(2, 20)).json()['log']
        logs = list(logs)[::-1]
        pagination_1 = request.args.get("pag1")
        if pagination_1 is None:
            pagination_1 = 10
        else:
            pagination_1 = int(pagination_1)
        total_1 = len(logs)
        page_1 = int(request.args.get('page1', 1))
        logs = logs[(page_1 - 1) * pagination_1: min(total_1, page_1 * pagination_1)]
        next_p_1 = min(page_1 + 1, ceil(total_1 / pagination_1))
        prev_p_1 = max(page_1 - 1, 1)
        format_logs = []
        for log in logs:
            format_logs.append({'time': log['time'], 'info': log['description']})
        return render_template('/admin_pages/about_user.html',
                               title='Страница',
                               documents=documents,
                               logs=format_logs,
                               user_id=user_id,
                               current_page=page,
                               pagination=pagination,
                               total_docs=total,
                               pages=list(range(1, ceil(total / pagination) + 1)),
                               selected=pagination,
                               next=next_p,
                               prev=prev_p,
                               current_page_1=page_1,
                               pagination_1=pagination_1,
                               total_docs_1=total_1,
                               pages_1=list(range(1, ceil(total_1 / pagination_1) + 1)),
                               selected_1=pagination_1,
                               next_1=next_p_1,
                               prev_1=prev_p_1,
                               username=current_user.login,
                               form_1=form,
                               message=message
                               )


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s]: %(message)s',
        handlers=[logging.FileHandler("log"), logging.StreamHandler()],
        encoding='utf-8'
    )
    api.add_resource(UserListResource, '/api/users')
    api.add_resource(LogsListResource, '/api/log')
    api.add_resource(UserResource, '/api/users/<int:user_id>')
    api.add_resource(DocumentListResource, '/api/documents')
    api.add_resource(DocumentResource, '/api/documents/<int:document_id>')
    api.add_resource(ServerListResource, '/api/servers')
    api.add_resource(ServerResource, '/api/servers/<int:server_id>')
    db_session.global_init("data/data.db")
    # app.run(debug=True, host='0.0.0.0')
    http = WSGIServer(('0.0.0.0', 5000), app.wsgi_app)
    http.serve_forever()
