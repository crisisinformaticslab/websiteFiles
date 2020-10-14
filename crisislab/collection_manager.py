import json
import ast
from datetime import datetime, date
from .config import file_path
class CollectionManager:
#each print statement can be used for debugging as needed.  They hold no other purpose and can be commented out if desired
#each function that needs to call another function has "self" as one of its parameters.  The FolderManager class needs to be passed to these functions for them to work properly.

	def initialization(self):
	#initialization function for debugging
		folderSystem = self.readFile()
		print("CollectionManager initialization - " + str(folderSystem) )

	def readFile():
	#read the folders file, and return the encoded json
		file = open(file_path + "folders.txt", "r")
		contents = file.read()
		file.close()
		if contents:
			print("CollectionManager readFile")
			return json.loads(contents)
		else:
			print("CollectionManager noContentsRead")
			return ""

	def writeFile(folderSystem):
	#receive the new json folder system, and write it to the file.  This completely overwrites the previous contents
		file = open(file_path + "folders.txt", "w")
		file.write(json.dumps(folderSystem))
		file.close()
		print("CollectionManager writeFile")

	def assignTerm(self, folder, term):
	#the term is first removed from the system entirely to avoid duplicates.  Then, if the folder the term is being assigned to does not exist (via bug, glitch, etc), it creates the folder.
	#after the term has been both removed and the folder is confirmed to exist, the term is appended into that folder
		self.removeTerm(self, term)
		folderSystem = self.readFile()
		if folder not in folderSystem:
			folderSystem = self.createFolder(self, folder)
			folderSystem = self.readFile()
		folderSystem[folder].append(term)
		print("CollectionManager assign term [" + term + "] to folder [" + folder + "]")
		self.writeFile(folderSystem)

	def removeTerm(self, term):
	#parses the folder system and removes the specified term
		folderSystem = self.readFile()
		for folder in folderSystem:
			if term in folderSystem[folder]:
				folderSystem[folder].remove(term)
				print("CollectionManager removeTerm: " + term)
		self.writeFile(folderSystem)

	def createFolder(self, folder):
	#creates a new folder by the specified name if the folder does not already exist
		folderSystem = self.readFile()
		if folder not in folderSystem:
			folderSystem[folder] = []
			print("CollectionManager createFolder: " + folder)
			self.writeFile(folderSystem)
			file = open(file_path + "collectionCreationDates.txt", "r")
			contents = file.read()
			if contents:
				contents = ast.literal_eval(contents)
			else:
				contents = {}
			file.close()
			contents[folder] = str(date.today())
			file = open(file_path + "collectionCreationDates.txt", "w")
			file.write( str(contents) )
			file.close()
		else:
			print("CollectionManager createFolder failed - folder already exists")
		return folderSystem

	def deleteFolder(self, folder):
		#take all terms in the specified collection and add them to a "remove" list.  Then, remove the collection, and return the list.
		folderSystem = self.readFile()
		try:
			abandonedTerms = folderSystem[folder]
		except:
			return "No such folder"
		folderSystem.pop(folder)
		print("CollectionManager deleteFolder: " + folder)
		self.writeFile(folderSystem)
		file = open(file_path + "collectionCreationDates.txt", "r")
		contents = file.read()
		if contents:
			contents = ast.literal_eval(contents)
		file.close()
		if folder in contents:
			contents.pop(folder)
			file = open(file_path + "collectionCreationDates.txt", "w")
			file.write( str(contents) )
			file.truncate()
			file.close()
		return abandonedTerms

	def Sync(self, terms):
	#using the Secrets Manager as the ultimate authority, sync the terms inside of the folder system. This is crucial if the Secrets Manager was updated via the console and not the website.
		folderSystem = self.readFile()
		#if a term does not exist in the folder system, add it to "Unassigned"
		for secretsTerm in terms:
			if secretsTerm == '':
				continue
			inFolder = False
			for folder in folderSystem:
				for folderTerm in folderSystem[folder]:
					if folderTerm == secretsTerm:
						inFolder = True
			if not inFolder:
				self.assignTerm(self, "Err-SYNCED_TERM", secretsTerm)
				print("CollectionManager - Synced term not in folder - " + secretsTerm)

		#if a term in the folder system does not exist in Secrets Manager, remove it
		for folder in folderSystem:
			for folderTerm in folderSystem[folder]:
				inTerms = False
				for secretsTerm in terms:
					if folderTerm == secretsTerm:
						inTerms = True
				if not inTerms:
					self.removeTerm(self, folderTerm)
					print("CollectionManager - Synced term not in SecretsManager - " + folderTerm)

	def collectionData(self):
	#this function combines the currently active folders with their tweet count.  It is done this way to account for deleted collections between now and the time the Athena stats queries last ran
		folderSystem = self.readFile()
		file = open(file_path + "collectionStats.txt", "r")
		numberOfTweets = ast.literal_eval(file.read())
		file.close()
		collectionList = []
		for folder in folderSystem:
			if folder not in numberOfTweets:
				numberOfTweets[folder] = "--No Information--"
			collectionList.append({'name':folder, 'tweets':numberOfTweets[folder]})
		if len(collectionList) > 0:
			return collectionList
		else:
			return None
