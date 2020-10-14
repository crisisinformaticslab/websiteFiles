#this python file should be the target for crontab, etc.  The folder it's hosted in may be renamed, but I do
#advise against renaming the "crisislab" folder inside of this one.

from flask import Flask
from crisislab import collection_manager, aws_helper, app
#app = Flask(__name__)

if __name__=='__main__':

	#from crisislab import app
	collection_manager.CollectionManager.initialization(collection_manager.CollectionManager)
	aws_helper.AWShelper.timeInit()
	app.config.from_pyfile('crisislab/config.py', silent=True)
	app.run(debug=True, ssl_context='adhoc')
