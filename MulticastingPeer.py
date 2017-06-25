#Dimitris Bouris 1894 email: bourisdim@gmail.com

# Event-driven code that behaves as either a client or a server
# depending on the argument.  When acting as client, it connects 
# to a server and periodically sends an update message to it.  
# Each update is acked by the server.  When acting as server, it
# periodically accepts messages from connected clients.  Each
# message is followed by an acknowledgment.
#
# Tested with Python 2.7.8 and Twisted 14.0.2
#
from __future__ import division
import sys
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor
import  os,re
from orderedMulticast import TotalyOrderedMulticast,Message,AckMessage,DataMessage
from utilities.ConstantsMod import Constants as cons

class MessageReader(object):
	delim = Message.delim
	
	def getMessages(self, data):
		rawMessagesList = re.split(r'['+Message.delim+']', data)
		trimedMessagesList = [s for s in rawMessagesList if s.strip()]
		return self.parseListWithMessageObjects(trimedMessagesList)
	
	def parseListWithMessageObjects(self, trimedMessagesList):
		readMessages = list()
		for i in range(0, len(trimedMessagesList)):
			if(self.isAckMessage(trimedMessagesList[i])):
				m = self.createAckMessage(trimedMessagesList[i])
				readMessages.append(m)
			else:
				m = self.createDataMessage(trimedMessagesList[i])
				readMessages.append(m)
		return readMessages
	
	def isAckMessage(self, rawMessage):
		messageAtrs = re.split(r'[\s]', rawMessage)
		if messageAtrs[0] == 'ACK':
			return True
		return False
	
	def createAckMessage(self, rawMessage):
		messageAtrs = re.split(r'[\s]', rawMessage)
		timeStamp = float(messageAtrs[2])
		dataAcknowleged = messageAtrs[1]
		return  AckMessage(timeStamp, dataAcknowleged)
	
	def createDataMessage(self, rawMessage):
		messageAtrs = re.split(r'[\s]', rawMessage)
		timeStamp = float(messageAtrs[1])
		data = messageAtrs[0]
		return DataMessage(timeStamp, data)


	
class multicastingPeer(Protocol):

	acks = 0
	connected = False
	mReader = MessageReader()
	def __init__(self, factory):
		self.factory = factory
		
	def connectionMade(self):
		print 'Connection Established'
		self.connected = True
		self.factory.multicastMechanism.addPeer(self)
		
	def sendMessage(self, message):
		try:
			self.transport.write(str(message))
		except Exception, e:
			print e.args[0]

	def dataReceived(self, data):
		receivedMessages = self.mReader.getMessages(data)
		
		for i in range(0, len(receivedMessages)):
			self.factory.multicastMechanism.messageReceived(receivedMessages[i])
	
	def connectionLost(self, reason):
		print("Connection Lost")
		self.factory.multicastMechanism.removeConnectedPeer(self)
		self.factory.report()

	def done(self):
		self.factory.finished(self.acks)

class PeerFactory(ClientFactory): 

	def __init__(self, uniqueId, startingUnicodeInt, writeCallback, closeFileCallBack):
	#	print '@__init__'
		self.closeFileCallBack = closeFileCallBack
		self.multicastMechanism = TotalyOrderedMulticast(int(uniqueId), startingUnicodeInt, writeCallback, self.stopFactory)
		self.acks = 0
		self.fname = "server0"
	
	
	def finished(self, arg):
		self.acks = arg
		self.report()

	def report(self):
		self.multicastMechanism.showConnectedPeersInfo()

	def startFactory(self):
		print "@startFactory"
		self.fp = open(self.fname, 'w+')

	def stopFactory(self):
		#print "@stopFactory"
		self.fp.close()
		self.closeFileCallBack()

	def buildProtocol(self, addr):
		#print "@buildProtocol"
		protocol = multicastingPeer(self)
		return protocol
	
	   
class processFactory(object):
	def __init__(self, writeCallback, stopCallback):
		self.AM = cons.AM
		self.writeCallback = writeCallback
		self.stopCallback = stopCallback
		self.uniqueId = int(sys.argv[1])
		if self.uniqueId == 0:
			self.startProcess0()
		if self.uniqueId == 1:
			self.startProcess1()
		if self.uniqueId == 2:
			self.startProcess2()
  
	def startProcess0(self):
		self.factory = PeerFactory(str(self.uniqueId),\
								 cons.PROCESS1_START_ASCIIINT, self.writeCallback, self.stopCallback)
		self.port = self.AM + self.uniqueId
		reactor.listenTCP(self.port, self.factory)  
		print "Starting server at port: " + str(self.port)
		
	def startProcess1(self):
		self.factory = PeerFactory(str(self.uniqueId),\
								 cons.PROCESS2_START_ASCIIINT, self.writeCallback, self.stopCallback)
		self.host1 = sys.argv[2]
		self.port1 = self.AM + self.uniqueId - 1 
		reactor.connectTCP(self.host1, self.port1, self.factory)  
		
		self.port2 = self.AM + self.uniqueId
		reactor.listenTCP(self.port2, self.factory) 
		print "Process 1 Listens at port:" + str(self.port2) + " and connects at host " + self.host1 + " port:" + str(self.port1)
		
	def startProcess2(self):
		self.factory = PeerFactory(str(self.uniqueId),\
								 cons.PROCESS3_START_ASCIIINT, self.writeCallback, self.stopCallback)
		self.host1 = sys.argv[2]
		self.host2 = sys.argv[3]
		self.port1 = self.AM + self.uniqueId - 2  
		self.port2 = self.AM + self.uniqueId - 1
		reactor.connectTCP(self.host1, self.port1, self.factory) 
		reactor.connectTCP(self.host2, self.port2, self.factory) 	
		print"Process 0 Connects at: " + str(self.host1)+ ":" + str(self.port2) + " and " +str(self.host2)+":"+ str(self.port1)

	def stopPeerFactory(self):
		self.factory.stopFactory()
		
def getPathFromOs():
	return os.path.dirname(os.path.abspath(__file__))


if __name__ == '__main__':
	#global pFactory
	fileName = getPathFromOs() + "/Delivered-MessagesMod-" + str(sys.argv[1]) + ".txt"
	fileFd = open(fileName, cons.MODE)
	
	def writeMessageCallBack(message):

		print message.getMessageWthoutDelims()
		fileFd.write(message.getMessageWthoutDelims() + ' \n')
	
	def closeFileCallBack():
		fileFd.close()
		try:
			reactor.stop() 
		except Exception, e:
			return
	
	
	pFactory = processFactory(writeMessageCallBack, closeFileCallBack)

	reactor.run() 
