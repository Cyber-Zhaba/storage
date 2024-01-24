from flask_wtf import FlaskForm
from wtforms import EmailField, BooleanField, PasswordField, StringField
from wtforms.validators import DataRequired


class AddServerForm(FlaskForm):
    name = StringField('Имя сервера', validators=[DataRequired()])
    address = StringField('Адрес Сервера', validators=[DataRequired()])
    port = StringField('Порт сервера', validators=[DataRequired()])