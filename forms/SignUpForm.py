from flask_wtf import FlaskForm
from wtforms import EmailField, BooleanField, PasswordField, StringField
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    login = StringField('Login', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember me')


class SignUpForm(FlaskForm):
    login = StringField('Login', validators=[DataRequired()])
    email = EmailField('eMail', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember me')
