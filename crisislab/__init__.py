#basic initialization
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config.from_pyfile('config.py', silent=True)

#database initialization called by running __init__ directly
if __name__=='__main__':
	from models import User, db
	with app.app_context():
		db.init_app(app)
		db.create_all()

else:
	import crisislab.routes
