from flask_wtf import FlaskForm
from wtforms import EmailField, BooleanField, PasswordField, StringField
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    login = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField(label='Запомнить меня')


class SignUpForm(FlaskForm):
    login = StringField('Логин', validators=[DataRequired()])
    email = EmailField('eMail', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField(label='Запомнить меня')


class EditUserForm(FlaskForm):
    login = StringField('Логин')
    email = EmailField('eMail')
