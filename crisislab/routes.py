from flask import Flask, render_template, redirect, request, url_for, flash, session
from flask_user import current_user, UserManager
from flask_login import LoginManager, login_required, login_user, logout_user
from flask_bcrypt import Bcrypt
from datetime import datetime
from crisislab import app
from .forms import EditTermForm, DeleteTermForm, AddCollectionForm, customLoginForm, athenaRunQuery
from .collection_manager import CollectionManager
from .aws_helper import AWShelper, security_stream, modification_stream, athena_stream
from .models import User, db
from .securityNode import SecurityNode
from .config import file_path, suspectList, authUserList
import json
import ast
import subprocess
import sys
from dateutil import tz

bcrypt = Bcrypt(app)
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
#user_manager = UserManager(app, db, User)
@app.route('/', methods=['GET'])
@login_required
def main():
#this is the main landing page after authentication through Nginx
	#initial checks.  Pull data from AWS (depending on timestamp checks), sync the folder system, and read text files to provide term, task, and folder information
	AWShelper.writeSecrets()
	currentTasks = AWShelper.getTasks()
	myDict = ast.literal_eval(AWShelper.getSecrets())
	CollectionManager.Sync(CollectionManager, myDict['TERMS'].split(';'))
	folderSystem = CollectionManager.readFile()
	#since currentTasks can be Null, rendering templates is easier if we provide two different return statements
	if currentTasks:
		return render_template('main.html', current_term=myDict['TERMS'], tasks=currentTasks['tasks'], folderSystem=folderSystem)
	else:
		return render_template('main.html', current_term=myDict['TERMS'], folderSystem=folderSystem)

@app.route('/login', methods=['GET', 'POST'])
def login():
#login page
	if request.environ.get('HTTP_X_REAL_IP', request.remote_addr) in suspectList:
		print("Access from suspect IP: " + request.environ.get('HTTP_X_REAL_IP', request.remote_addr))
		return "sysErr"
	SecurityNode.purgeLog()
	banList = SecurityNode.scanLog()
	#check for banned ip addresses.  These refresh every 24 hours
	if request.environ.get('HTTP_X_REAL_IP', request.remote_addr) in banList:
		return render_template('403.html'), 403
	form = customLoginForm()
	if form.validate_on_submit():
		user = User.query.get(form.username.data)
		#check password
		if user:
			if bcrypt.check_password_hash(user.password, form.password.data):
				user.authenticated = True
				db.session.add(user)
				db.session.commit()
				login_user(user, remember=False)
				session['username'] = form.username.data
				session.permanent = True
				AWShelper.putCloudWatchLogs(security_stream, "LOGGED IN - " + form.username.data + " - " + request.environ.get('HTTP_X_REAL_IP', request.remote_addr))

				return redirect(url_for('main'))
			else:
				print("FAILED LOGIN WITH INCORRECT PASSWORD <<>>: " + form.username.data)
				flash("Incorrect username/password combination", "userlogin")
				AWShelper.putCloudWatchLogs(security_stream, "Failed password - " + form.username.data + " - " + request.environ.get('HTTP_X_REAL_IP', request.remote_addr))
				SecurityNode.logFailedLogin(request.environ.get('HTTP_X_REAL_IP', request.remote_addr), form.username.data, "passErr")
				return redirect(url_for('login'))
		else:
			print("FAILED LOGIN WITH INCORRECT USERNAME: " + form.username.data)
			flash("Incorrect username/password combination", "userlogin")
			AWShelper.putCloudWatchLogs(security_stream, "No such username - " + form.username.data + " - " + request.environ.get('HTTP_X_REAL_IP', request.remote_addr))
			SecurityNode.logFailedLogin(request.environ.get('HTTP_X_REAL_IP', request.remote_addr), form.username.data, "nameErr")
			return redirect(url_for('login'))
	print("Login page accessed from " + request.environ.get('HTTP_X_REAL_IP', request.remote_addr))
	return render_template('login.html', form=form)

@app.route('/logout', methods=['GET'])
@login_required
def logout():
#not at all complicated.  This logs out the user
	user = current_user
	user.authenticated = False
	db.session.add(user)
	db.session.commit()
	logout_user()
	AWShelper.putCloudWatchLogs(security_stream, "LOGGED OUT - " + session['username'] + " - " + request.environ.get('HTTP_X_REAL_IP', request.remote_addr))
	flash('Successfully logged out, ' + session['username'], "userlogin")
	return redirect(url_for('login'))

@app.route('/addCollection', methods=['GET', 'POST'])
@login_required
def addNewCollection():
#landing page for adding a new collection
	form = AddCollectionForm()

	if request.method == 'GET':
		return render_template('addCollection.html', form=form)
	elif request.method == "POST":
		if form.addCollection.data:
			CollectionManager.createFolder(CollectionManager, form.addCollection.data)
			AWShelper.putCloudWatchLogs(modification_stream, "Add collection - " + form.addCollection.data + " - " + session['username'])
		return redirect(url_for('main'))

@app.route('/editCollection', methods=['GET'])
@login_required
def editCollection():
#information for a specfic collection
	folder = request.args.get('collection')
	folderSystem = CollectionManager.readFile()
	try:
		folderSystem = folderSystem[folder]
	except:
		flash("No such collection", "systemError")
		return redirect(url_for('main'))

	currentTasks = AWShelper.getTasks()
	if currentTasks is None:
		return render_template('editCollection.html', folderSystem=folderSystem, folderName=folder)
	else:
		return render_template('editCollection.html', folderSystem=folderSystem, currentTasks=currentTasks['tasks'], folderName=folder)

@app.route('/editCollection/editTerms', methods=['GET', 'POST'])
@login_required
def editTerms():
#either add new terms to the collection, or delete them
	folder = request.args.get('collection')
	folderSystem = CollectionManager.readFile()
	try:
		folderSystem = folderSystem[folder]
	except:
		flash("No such collection", systemError)
		return redirect(url_for('main'))

	currentTasks = AWShelper.getTasks()

	if request.method == 'GET':
		termDictionary = []
		for term in folderSystem:  #convert the list of strings to a list of dictionaries in order to
			tempDict = {"term": term}
			termDictionary.append(tempDict)

		if len(termDictionary) == 1 and termDictionary[0]['term'] == '':  #if there are no terms to delete
			form = EditTermForm()
		else:
                	form = EditTermForm(myTerms=termDictionary)

		return render_template('editTerms.html', folderSystem=folderSystem, currentTasks=currentTasks['tasks'], folderName=folder, form=form)

	elif request.method == 'POST':
		form = EditTermForm()
		#first we take the terms that already exist and weed out any ghosts.  Then we take inputs from the form data and append it to a new list (for debugging purposes).
		#The two lists are joined then reseparated into terms (input sanitization).  Duplicates are then parsed and weeded out, and finally the list is passed to the AWS Secrets Manager.
		#The user is then returned to the main page.
		termsListOrigin = ast.literal_eval(AWShelper.getSecrets())
		termsListOrigin = termsListOrigin['TERMS'].split(';')
		for term in termsListOrigin:
			if term == '':  #remove ghost elements (often an artifact created by deleting the last term in AWS)
				termsListOrigin.remove(term)
		termsListNew = []
		#parse the form data.  Edit this if a better form system is implemented.  The end result just needs to be that termsListNew is a list of each inputted term
		if form.first_param.data:
			termsListNew.append(form.first_param.data)
		if form.second_param.data:
			termsListNew.append(form.second_param.data)
		if form.third_param.data:
			termsListNew.append(form.third_param.data)
		if form.fourth_param.data:
			termsListNew.append(form.fourth_param.data)
		if form.fifth_param.data:
			termsListNew.append(form.fifth_param.data)

		#separate any terms added in multiples in a single line of the form (ex. '#term;#anotherterm')
		inputSanitization = ';'.join(termsListNew)
		termsListNew = inputSanitization.split(';')
		#check for and remove duplicates and ghosts
		for x in termsListOrigin:
			for y in termsListNew:
				if x == y or y == '':
					termsListNew.remove(y)

		fullTermsList = termsListOrigin + termsListNew  #the list of terms
		if len(termsListNew) > 0:
			AWShelper.putCloudWatchLogs(modification_stream, "Insert terms - " + str(termsListNew) + " -into- " + folder + " - " + session['username'])

		for term in termsListNew:
			CollectionManager.assignTerm(CollectionManager, folder, term)
		itemIterator = 0
		popList = [] #this is the list of terms marked for deletion
		for item in form.myTerms:
			if item.term.data == "Delete":
				popList.append(termsListOrigin[itemIterator])
			itemIterator += 1

		if len(popList) > 0:
			AWShelper.putCloudWatchLogs(modification_stream, "Delete terms - " + str(popList) + " -from- " + folder + " - " + session['username'])

		for term in popList: #for each term, remove it from the list
			fullTermsList.remove(term)
			CollectionManager.removeTerm(CollectionManager, term)

		newTermString = ';'.join(fullTermsList)
		AWShelper.updateSecrets(newTermString) #make the update in AWS
		#instead of using url_for, a direct redirect is used instead to manage the url
		return redirect(url_for('editCollection', collection=folder))

@app.route('/editCollection/editSpecificTerm', methods=['GET', 'POST'])
@login_required
def editSpecificTerm():
#edit the details of a specific term.  This can also be used for reassignment
	return "Nothing here yet"

@app.route('/deleteCollection', methods=['GET'])
@login_required
def deleteSpecificCollection():
	folder = request.args.get('collection')
	abandonedTerms = CollectionManager.deleteFolder(CollectionManager, folder);
	if abandonedTerms == "No such folder":
		flash("Collection delete error - " + folder, "systemError")
		return redirect(url_for('main'))

	currentTerms = ast.literal_eval(AWShelper.getSecrets())
	currentTerms = currentTerms['TERMS'].split(';')

	for term in abandonedTerms:
		currentTerms.remove(term)
	newTerms = ';'.join(currentTerms)
	AWShelper.updateSecrets(newTerms)
	AWShelper.putCloudWatchLogs(modification_stream, "Delete Collection - " + folder + " - " + session['username'])
	return redirect(url_for('main'))



@app.route('/athena', methods=['GET', 'POST'])
@login_required
def athena_main():
	form = athenaRunQuery()
	if request.method == 'GET':
		queryList = ['-Select Query-']
		myQueries = AWShelper.getAthenaQueries()
		if myQueries:
			for item in myQueries:
				queryList.append(item['Name'])
			form.queryName.choices = queryList
		collections = CollectionManager.collectionData(CollectionManager)
		file = open(file_path + "collectionCreationDates.txt", "r")
		contents = file.read()
		if contents:
			contents = ast.literal_eval(contents)
		file.close()
		if collections is not None:
			for collection in collections:
				if collection['name'] in contents:
					collection['date'] = contents[collection['name']]
				else:
					collection['date'] = "Unknown"

			return render_template('athena.html', query=myQueries, form=form, collections=collections)

		else:
			return render_template('athena.html', query=myQueries, form=form)

	elif request.method == 'POST':
		if form.queryName.data != "-Select Query-":
			executedQuery = AWShelper.runAthenaQuery(AWShelper, form.queryName.data)
			AWShelper.putCloudWatchLogs(athena_stream, "Ran query - " + form.queryName.data + " - " + session['username'])
			flash(executedQuery, "systemError") #not necessarily an error, but it gets put in that class for ease of organization
		else:
			flash ("-Select Query- is not a query to be selected.", "systemError")
		return redirect(url_for('athena_main'))

@app.route('/athena/viewQueries', methods=['GET', 'POST'])
@login_required
def athena_view():
	file = open(file_path + "athenaQueryIDs.txt", "r")
	queryLines = file.readlines()
	file.close()
	if len(queryLines) == 0:
		flash("No queries to view.  Please note results are deleted after 24 hours", "systemError")
		return redirect(url_for('athena_main'))
	queryExecutions = AWShelper.returnQueryExecution(queryLines, "initial")
	if queryExecutions is None:
		flash("No queries to view.  Please note results are deleted after 24 hours", "systemError")
		return redirect(url_for('athena_main'))

	queryData = []
	for item in queryExecutions['QueryExecutions']:
		if item['Status']['State'] == "SUCCEEDED":
			item['ResultData'] = AWShelper.returnQueryExecution(item['QueryExecutionId'], "results")
			#angela make changes here
		queryData.append(item)
	return render_template('athenaQueries.html', queryData=queryData)

@app.route('/athena/runCrawler', methods=['GET'])
@login_required
def runCrawler():
	if session['username'] in authUserList:
		pid = subprocess.Popen([sys.executable, "crisislab/forceCrawlerAndAthena.py"])
		flash ("Successfully executed - allow up to 15 minutes for processing", "systemError")
	else:
		flash("You lack the permissions to touch this button.  Do not touch this button.", "systemError")

	return redirect(url_for('athena_main'))

@app.route('/digitalvolunteer', methods=['GET'])
def redirectDigi():
	return redirect(url_for('athena_main'))
	#return redirect('http://127.0.0.1:8070')

@app.template_filter('formatdatetime')
def format_datetime(value, format="%d %b %Y %I:%M %p"):
#this is the converter function to make datetimes look pretty.  this takes the string datetime, converts it into a datetime object, assigns it to the timezone set on the EC2 instance, reformats it, and then returns it
	if value is None:
		return ""
	to_zone = tz.tzlocal() #this pulls the time zone from the EC2 (local)
	try:
		value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
	except ValueError as v: #common error with converting datetimes to strings
		if len(v.args) > 0 and v.args[0].startswith('unconverted data remains: '):
			value = value[:-(len(v.args[0]) - 26)] #this solution was found online.  not my own coding
			value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')

	newValue = value.astimezone(to_zone)
	return newValue.strftime(format)

@login_manager.user_loader
def user_loader(user_id):
#takes a user id, and returns the associated object
	return User.query.get(user_id)
