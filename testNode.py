#!/usr/bin/python3
import hashlib
import rospy
from std_msgs.msg import String


nodeType = '-'
nodeID = '-'
nodeName = 'testNode'
targetTopic = '-'
connectedToTopic = False
pub = None
sub = None


def receiveMessage(data):
    ## get message
    inputString = data.data
    if type(inputString) == type("testString"):
        # echo message
        print(inputString)
        # check structure
        if(length(inputString) > 8):
            commandDataLength = int(inputString[4])
            if(length(inputString) == (7+commandDataLength)):
                targetNodeType = inputString[0]
                targetNodeID = inputString[1]
                sourceNodeType = inputString[2]
                sourceNodeID = inputString[3]
                commandData = inputString[5:(5+commandDataLength)]
                m = hashlib.sha256()
                m.update(commandData)
                hashResult = m.hexdigest()

                # check byte count

                # check sha256
                # highlight problems
            else:
                print("received data too short")
        else:
            print("received data too short")
    else:
        print("recived data incorrect type, ie not string")







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
        dealtWith = 1
        pass

    if (inputString == "exit" and dealtWith == 0):
        print("Exiting")
        dealtWith = 1
        break;

    if (dealtWith == 0):
        print("Input not recognised")
        dealtWith = 1
