incomingMap={}
outgoingMap={}
pollCount=0
pollTotal=0
currentVersion=0

def getOutgoingMap():
    global outgoingMap
    return outgoingMap

def setOutgoingMap(map):
    global outgoingMap
    outgoingMap=map

def getIncomingMap():
    global incomingMap
    return incomingMap

def setIncomingMap(map):
    global incomingMap
    incomingMap=map

def setIncomingMapElement(key,value):
    global incomingMap
    incomingMap[key]=value

def getPollCount():
    global pollCount
    return pollCount

def clearPollCount():
    global pollCount
    pollCount=0

def getPollTotal():
    global pollTotal
    return pollTotal

def setPollTotal(total):
    global pollTotal
    pollTotal=total

def bumpPoll():
    global pollCount,pollTotal
    pollCount+=1
    pollTotal+=1

def getCurrentVersion():
    global currentVersion
    return currentVersion

def setCurrentVersion(version):
    global currentVersion
    currentVersion=version

