current_terms and current_tasks are cache files to hold information pulled from AWS.  To avoid uneccesary calls to the API, data is stored here and accessed by the scripting to be fed to the html pages.

folders serves as a "metadata" for each term in the AWS Secrets Manager.  This is where the information is stored that shows which term is hosted in what folder.  This is purely for organizational purposes.

timestamp files hold the datetime that the last call to AWS was made, etc.  Various scripts reference these to determine whether or not to make a costly action (such as calling AWS)

secNode is the log data for failed login attempts.

banList is a list of banned IP address, recalculated during login.

suspectList is manually maintained to persistently block an IP address.  Used for when an attack is suspected, or if a certain location needs access blocked

athenaQueries and athenaQueryIDs store data related to Athena queries that have been run.  These files are cleaned to only hold data from the past 24 hours.

collectionStats is collection data pulled from Athena to show how many tweets each collection has found.  This is updated by the queryStats script, which is run every hour by a crontab.

collectionCreationDates store the creation dates for each collection (did I really need to type this).  This will be referenced by the website to give context to the number of tweets each collection has found.

