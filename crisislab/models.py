#do not modify this file unless specifically needed
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
	__tablename__ = 'user'

	username = db.Column(db.String, primary_key=True)
	password = db.Column(db.String)
	authenticated = db.Column(db.Boolean, default=False)

	def __repr__(self):
		return '<User %r>' % self.username

	def get_id(self):
		return self.username

	def is_authenticated(self):
		return self.authenticated

	def is_active(self):
		return True

	def is_anonymous(self):
		return False
