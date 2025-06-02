import os

def fileExists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False

def readFile(name):
    try:
        f=open(name,'r')
        value=f.read()
        f.close()
    except:
        value=None
    return value

def writeFile(name,text):
    f=open(name,'w')
    f.write(text)
    f.close()

def appendFile(name,text):
    f=open(name,'a')
    f.write(text)
    f.close()

def createDirectory(path):
    try:
        os.mkdir(path)
    except OSError as e:
        if e.args[0] != 17: return False
    return True

def clearFile(name):
    open(name,'w').close()

def deleteFile(file):
    try:
        os.remove(file)
        return True
    except: return False

def renameFile(oldName,newName):
    os.rename(oldName,newName)
