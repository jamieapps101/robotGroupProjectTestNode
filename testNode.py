#!/usr/bin/python3
import hashlib
import rospy
from std_msgs.msg import String


nodeType = '-'
nodeID = '-'
nodeName = 'testNode'
targetTopic = '/transport'
connectedToTopic = False
pub = None
sub = None

testMessage = "3141022062(1,1.9544444444444444,0.8470588235294118,0.036680787756651845)ab8789e45d34efd7512e9f71d754793a7169f1e652f1f3f2827665db93eecc9b"

def receiveMessage(data):
    ## get message
    inputString = data.data
    if type(inputString) == type("testString"):
        # echo message
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
            commandDataLength = int(inputString[7:10])
            print("commandDataLength {}".format(commandDataLength))
            commandData = inputString[5:(5+commandDataLength)]
            if(len(inputString) == (136+commandDataLength)):
                print("commandData {}".format(commandData))
                print("checksum {}".format(checksum))

                checksum = inputString[(5+commandDataLength):]
                m = hashlib.sha256()
                m.update(commandData)
                hashResult = str(m.hexdigest())
                if(hashResult == checksum):
                    print("aaaah fuck theres a problem, print everything")
                    print(targetNodeType)
                    print(targetNodeID)
                    print(sourceNodeType)
                    print(sourceNodeID)
                    print(commandData)
                    print(checksum)
                # check byte count

                # check sha256
                # highlight problems
            else:
                print("received data too short")
                print("actualLength {}".format(len(inputString)))
        else:
            print("received data too short")
    else:
        print("recived data incorrect type, ie not string")
    sub.unregister()
    #sub = None
    pub.unregister()
    #pub = None







while (True):
    inputString = input(">>")
    dealtWith = 0

    if (inputString == "sendMessage" and dealtWith == 0):
        dealtWith = 1
        print("header def")
        headerDefInputString = input(">>")
        #check this is number
        print("data String")
        dataStringInputString = input(">>")
        #check this is number
        stringToSend = "complete me!"
        pub.publish(stringToSend)

    if (inputString == "setownID" and dealtWith == 0):
        print("set node type: (use "-" as null entry)")
        nodeTypeInputString = input(">>")
        #check input is valid letter, assign to variable as letter/string
        print("set node ID: (use "-" as null entry)")
        nodeIDInputString = input(">>")
        #check input is valid number, assign to variable as letter/string
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
            sub = None
            pub.unregister()
            pub = None
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
            inputString = input(">>>>")
            if(inputString != ''):
                targetTopic = inputString
            else:
                pass
        else:
            print("currently connected to a topic, please disconnect first")
        dealtWith = 1
        pass

    if (inputString == "help" and dealtWith == 0):
        commandsList = ['help', 'setTopic', 'disconnectTopic', 'connectTopic', 'sendMessage']
        for command in commandsList:
            print(command)
        dealtWith = 1
        pass

    if (inputString == "exit" and dealtWith == 0):
        print("Exiting")
        dealtWith = 1
        break;

    if (inputString == "" and dealtWith == 0):
        dealtWith = 1

    if (dealtWith == 0):
        print("Input not recognised")
        dealtWith = 1
