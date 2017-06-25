#DIMITRIS BOURIS 1894 email: bourisdim@gmail.com
'''
Created on Nov 3, 2015

@author: jimbouris 
'''
from __future__ import division
from abc import ABCMeta, abstractmethod 

from twisted.internet import reactor
import time, random
import heapq as heapq
from utilities.ConstantsMod import Constants as cons
from utilities.AsciiUtils import AsciiUtilities

class ConnectedPeers:

    def __init__(self):
        self.__peers = []

    def addProtocolToList(self, peer):
        self.__peers.append(peer)
        
    def removeProtocolFromList(self, peer):
        if self.__peers.__contains__(peer):
            self.__peers.remove(peer)     
    
    def showInfo(self):
        print "@Printing connected Peers"
        for peer in self.__peers:
            print "Peer: ", peer.transport.getPeer()
    
    def multicastMessageToEveryConnection(self, message):
        for peer in self.__peers:
            peer.sendMessage(message)
    
    def numberOfConnections(self):
        return len(self.__peers)
            
    
class Message(object):
    
    __metaclass__ = ABCMeta
    delim = '$'
    
    def __init__(self, timestamp, actualMessage):
        self.__timeStamp = timestamp
        self.__messageData = actualMessage
        
    def __str__(self):
        return self.messageData + " " + str(self.timeStamp) + self.delim ;
    
    @property
    def timeStamp(self):
        return self.__timeStamp
    @timeStamp.setter
    def timeStamp(self, time):
        self.__timeStamp = time
    
    @property
    def messageData(self):
        return self.__messageData
    @messageData.setter
    
    def messageData(self, actualMessage):
        self.__messageData = actualMessage
    
    def getMessageWthoutDelims(self):
        return str(self.timeStamp) + " " + self.messageData
    
    def printMessage(self):
        return str(self.timeStamp) + " " + self.messageData

    def __cmp__(self, other):
        return cmp(self.timeStamp, other.timeStamp)
    
    @abstractmethod
    def update(self, multMechanism): pass

        
class AckMessage(Message):
    
    def update(self, multMechanism):
        multMechanism.updateTime(self.timeStamp)  
	multMechanism.increaseTime()
        if self.isMyDataMessageInHeapIncreaseItsAcks(multMechanism) == True: 
            return
        multMechanism.appendUnknownAcks(self)
        
    def isMyDataMessageInHeapIncreaseItsAcks(self, multMechanism):    
        for dataM in multMechanism.getMessageList():
            if dataM.messageData == self.messageData:
                dataM.increaseAcks()
                if multMechanism.smallesMessageFullyAcked():
                    multMechanism.releaseHeadMessage()
                return True 
        return False
   
    def __str__(self):
        return self.delim + "ACK " + super(AckMessage, self).__str__()  
    

class DataMessage(Message):
    def __init__(self, timestamp, actualMessage):
        super(DataMessage, self).__init__(timestamp, actualMessage)
        self.__acks = 0
        
    @property
    def acks(self):
        return self.__acks
    @acks.setter
    def acks(self, ackNumber):
        self.__acks = ackNumber        
  
    def increaseAcks(self):
        self.acks += 1.0 

    def update(self, multMechanism):
        multMechanism.updateTime(self.timeStamp)  
        multMechanism.addIncomingMessageToList(self)
        multMechanism.increaseTime()   
        multMechanism.multicastAcknowlegment(self.getMyAckMessage(multMechanism.getTime()))  
        
    def __str__(self):
        return self.delim + super(DataMessage, self).__str__()
        
    def printMessage(self):
        print super(DataMessage, self).printMessage() + ' acks: ' + str(self.acks) 
        
    def getMyAckMessage(self, timeStamp):
        return AckMessage(timeStamp, self.messageData)
     
     
class TotalyOrderedMulticast(object):

    def __init__(self, uniqueId, asciiInt, writeCallback, stopFactoryCallback):
        self.callBackToWrite = writeCallback
        self.stopFactoryCallBack = stopFactoryCallback
        self.__clock = LampardClock(uniqueId)
        self._messageHeap = []
        self.__connectedPeers = ConnectedPeers()
        self.__unknownAcks = dict()
        self.__uniqueId = uniqueId
        self.__startingasciiInt = asciiInt
        self.__messagesReceived = 0

    def messageReceived(self, receivedMessage):
        receivedMessage.update(self)        
           
    def multicastMessage(self, asciiInt):
        self.increaseTime()
        message = DataMessage(self.__clock.time, AsciiUtilities.getasciiValue(asciiInt))
        self.addLocalMessageToList(message)
        self.__connectedPeers.multicastMessageToEveryConnection(message)   
        if self.sentAllMuslticastMessages(asciiInt + 1):
            reactor.callLater(5, self.checkHowManyMessagesReceived) 
        else:
            reactor.callLater(random.randint(2, 3), self.multicastMessage, asciiInt + 1)  
            
    def addLocalMessageToList(self, message):
        message.increaseAcks()
        heapq.heappush(self._messageHeap, message)
         
 
    def addIncomingMessageToList(self, message):
        if self.__unknownAcks.has_key(message.messageData):
            message.increaseAcks()
            del self.__unknownAcks[message.messageData] 
        message.increaseAcks()  
        message.increaseAcks()  
        heapq.heappush(self._messageHeap, message)  
                  
       
    def updateTime(self, messageTimeStamp):
        if messageTimeStamp > self.__clock.time:
            self.__clock.time = int(messageTimeStamp) + (self.__uniqueId / 10)
        
    def sentAllMuslticastMessages(self, asciiInt):
        if asciiInt == self.__startingasciiInt + cons.NUM_OFMESSAGES_PER_PROCESS:
            print "PROCESS STOPS MULTICASTING"
            return True
        return False
    
    def checkHowManyMessagesReceived(self):
        if self.smallesMessageFullyAcked():
            self.releaseHeadMessage()
        if self.__messagesReceived == cons.ALL_MESSAGES_INGROUP:
            self.stopFactoryCallBack()
        else:
            reactor.callLater(3, self.checkHowManyMessagesReceived) 

            
    def smallesMessageFullyAcked(self):
        if(len(self._messageHeap) > 0):
            if self._messageHeap[0].acks == cons.MAX_ACKS :
                return True
        
    def releaseHeadMessage(self): 
        headMessage = heapq.heappop(self._messageHeap)
        self.__messagesReceived += 1
        self.callBackToWrite(headMessage)
        
    def appendUnknownAcks(self, message):
        self.__unknownAcks[message.messageData] = True
       
    def multicastAcknowlegment(self, ackMessage):
        self.__connectedPeers.multicastMessageToEveryConnection(ackMessage)      

    def showConnectedPeersInfo(self):
        self.__connectedPeers.showInfo()
           
    def PrintQueuedMessages(self):
        print "PrintingHeap:"
        for m in self._messageHeap:
            m.printMessage() 
 
    def addPeer(self, peer):
        self.__connectedPeers.addProtocolToList(peer)
        if self.__connectedPeers.numberOfConnections() == cons.NUMBER_OFCONNECTIONS_TOSTARTMULT :
            print 'PROCESS ' + str(self.__uniqueId) + ' STARTS MULTICASTING'
            self.multicastMessage(self.__startingasciiInt)

    def getTime(self):
        return self.__clock.time
    
    def getMessageList(self):
        return self._messageHeap

    def removeConnectedPeer(self, peer):
        self.__connectedPeers.removeProtocolFromList(peer)
    
    def increaseTime(self):
        self.__clock.increase()
 
        
class LampardClock:
    def __init__(self, uniqueId):
        self.time = uniqueId / 10
    
    @property
    def time (self):
        return self.__time
    @time.setter
    def time(self, time):
        self.__time = time
    
    def increase(self):
        self.time += 1

