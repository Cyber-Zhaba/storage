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
from requests import get, post, delete, put
from forms.SignUpForm import SignUpForm, LoginForm
from data.user_service import UserResource, UserListResource

app = Flask(__name__)
api = Api(app)
login_manager = LoginManager(app)
login_manager.init_app(app)
app.config['SECRET_KEY'] = 'prev_prof_lovers_secret_key'


@app.errorhandler(404)
def not_found(error):
    print(error)
    return render_template('404.html')


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
    return render_template('main.html', title='Главная страница')


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    return render_template('profile.html', title='Главная страница')


@app.route('/user_profile', methods=['GET', 'POST'])
def user_profile():
    return render_template('user_profile.html', title='Главная страница')



if __name__ == '__main__':
    api.add_resource(UserListResource, '/api/users')
    api.add_resource(UserResource, '/api/<int:user_id>')
    db_session.global_init("data/data.db")
    app.run(debug=True, host='0.0.0.0')
