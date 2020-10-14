from config import file_path, aws_dict
import boto3
import time
from datetime import datetime
import ast

def ProvisionQuery(instanceQuery):
#this function is what calls Athena to start the statistics query
	client = boto3.client('athena')
	executionID = client.start_query_execution(
		QueryString=instanceQuery, #the instanceQuery is the string created from the main part of the code
		QueryExecutionContext={
			'Database': aws_dict['athena_database']
		},
		WorkGroup=aws_dict['workgroup']
	)
	return executionID #this id is the identifier used by Athena to keep track of queries.  We'll use this id later to ask if the query has completed, and what the results were

#three dictionaries to keep track of various parts of the query process.  This can be rewritten to be one single dictionary, but it was split up into three for troubleshooting purposes
queries = {}
queryStates = {}
results = {}

print("queryStats started")

file = open(file_path + "folders.txt", "r")  #get current collections
contents = file.read()
if contents: #if there is anything inside of the file, translate it to an object
	contents = ast.literal_eval(contents)
file.close()

queryString = 'SELECT COUNT (DISTINCT id) AS Collection FROM "2020" WHERE search_term '  #this is the base query that will be customized for each collection

for collection in contents:
	terms = contents[collection]
	if len(terms) is 1:
		instanceQuery = queryString + '= \'' + terms + '\''
	elif len(terms) > 1:
		instanceQuery = queryString + 'IN ('
		for term in terms:
			instanceQuery = instanceQuery + '\'' + term + '\','
		instanceQuery = instanceQuery[:-1] + ")"
	elif len(terms) is 0:
		continue
	id = ProvisionQuery(instanceQuery)['QueryExecutionId']  #provisions the query, then records the query id
	queries[id] = collection
	queryStates[id] = "Set"

finishedAllQueries = False
while not finishedAllQueries:
	time.sleep(15)  #this is the upper average time it takes for the queries to run.  this sleep command is used to allow the queries time to run fully
	queryList = []

	for query in queryStates:
		if queryStates[query] not in ['SUCCEEDED', 'FAILED', 'CANCELLED']:  #if we are still waiting on the results of a query, add it to the queryList list
			queryList.append(query)
	if len(queryList) > 0:  #if there are any queries we're still waiting on, call Athena to get their updated status
		client = boto3.client('athena')
		executionStates = client.batch_get_query_execution(
			QueryExecutionIds=queryList
		)
		for id in executionStates['QueryExecutions']:  #for each of the returned results, check if the query is completed.  Update the results dictionary accordingly
			queryStates[id['QueryExecutionId']] = id['Status']['State']
			if id['Status']['State'] == "SUCCEEDED":
				queryResults = client.get_query_results(
					QueryExecutionId=id['QueryExecutionId']
				)
				results[id['QueryExecutionId']] = queryResults['ResultSet']['Rows'][1]['Data'][0]['VarCharValue']
			elif id['Status']['State'] == "FAILED":
				results[id['QueryExecutionId']] = "Failed - " + id['Status']['StateChangeReason']
			elif id['Status']['State'] == "CANCELLED":
				results[id['QueryExecutionId']] = "CANCELLED"

		queryList = []
		for query in queryStates:  #check again to see if there are any queries we're still waiting on
			if queryStates[query] not in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
				queryList.append(query)
		if len(queryList) == 0:  #if we're done, then we're done!
			finishedAllQueries = True
	else:  #if there are no more queries that we're waiting on, exit the loop.  This is a safeguard in case the other condition returns a false positive
		finishedAllQueries = True

combinedData = {}  #this combines the useful data from the two other dictionaries
for collection in queries:
	combinedData[queries[collection]] = results[collection]
file = open(file_path + "collectionStats.txt", "w") #write the results to a text file that the server's scripts will reference
file.write( str(combinedData) )
file.truncate()
file.close()

