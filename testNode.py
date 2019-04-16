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
            #check previous log of messages for similarity
            seenBefore=False
            #lastMessage = None
            try:
                lastMessage = lastMessageReference[sourceNodeType+sourceNodeID]
                if lastMessage == inputString:
                    seenBefore = True # we've seen the message before, warn the proceeding code
                else:
                    lastMessageReference[sourceNodeType+sourceNodeID] = inputString # we haven't seen this message before, record it
            except KeyError:
                lastMessageReference[sourceNodeType+sourceNodeID] = inputString
            # send ack
            messageData=[sourceNodeType,sourceNodeID,targetNodeType,targetNodeID,"000",""]
            messageString = sendMessage(messageData)
            controlNodeUIPub.publish(messageString)
            if seenBefore == False: # ie assuming we haven't aready acted on this message
                if commandType == "006": # ie is the UI give the system a new job
                    shapesMask=[0,1,2,3]
                    holeMask=4
                    #commandData
                    shapes = [] # should be numebrs corresponding to position
                    for i in shapesMask:
                        if(commandData[i] != 'N'):
                            shapes.append(commandData[i])

                    hole = True if (commandData[holeMask]=='H') else False

                    # # Work out the path based on the specifications
                    path = []
                    path.append("(7:True)") #
                    if len(shapes) > 0:
                        path.append("(1:"+''.join(shapes)+")") # to the path, append a node and its job id's in brackets
                    if(hole==True):
                        path.append("(6:True)")
                    path.append("(8:True)")
                    # prehaps append data regarding user who ordered?
                    # # append user/job data to the job
                    # # store path to big vector,
                    jobsheet.append(path)
                    #
                    if transportNodeActive == False and len(jobsheet)==1:
                        transportActiveJob=jobsheet[0] # get oldest job from jobsheet, save to active
                        jobsheet.remove(0) # remove it from job sheet
                        transportNodeActive = True # set node to active
                        transportActiveJobIndex=0
                        #send a message here to vision node to send transportActiveJobIndex path to transport
                        nodeJobSlots=re.findall("\([0-9]:[a-zA-Z]*\)*",transportActiveJob)
                        nextProcessingNode = nodeJobSlots[transportActiveJobIndex][1]
                        if (len(nodeJobSlots)-1)==transportActiveJobIndex: # ie are we on the last task for that work peice
                            transportActiveJobIndex =0
                            transportNodeActive == False
                        else:
                            transportActiveJobIndex += 1
                        messageString =  createMessage([4,1,5,1,"018","(1,"+str(nextProcessingNode)+")"])
                        controlNodeVisionPub.publish(messageString)
                        messageToAck = [int(round(time.time() * 1000)), messageString]

                if commandType == "003": #ie stop production
                    pass

                if commandType == "000": # ie acknowledge last
                # remove last message for this sender from the toAcknowledgeMessages list
                    toRemove = []
                    for message in toAcknowledgeMessages:
                        prevMessTargetNodeType = message[1][0]
                        prevMessTargetNodeID = message[1][1]
                        prevMessSourceNodeType = message[1][2]
                        prevMessSourceNodeID = message[1][3]
                        if((sourceNodeType+sourceNodeID)==(prevMessTargetNodeType+prevMessTargetNodeID)):
                            # check the ack message source is the same as the archived message target
                            toRemove.append(message)
                    for message in toRemove:
                        toAcknowledgeMessages.remove(message)
        else:
            #reject
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
            #check previous log of messages for similarity
            seenBefore=False
            #lastMessage = None
            try:
                lastMessage = lastMessageReference[sourceNodeType+sourceNodeID]
                if lastMessage == inputString:
                    seenBefore = True # we've seen the message before, warn the proceeding code
                else:
                    lastMessageReference[sourceNodeType+sourceNodeID] = inputString # we haven't seen this message before, record it
            except KeyError:
                lastMessageReference[sourceNodeType+sourceNodeID] = inputString
            # send ack
            messageData=[sourceNodeType,sourceNodeID,targetNodeType,targetNodeID,"000",""]
            messageString = sendMessage(messageData)
            controlNodeUIPub.publish(messageString)
            if seenBefore == False: # ie assuming we haven't aready acted on this message
                # need command check referencing message from transport node to control node to indicate finished process,
                # in which get next processing node for the vision node. send ack to the transport node and store message
                # to vision node for ack checking
                ##############################
                ##############################
                ##############################

                if commandType == "000": # ie acknowledge last
                # remove last message for this sender from the toAcknowledgeMessages list
                    toRemove = []
                    for message in toAcknowledgeMessages:
                        prevMessTargetNodeType = message[1][0]
                        prevMessTargetNodeID = message[1][1]
                        prevMessSourceNodeType = message[1][2]
                        prevMessSourceNodeID = message[1][3]
                        if((sourceNodeType+sourceNodeID)==(prevMessTargetNodeType+prevMessTargetNodeID)):
                            # check the ack message source is the same as the archived message target
                            toRemove.append(message)
                    for message in toRemove:
                        toAcknowledgeMessages.remove(message)


class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False

# s = sched.scheduler(time.time, time.sleep)
def resendUponNoAcknowledge():
    #pass # run through messages not yet acknowledged, if older than 3 seconds, send message again
    for message in toAcknowledgeMessages: # for each message
        if message[0]-int(round(time.time() * 1000))>3000: # if the time stamp is older than 3 seconds
            messTargetNodeType = message[1][0]
            messTargetNodeID = message[1][1]
            messSourceNodeType = message[1][2]
            messSourceNodeID = message[1][3] # get target node to determine which topic to publish to
            if messTargetNodeType == 4: # ie vision
                controlNodeVisionPub.publish(message[1])

            if messTargetNodeType == 1: # ie processing
                pass

            if messTargetNodeType == 2: # ie UI
                controlNodeUIPub.publish(message[1])

            if messTargetNodeType == 3: # ie platform/transport
                controlNodeTransportPub.publish(message[1])

rt = RepeatedTimer(1, resendUponNoAcknowledge)
#     s.enter(1, 1, resendUponNoAcknowledge,()) # run every second, with priority 1, calling this function again
#
# s.enter(1, 1, resendUponNoAcknowledge,())
# s.run()

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
                rospy.init_node("controlNode",anonymous=True)
                controlNodeVisionPub = rospy.Subscriber("/vision", String, receiveMessage)
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



rt.stop()
