from getpass import getpass
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import sys
from config import db_location

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = db_location
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)


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


def main():

	print('(A)dd or (r)emove users: ')
	pathPrint = input()
	if pathPrint.lower() == 'a' or pathPrint.lower() == 'add':
		print('Enter username: ')
		username = input()
		for char in username:
			if char == "_":
				print("'_' is not an allowed character.")
				exit()

		password = getpass()
		assert password == getpass('Password (again):')

		password = password.encode('utf-8')

		user = User(
			username=username,
			password=bcrypt.generate_password_hash(password).decode('utf-8')
		)
		db.session.add(user)
		db.session.commit()
		print('User added.')
	elif pathPrint.lower() == 'r' or pathPrint.lower() == 'remove':
		userList = db.session.execute("SELECT username FROM user").fetchall()
		userList = list(userList)
		print ('\nType the name of the user to delete.  Current users:')
		for user in userList:
			user = str(user)
			print(user[2:-3])
		print('')
		userDelInput = input()
		userDel = User.query.get(str(userDelInput))
		if userDel:
			db.session.delete(userDel)
			db.session.commit()
			print('Removed.')
		else:
			print('No such user.')
	else:
		print("Exit")
if __name__ == '__main__':
	sys.exit(main())
