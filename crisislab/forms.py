from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FieldList, FormField, PasswordField
from wtforms.validators import DataRequired, Optional
#update this to a more robust/dynamic version if preferred
class DeleteTermForm(FlaskForm):
	term = SelectField('Secrets Term', choices=[('Keep'), ('Delete')])

class EditTermForm(FlaskForm):
	first_param = StringField('First Parameter')
	second_param = StringField('Second Parameter')
	third_param = StringField('Third Parameter')
	fourth_param = StringField('Fourth Parameter')
	fifth_param = StringField('Fifth Parameter')
	myTerms = FieldList(FormField(DeleteTermForm))

class AddCollectionForm(FlaskForm):
	addCollection = StringField('New Collection')

class customLoginForm(FlaskForm):
	username = StringField('Username')
	password = PasswordField('Password')

class athenaRunQuery(FlaskForm):
	queryName = SelectField('Query Name')
