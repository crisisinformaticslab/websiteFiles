#configuration settings
import os
from datetime import timedelta

db_location = "sqlite:///../dbdir/crisislab.db"
file_path = "/home/flaskProjects/crisislab_master/crisislab/textFiles/"
aws_dict = {  #update this as needed to match your AWS account
	'secret_id':'prod/twitter/terms',
	'cluster_name':'twitter-ingest-cluster',
	'cloudwatch_loggroup':'EC2-WebApp',
	'security_stream':'WebApp - Authentication Logs',
	'modification_stream':'WebApp - Collection Edits',
	'athena_stream':'WebApp - Athena Queries',
	'athena_database':'crisislab-twitter-db',
	'workgroup':'Twitter-Group',
	'crawler_name':'crisislab-twitter-athenacrawler'
}

authUserList = [
	'ahughes',
	'ssundrud'
	]

file = open(file_path + "suspectList.txt", "r") #manually added banned IP addresses
suspectList = file.read()
file.close()


SQLALCHEMY_DATABASE_URI = db_location
SQLALCHEMY_TRACK_MODIFICATIONS = False
USER_EMAIL_SENDER_EMAIL = "none@none.com"
PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

#top line is for development, bottom is for production.  Comment/uncomment as needed ----------------<<<<<<<
#SECRET_KEY = "mysuperdupersecretkey"
SECRET_KEY = os.environ['SECRET_KEY']
