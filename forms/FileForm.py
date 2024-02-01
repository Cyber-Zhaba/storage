from flask_wtf import FlaskForm
from wtforms import FileField
from wtforms.validators import DataRequired


class AddDocumentsForm(FlaskForm):
    content = FileField('Текстовый файл', validators=[DataRequired()])
