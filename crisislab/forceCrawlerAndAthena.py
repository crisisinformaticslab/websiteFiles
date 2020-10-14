import boto3
import time
import subprocess
import sys
from config import aws_dict

client = boto3.client('glue')
crawler_name = aws_dict['crawler_name']
crawler_finished = False

print("Start Force Script")

initialCheck = client.get_crawler_metrics(
	CrawlerNameList=[crawler_name]
)['CrawlerMetricsList'][0]
if initialCheck['TimeLeftSeconds'] > 0 or initialCheck['StillEstimating'] == True:
	print("Force Exit")
	exit()

client.start_crawler(
	Name=crawler_name
)

while not crawler_finished:
	print("While loop")
	time.sleep(300)
	checkCrawler = client.get_crawler_metrics(
		CrawlerNameList=[crawler_name]
	)['CrawlerMetricsList'][0]
	if checkCrawler['TimeLeftSeconds'] == 0 and checkCrawler['StillEstimating'] == False:
		crawler_finished = True
print("Force crawler stopped - starting queryStats")

pid = subprocess.Popen([sys.executable, "crisislab/queryStats.py"])
