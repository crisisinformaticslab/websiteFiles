from .config import file_path
from datetime import datetime
class SecurityNode:

	def logFailedLogin(ipaddress, username, err):
		username = list(username)
		for char in range(len(username)):
			if username[char] == '_':
				username[char] = '-'
		username = ''.join(username)
		file = open(file_path + "secNode.txt", "a")
		logline = ipaddress + "_" + username + "_" + err + "_" + str(datetime.now()) + "\n"
		file.write(logline)
		file.close()

	def scanLog():
		scanTime = datetime.now()
		file = open(file_path + "secNode.txt", "r")
		secLog = file.readlines()
		file.close()

		ipList = {}
		#userList = {}
		for line in secLog:
			dataSet = line.split('_')
			elapsedTime = scanTime - datetime.strptime(dataSet[3].rstrip(), '%Y-%m-%d %H:%M:%S.%f')
			if elapsedTime.days == 0:
				if dataSet[0] in ipList:
					ipList[dataSet[0]] += 1
				else:
					ipList[dataSet[0]] = 1
		banList = []
		for addr in ipList:
			if ipList[addr] >= 5:
				banList.append(addr)

		file = open(file_path + "banList.txt", "w")
		file.write( str(banList) )
		file.close()

		return banList

	def purgeLog():
		scanTime = datetime.now()
		file = open(file_path + "secNodeTimestamp.txt", "r")
		lastAudit = file.read()
		file.close()

		if (scanTime - datetime.strptime(lastAudit.rstrip(), '%Y-%m-%d %H:%M:%S.%f')).days > 7:
			file = open(file_path + "secNode.txt", "r")
			secLog = file.readlines()
			file.close()
			for line in secLog:
				dataSet = line.split('_')
				elapsedTime = scanTime - datetime.strptime(dataSet[3].rstrip(), '%Y-%m-%d %H:%M:%S.%f')
				if elapsedTime.days > 7:
					secLog.remove(line)

			file = open(file_path + "secNode.txt", "w")
			file.writelines(secLog)
			file.close()

			file = open(file_path + "secNodeTimestamp.txt", "w")
			file.write( str(scanTime) )
			file.close()
