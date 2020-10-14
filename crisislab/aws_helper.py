import boto3
import json
from datetime import datetime, tzinfo
from .config import file_path, aws_dict
import time
from pytz import timezone

#these variables should be edited in the config file to reflect your own system.
#secret_id and cluster_name are your paths in AWS for your Secrets Manager and ECS
#workgroup is your designated workgroup in Athena
#file_path is the path leading to this folder.  Use pwd to make sure your filepath is correct (pulled from the config file)
#cloudwatch and the streams are for logging purposes, same with Athena and its database and stream
#readAWSDelay is how often you allow calls to be made to AWS.  This number should be low enough to provide usability to your team, and high enough to protect against malicious or accidental bill inflation.
#in addition to this delay buffer, I advise adding a CloudWatch on your AWS account to watch for bill inflation.
secret_id = aws_dict['secret_id']
cluster_name = aws_dict['cluster_name']
workgroup = aws_dict['workgroup']
cloudwatch_loggroup = aws_dict['cloudwatch_loggroup']
security_stream = aws_dict['security_stream']
modification_stream = aws_dict['modification_stream']
athena_stream = aws_dict['athena_stream']
athena_database = aws_dict['athena_database']

readAWSDelay = 5

class AWShelper:
	def timeInit():
	#if the timestamp files are empty, set them to current time
		timeFiles = ["secretsTimestamp.txt", "athenaTimestamp.txt", "secNodeTimestamp.txt"]
		for timeFile in timeFiles:
			file = open(file_path + timeFile, "r")
			contents = file.read()
			file.close()
			if contents == "":
				file = open(file_path + timeFile, "w")
				file.write( str(datetime.now()) )
				file.close()

	def writeSecrets():
	#this function writes the contents of the Secrets Manager to the current_terms file.  It only makes the call if the datetime in the timestamp file is more than readAWSDelay number of seconds old.
		requestTime = datetime.now()
		timeFile = open(file_path + "secretsTimestamp.txt", "r")
		contents = timeFile.read()
		timeFile.close()
		requestTimeDelta = (requestTime - datetime.strptime(contents, '%Y-%m-%d %H:%M:%S.%f'))  #this is the delta we are comparing against readAWSDelay

		if requestTimeDelta.seconds >= readAWSDelay:
			#read the Secrets Manager, and write to txt file
			client = boto3.client('secretsmanager')
			response = client.get_secret_value(
				SecretId=secret_id
			)
			print("AWSHelper - read Secrets from AWS")
			myDict = json.loads(response['SecretString'])

			w = open(file_path + "/current_terms.txt", "w")
			w.write( str(myDict) )
			w.truncate()
			w.close()
			print("AWSHelper - write to file")

	def getSecrets():
	#unrestricted file read to get the terms most recently pulled from the Secrets Manager
		file = open(file_path + "current_terms.txt", "r")
		contents = file.read()
		file.close()
		print("AWSHelper - read Secrets from file")

		return contents

	def updateSecrets(updateString):
	#called when terms have been changed, and makes the update to both AWS and the local text file
		requestTime = datetime.now()
		client = boto3.client('secretsmanager')
		client.update_secret(
			SecretId=secret_id,
			SecretString=json.dumps({"TERMS":updateString})
		)
		print("AWSHelper - write Secrets - <<<<<AWS CALL>>>>>")

		timeFile = open(file_path + "secretsTimestamp.txt", "w")
		timeFile.write( str(requestTime) )
		timeFile.close()
		termFile = open(file_path + "current_terms.txt", "w")
		termFile.write( str(json.dumps({"TERMS":updateString})) )
		termFile.close()

	def datetimeConverter(myObj):
	#conversion to allow json and datetimes to play nice without swearing at each other
		if isinstance(myObj, datetime):
			return myObj.__str__()


	def getTasks():
	#if the readAWSDelay condition is met, pull tasks from AWS ECS.  Then return the task file.
		requestTime = datetime.now()
		timeFile = open(file_path + "secretsTimestamp.txt", "r")
		contents = timeFile.read()
		timeFile.close()
		requestTimeDelta = (requestTime - datetime.strptime(contents, '%Y-%m-%d %H:%M:%S.%f'))

		if requestTimeDelta.seconds > readAWSDelay:
			client = boto3.client('ecs')
			response = client.list_tasks(
				cluster=cluster_name
			)
			print("AWSHelper - read Cluster Tasks - <<<<<AWS CALL>>>>>")
			#check if there are any tasks to actually read
			if response['taskArns']:
				currentTasks = client.describe_tasks(
					cluster=cluster_name,
					tasks=response['taskArns']
				)
				print("AWSHelper - read Task Descriptions - <<<<<AWS CALL>>>>>")
				file = open(file_path + "current_tasks.txt", "w")
				file.write( json.dumps(currentTasks, default=AWShelper.datetimeConverter) )
				file.close()
			else:
				print("AWSHelper - no tasks to be read")
				file = open(file_path + "current_tasks.txt", "w")
				file.write("") #reset the file to empty
				file.close()

			timeFile = open(file_path + "secretsTimestamp.txt", "w")
			timeFile.write( str(requestTime) )
			timeFile.close()
		#end the function by opening the file and reading contents.  Requiring all returned information to be pulled from the text file as opposed to being pulled directly from AWS allows code in
		#routes.py to handle standardized formatting of datetimes.  Trying to return raw json from AWS would require too much additional code to be worth it.
		file = open(file_path + "current_tasks.txt", "r")
		contents = file.read()
		file.close()
		if contents:
			return json.loads(contents)
		else:
			return None

	def getAthenaQueries():
	#gets and returns the current named queries saved in Athena
		requestTime = datetime.now()
		timeFile = open(file_path + "athenaTimestamp.txt", "r")
		contents = timeFile.read()
		timeFile.close()
		requestTimeDelta = (requestTime - datetime.strptime(contents, '%Y-%m-%d %H:%M:%S.%f'))

		if requestTimeDelta.seconds > readAWSDelay:  #checking the AWS delay before pulling information
			client = boto3.client('athena')
			named_query_list = client.list_named_queries(
				WorkGroup=workgroup
			)
			if len(named_query_list['NamedQueryIds']) > 0:
				myQueries = client.batch_get_named_query(
					NamedQueryIds=named_query_list['NamedQueryIds']
				)
				myQueries = myQueries['NamedQueries']
			else:
				myQueries = None
			timeFile = open(file_path + "athenaTimestamp.txt", "w")
			timeFile.write( str(requestTime) )
			timeFile.close()
			file = open(file_path + "athenaQueries.txt", "w")
			if myQueries:
				file.write( json.dumps(myQueries) )
			else:
				file.write("")
			file.close()
			return myQueries
		else:
			file = open(file_path + "athenaQueries.txt", "r")
			myQueries = file.read()
			file.close()
			if myQueries != "":
				return json.loads(myQueries)
			else:
				return None

	def runAthenaQuery(self, queryName):
	#function to run a saved query by a specified query name.  The id of the provisioned query is saved into a text file to be referenced by other other scripts
		availableQueries = self.getAthenaQueries()
		for query in availableQueries:
			if query['Name'] == queryName:
				client = boto3.client('athena')
				executionID = client.start_query_execution(
					QueryString=query['QueryString'],
					QueryExecutionContext={
						'Database': athena_database
					},
					WorkGroup=workgroup
				)
				file = open(file_path + "athenaQueryIDs.txt", "a")
				file.write(executionID['QueryExecutionId'] + '\n')
				file.close()

				return "Query started - check the query page for status and results"
		return "Err - query not found"

	def returnQueryExecution(queryIDs, method):
	#takes the execution IDs of queries and returns their status.  Also purges the id text file for anything over 24 hours old
		client = boto3.client('athena')
		if method == "initial":
			queryTime = datetime.now(timezone('UTC'))
			expiredList = []
			for line in range(len(queryIDs)):
				queryIDs[line] = queryIDs[line].rstrip()
			executionStates = client.batch_get_query_execution(
				QueryExecutionIds=queryIDs
			)
			for id in executionStates['QueryExecutions']:
				if (queryTime - id['Status']['SubmissionDateTime']).days > 1:
					executionStates['QueryExecutions'].remove(id)
					expiredList.append(id['QueryExecutionId'])
			if len(expiredList) > 0:
				file = open(file_path + "athenaQueryIDs.txt", "r+")
				contents = file.readlines()
				for line in contents:
					print(line)
					if line.rstrip('\n') in expiredList:
						contents.remove(line)
				file.seek(0)
				file.writelines(contents)
				file.truncate()
				file.close()

			if len(executionStates['QueryExecutions']) > 0:
				return executionStates
			else:
				return None

		elif method == "results":
		#returns the actual results of successfully finished queries
			executionResults = client.get_query_results(
				QueryExecutionId=queryIDs
			)
			return executionResults


	def putCloudWatchLogs(stream_name, message):
	#takes a stream and message, and pushes the log accordingly.


		activeLogging = True  #edit me to be either true/false to turn on/off logging
		#See above line if you want to deactivate logging

		if activeLogging:
			timestamp = int(datetime.now().timestamp() * 1000)
			client = boto3.client('logs')

			sequenceToken = client.describe_log_streams(
				logGroupName=cloudwatch_loggroup,
				logStreamNamePrefix=stream_name
				)
			sequenceToken = sequenceToken['logStreams']
			try:
				sequenceToken = sequenceToken[0]['uploadSequenceToken']
			except:
				sequenceToken = None
			if sequenceToken:
				client.put_log_events(
					logGroupName=cloudwatch_loggroup,
					logStreamName=stream_name,
					logEvents=[
						{
							'timestamp': timestamp,
							'message': message
						}
					],
					sequenceToken=sequenceToken
				)
			else:
				client.put_log_events(
					logGroupName=cloudwatch_loggroup,
					logStreamName=stream_name,
					logEvents=[
						{
							'timestamp': timestamp,
							'message': message
						}
					]
				)
