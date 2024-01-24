from flask_wtf import FlaskForm
from wtforms import EmailField, BooleanField, PasswordField, StringField, FileField
from wtforms.validators import DataRequired


class AddDocumentsForm(FlaskForm):
    content = FileField('Текстовый файл', validators=[DataRequired()])
