#!/usr/bin/python
import hashlib
import rospy
from std_msgs.msg import String
import re
import sched, time
import time
from time import sleep
from threading import Timer

nodeType = '-'
nodeID = '-'
targetNodeType = '-'
targetNodeID = '-'
nodeName = 'testNode'
targetTopic = '/transport'
connectedToTopic = False
pub = None
sub = None
lastMessage = ""

muteEnabled = False

testMessage = "3141022062(1,1.9544444444444444,0.8470588235294118,0.036680787756651845)ab8789e45d34efd7512e9f71d754793a7169f1e652f1f3f2827665db93eecc9b"



def Length3Digit(Length):
    if Length > 100:
        return (str(Length))
    elif Length > 10:
        return ('0' + str(Length))
    elif Length > 0:
        return ('00' + str(Length))

def createMessage(messageList):
    targetNodeType    = str(messageList[0])
    targetNodeID      = str(messageList[1])
    sourceNodeType    = str(messageList[2])
    sourceNodeID      = str(messageList[3])
    commandType       = str(messageList[4])
    commandData       = str(messageList[5])
    commandDataLength = Length3Digit(len(commandData))
    dataToCheckSum = targetNodeType + targetNodeID + sourceNodeType + sourceNodeID + commandType + commandDataLength + commandData
    m = hashlib.sha256()
    m.update(dataToCheckSum.encode("utf-8"))
    checksum = str(m.hexdigest())
    dataToCheckSum += checksum
    return dataToCheckSum

controlNodeMode = False
initControlNode = False
controlNodeUIPub = None
controlNodeUISub = None
controlNodeGeneralPub = None
controlNodeGeneralSub = None
controlNodeProcessPub = None
controlNodeProcessSub = None
controlNodeVisionPub = None
controlNodeVisionSub = None
controlNodeTransportPub = None
controlNodeTransportSub = None
transportNodeActive=False
transportActiveJob=[]
transportActiveJobIndex=0
jobSheet = []
lastMessageReference=dict()
toAcknowledgeMessages=[]

def sendMessage(inputData):
    behaviourChar = inputData[1]
    auxData = re.findall(":[a-zA-Z]*\)",inputData)
    auxData = auxData[1:-1]
    node = None
    try:
        node = int(behaviourChar) # behaviourChar is a number, indicating which node to go to next
        messageString = createMessage([4,1,5,1,"018","(1,"+str(node)+")"])
        # then send a message to the vision  node to find aa path to next node and guide robot there
        controlNodeVisionPub.publish(messageString)
    except ValueError:
        #behaviourChar is a char, an action for a specific node
        if behaviourChar == "g": # ie arm grab
            messageString = createMessage([3,1,5,1,"050",""])
            controlNodeTransportPub.publish(messageString)
        if behaviourChar == "d": # ie arm drop
            messageString = createMessage([3,1,5,1,"051",""])
            controlNodeTransportPub.publish(messageString)
        if behaviourChar == "p": # ie process node shape instruction
            messageString = createMessage([3,1,5,1,"040",auxData])
            controlNodeProcessPub.publish(messageString)
        if behaviourChar == "h": # ie activate hole node
            messageString = createMessage([6,1,5,1,"054",""])
            controlNodeProcessPub.publish(messageString)

def UICallback(data):
    inputString = data.data
    if controlNodeMode == True: # get your data out
        targetNodeType = inputString[0]
        targetNodeID = inputString[1]
        sourceNodeType = inputString[2]
        sourceNodeID = inputString[3]
        commandType = inputString[4:7]
        commandDataLength = int(inputString[7:10])
        commandData = inputString[10:(10+commandDataLength)]
        dataToCheckSum = inputString[:(10+commandDataLength)]
        checksum = inputString[(10+commandDataLength):]
        # get data, validate
        m = hashlib.sha256()
        m.update(dataToCheckSum.encode("utf-8"))
        hashResult = str(m.hexdigest())
        if(hashResult == checksum and (targetNodeType==5 or targetNodeType==0)): # check the message is valid and for me
            #if seenBefore == False: # ie assuming we haven't aready acted on this message
            if commandType == "006": # ie is the UI give the system a new job
                shapesMask=[0,1,2,3]
                holeMask=4
                #emailMask=range(5,commandDataLength)
                #commandData
                shapes = [] # should be numebrs corresponding to position
                for i in shapesMask:
                    if(commandData[i] != 'N'):
                        shapes.append(commandData[i])

                hole = True if (commandData[holeMask]=='H') else False
                email = str(commandData[5:commandDataLength])

                # # Work out the path based on the specifications
                path = []
                path.append("(7:True)") # send first to materials hopper
                path.append("(g:true)") # grab materials from
                if len(shapes) > 0:
                    path.append("(1:true)") # to the path, append a node and its job id's in brackets, with an instruction for arm to drop and grab after
                    path.append("(d:true)")
                    for shape in shapes:#instruct process node to do a thing
                        path.append("(p:"+str(shape)+")")
                    path.append("(g:true)")
                if(hole==True):
                    path.append("(6:True)(d:true)(h:true)(g:true)") # send to "hole" node
                path.append("(8:True)(d:true)") # send to finish bucket
                jobsheet.append(path)
                #
                if transportNodeActive == False and len(jobsheet)==1:
                    transportActiveJob=jobsheet[0] # get oldest job from jobsheet, save to active
                    jobsheet.remove(0) # remove it from job sheet
                    transportNodeActive = True # set node to active
                    transportActiveJobIndex=0
                    #send a message here to vision node to send transportActiveJobIndex path to transport
                    nodeJobSlots=re.findall("\([0-9gdph]:[a-zA-Z]*\)*",transportActiveJob) # 0-9 for nodes, gd for grab drop on arm, p for process then shape,h for hole
                    nextNode = nodeJobSlots[transportActiveJobIndex][1]
                    # this is new job, so should write to an RFID reader first!
                    messageString =  createMessage([9,1,5,1,"048",email])
                    time.sleep(1) # sleep one second to ensure data is writen

                    sendMessage(nextNode)# send message here

                    if (len(nodeJobSlots))==transportActiveJobIndex: # ie are we past the last task for that work peice
                        transportActiveJobIndex =0
                        transportNodeActive == False
                    else:
                        transportActiveJobIndex += 1


            if commandType == "003": #ie stop production
                pass


def platformCallback(data):
    inputString = data.data
    if controlNodeMode == True: # get your data out
        targetNodeType = inputString[0]
        targetNodeID = inputString[1]
        sourceNodeType = inputString[2]
        sourceNodeID = inputString[3]
        commandType = inputString[4:7]
        commandDataLength = int(inputString[7:10])
        commandData = inputString[10:(10+commandDataLength)]
        dataToCheckSum = inputString[:(10+commandDataLength)]
        checksum = inputString[(10+commandDataLength):]
        # get data, validate
        m = hashlib.sha256()
        m.update(dataToCheckSum.encode("utf-8"))
        hashResult = str(m.hexdigest())
        if(hashResult == checksum and (targetNodeType==5 or targetNodeType==0)): # check the message is valid and for me
            if commandType == "043":# ie has the platform just finished what it was doing?
                #send a message here to vision node to send transportActiveJobIndex path to transport
                nodeJobSlots=re.findall("\([0-9]:[a-zA-Z]*\)*",transportActiveJob)
                nextNode = nodeJobSlots[transportActiveJobIndex][1]
                if (len(nodeJobSlots))!=transportActiveJobIndex: # ie we're currently not past the last slot on the job
                    sendMessage(nextNode)# send message here

                    transportActiveJobIndex += 1

                else: # thatw as the last job on the sheet
                    transportActiveJobIndex =0
                    transportNodeActive == False # ok we've finished this job
                    # check for new tasks here?
                    if(len(jobsheet) > 0): # if another job on the jobsheet
                        transportActiveJob=jobsheet[0] # get oldest job from jobsheet, save to active
                        jobsheet.remove(0) # remove it from job sheet
                        transportNodeActive = True # set node to active
                        transportActiveJobIndex=0 # set current index to 0
                        nodeJobSlots=re.findall("\([0-9]:[a-zA-Z]*\)*",transportActiveJob) # convert string job sheet to list of nodes
                        nextNode = nodeJobSlots[transportActiveJobIndex][1] # get next processing node
                        sendMessage(nextNode)# send message here
                        transportActiveJobIndex += 1

def processingNodeCallback(data):
        inputString = data.data
        if controlNodeMode == True: # get your data out
            targetNodeType = inputString[0]
            targetNodeID = inputString[1]
            sourceNodeType = inputString[2]
            sourceNodeID = inputString[3]
            commandType = inputString[4:7]
            commandDataLength = int(inputString[7:10])
            commandData = inputString[10:(10+commandDataLength)]
            dataToCheckSum = inputString[:(10+commandDataLength)]
            checksum = inputString[(10+commandDataLength):]
            # get data, validate
            m = hashlib.sha256()
            m.update(dataToCheckSum.encode("utf-8"))
            hashResult = str(m.hexdigest())
            if(hashResult == checksum and (targetNodeType==5 or targetNodeType==0)): # check the message is valid and for me
                if commandType == "043":# ie has the platform just finished what it was doing?
                    #send a message here to vision node to send transportActiveJobIndex path to transport
                    nodeJobSlots=re.findall("\([0-9]:[a-zA-Z]*\)*",transportActiveJob)
                    nextNode = nodeJobSlots[transportActiveJobIndex][1]
                    if (len(nodeJobSlots))!=transportActiveJobIndex: # ie we're currently not past the last slot on the job
                        sendMessage(nextNode)# send message here

                        transportActiveJobIndex += 1

                    else: # thatw as the last job on the sheet
                        transportActiveJobIndex =0
                        transportNodeActive == False # ok we've finished this job
                        # check for new tasks here?
                        if(len(jobsheet) > 0): # if another job on the jobsheet
                            transportActiveJob=jobsheet[0] # get oldest job from jobsheet, save to active
                            jobsheet.remove(0) # remove it from job sheet
                            transportNodeActive = True # set node to active
                            transportActiveJobIndex=0 # set current index to 0
                            nodeJobSlots=re.findall("\([0-9]:[a-zA-Z]*\)*",transportActiveJob) # convert string job sheet to list of nodes
                            nextNode = nodeJobSlots[transportActiveJobIndex][1] # get next processing node
                            sendMessage(nextNode)# send message here# send message here
                            transportActiveJobIndex += 1


def visionNodeCallback():
    pass


def receiveMessage(data):
    if muteEnabled == False:
        ## get message
        inputString = data.data
        if type(inputString) == type("testString"):
            # echo message
            if(inputString != lastMessage):
                print("")
                print("new message from \"{}\"".format(targetTopic))
                print(inputString)
                # check structure
                if(len(inputString) > 11):
                    targetNodeType = inputString[0]
                    print("targetNodeType: {}".format(targetNodeType))
                    targetNodeID = inputString[1]
                    print("targetNodeID {}".format(targetNodeID))
                    sourceNodeType = inputString[2]
                    print("sourceNodeType {}".format(sourceNodeType))
                    sourceNodeID = inputString[3]
                    print("sourceNodeID {}".format(sourceNodeID))
                    commandType = inputString[4:7]
                    print("commandType {}".format(commandType))
                    commandDataLength = int(inputString[7:10])
                    print("commandDataLength {}".format(commandDataLength))
                    commandData = inputString[10:(10+commandDataLength)]
                    dataToCheckSum = inputString[:(10+commandDataLength)]
                    if(len(inputString) == (10+64+commandDataLength)):
                        print("commandData {}".format(commandData))

                        checksum = inputString[(10+commandDataLength):]
                        m = hashlib.sha256()
                        m.update(dataToCheckSum.encode("utf-8"))
                        hashResult = str(m.hexdigest())
                        print("checksum {}".format(checksum))
                        if(hashResult != checksum):
                            print("aaaah fuck theres a problem, print everything")
                            print(targetNodeType)
                            print(targetNodeID)
                            print(sourceNodeType)
                            print(sourceNodeID)
                            print(commandData)
                            print("received checksum: {}".format(checksum))
                            print("calculated checksum: {}".format(hashResult))
                        else:
                            print("message clean")
                        #print(">>")
                    else:
                        print("received data too short")
                        print("actualLength {}".format(len(inputString)))
                else:
                    print("received data too short")
            else:
                print("sent message received on topic")
        else:
            print("recived data incorrect type, ie not string")

while (True):
    inputString = raw_input(">>")
    dealtWith = 0

    if (inputString == "controlNodeToggle" and dealtWith == 0):
        dealtWith = 1
        if(controlNodeMode == True):
            print("Control Node deactivated")
            controlNodeMode = False
        else:
            print("Control Node activated")
            controlNodeMode = True
            if initControlNode == False:
                controlNodeVisionPub = rospy.Publisher("/vision", String, queue_size=10)
                controlNodeUIPub = rospy.Publisher("/UI", String, queue_size=10)
                controlNodeGeneralPub = rospy.Publisher("/system", String, queue_size=10)
                controlNodeTransportPub = rospy.Publisher("/transport", String, queue_size=10)
                controlNodeProcessPub = rospy.Publisher("/process", String, queue_size=10)
                rospy.init_node("controlNode",anonymous=True)
                controlNodeProcessSub = rospy.Subscriber("/process", String, processingNodeCallback)
                controlNodeVisionPub = rospy.Subscriber("/vision", String, visionNodeCallback)
                controlNodeUIPub = rospy.Subscriber("/UI", String, UICallback)
                controlNodeGeneralSub = rospy.Subscriber("/system", String, receiveMessage)
                controlNodeTransportSub = rospy.Subscriber("/transport", String, platformCallback)
                initControlNode = True
                print("Control node initialised")

    if (inputString == "sendBlocks" and dealtWith == 0):
        dealtWith = 1
        print("source/dest address, command type")
        blockA = raw_input(">>>")
        print("Data")
        blockB = raw_input(">>>")
        stringToSend = blockA + Length3Digit(len(blockB)) + blockB
        m = hashlib.sha256()
        m.update(stringToSend.encode("utf-8"))
        hashResult = str(m.hexdigest())
        stringToSend = stringToSend + str(hashResult)
        #stringToSend = "complete me!"
        pub.publish(stringToSend)

    if (inputString == "sendMessage" and dealtWith == 0):
        dealtWith = 1
        if nodeType == '-':
            print("please set local node type first")
            continue

        if nodeID == '-':
            print("please set local node type first")
            continue

        targetNodeTypeTemp = False
        if(targetNodeType == '-'):
            targetNodeTypeTemp = True
            print("target node type")
            targetNodeType = int(raw_input(">>>>"))
            if(targetNodeType < 0 or targetNodeType > 9):
                print("not a valid input (true values between 0 and 9)")
                continue
        else:
            print("using already set targetNodeType: {}".format(targetNodeType))

        targetNodeIDTemp = False
        if(targetNodeID == '-'):
            targetNodeIDTemp = True
            print("target node ID")
            targetNodeID = int(raw_input(">>>>"))
            if(targetNodeID < 0 or targetNodeID > 9):
                print("not a valid input (true values between 0 and 9)")
                continue
        else:
            print("using already set targetNodeID: {}".format(targetNodeID))


        print("header def (command type)")
        headerDefInputString = int(raw_input(">>"))
        if(headerDefInputString < 0 or headerDefInputString > 999):
            print("not a valid input (true values between 0 and 999)")
            continue
        #check this is number
        print("data String")
        dataStringInputString = raw_input(">>")

        #check this is number
        stringToSend = str(targetNodeType)+str(targetNodeID)+str(nodeType)+str(nodeID)
        stringToSend = stringToSend+str(headerDefInputString)+Length3Digit(len(dataStringInputString))+dataStringInputString

        m = hashlib.sha256()
        m.update(stringToSend.encode("utf-8"))
        hashResult = str(m.hexdigest())
        stringToSend = stringToSend + str(hashResult)
        #stringToSend = "complete me!"
        pub.publish(stringToSend)
        if(targetNodeTypeTemp == True):
            targetNodeType = '-'
        if(targetNodeIDTemp == True):
            targetNodeID = '-'

    if (inputString == "sendTest" and dealtWith == 0):
        dealtWith = 1
        stringToSend = testMessage
        pub.publish(stringToSend)

    if (inputString == "setNodeType" and dealtWith == 0):
        print("set node type: (use \"-\" as null entry)")
        nodeTypeInputString = int(raw_input(">>>>"))
        if(nodeTypeInputString < 0 or nodeTypeInputString > 9):
            print("not a valid input (true values between 0 and 9)")
            continue
        dealtWith = 1

    if (inputString == "setNodeID" and dealtWith == 0):
        print("set node ID: (use \"-\" as null entry)")
        nodeTypeInputString = int(raw_input(">>>>"))
        if(nodeTypeInputString < 0 or nodeTypeInputString > 9):
            print("not a valid input (true values between 0 and 9)")
            continue
        dealtWith = 1

    if (inputString == "connectTopic" and dealtWith == 0):
        if targetTopic != "-":
            if connectedToTopic == False:
                pub = rospy.Publisher(targetTopic, String, queue_size=10)
                rospy.init_node(nodeName)
                sub = rospy.Subscriber(targetTopic, String, receiveMessage)
                connectedToTopic = True
                pass
            else:
                print("Already connected to topic {}".format(targetTopic))
        else:
            print("Please set topic name")
        dealtWith = 1
        pass

    if (inputString == "disconnectTopic" and dealtWith == 0):
        if connectedToTopic == True:
            sub.unregister()
            #sub = None
            pub.unregister()
            #pub = None
            connectedToTopic = False
            pass
        else:
            print("Already diconnected from topic")
        dealtWith = 1
        pass

    if (inputString == "setTopic" and dealtWith == 0):
        if connectedToTopic == False:
            print("type name of topic to connect to, eg '/control' ")
            print("type '-' to cancel or leave blank")
            inputString = raw_input(">>>>")
            if(inputString != ''):
                targetTopic = inputString
            else:
                pass
        else:
            print("currently connected to a topic, please disconnect first")
        dealtWith = 1
        pass

    if (inputString == "mute" and dealtWith == 0):
        muteEnabled = True
        dealtWith = 1
        pass

    if (inputString == "unmute" and dealtWith == 0):
        muteEnabled = False
        dealtWith = 1
        pass

    if (inputString == "help" and dealtWith == 0):
        commandsList = ['help', 'setTopic', 'disconnectTopic', 'connectTopic', 'sendMessage', 'controlNodeToggle', 'sendBlocks', 'sendTest', 'setNodeType', 'setNodeID', 'connectTopic', 'disconnectTopic', 'mute', 'unmute', 'exit']
        for command in commandsList:
            print(command)
        dealtWith = 1
        pass

    if (inputString == "exit" and dealtWith == 0):
        print("Exiting")
        if pub != None:
            sub.unregister()
            pub.unregister()
        dealtWith = 1
        break;

    if (inputString == "" and dealtWith == 0):
        dealtWith = 1

    if (dealtWith == 0):
        print("Input not recognised")
        dealtWith = 1
