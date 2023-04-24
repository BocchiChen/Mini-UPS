import socket
import psycopg2
from protobuf import world_ups_pb2
from protobuf import ups_amazon_pb2
import threading
import time

import message
import database
import amazon

#world settings
WORLD_HOST = ''
WORLD_PORT = 12345

#time
TIME_WAIT = 5

#global variables
world_socket = None
world_id = None
dbconn = None
amazon_seqnum = 0
ackset = set()
received_seqnum = set()

#lock
mutex = threading.Lock()

#connect to the world
def connectToWorldServer():
  global world_socket
  try:
    world_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    world_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    address = (WORLD_HOST, WORLD_PORT)
    world_socket.connect(address)
    return world_socket
  except Exception as e:
    print("Error occurs while connecting the world: ", e)

#send message to world
def sendMsgToWorld(ucommands):
  global world_socket
  message.sendMsgToWorld(world_socket, ucommands)
 
#create new world (send message to world without worldid, if UPS starts the deal)
def createNewWorld():
  global world_socket
  global world_id
  try:
    uconnect = world_ups_pb2.UConnect()
    uconnect.isAmazon = False
    message.sendMsgToWorld(world_socket, uconnect)
    uconnected = world_ups_pb2.UConnected()
    uconnected.ParseFromString(message.recMsgFromWorld(world_socket))
    print("Received response from World says: ", uconnected)
    world_id = uconnected.worldid
  except Exception as e:
    print("Error occurs while creating new world: ", e)
   
#communicate with world
def sayHelloToWorld(truck_num):
  global world_socket
  global world_id
  global dbconn
  try:
    dbconn = database.connectToDB()
    database.clearDB(dbconn)
    cur = dbconn.cursor()
    
    uconnect = world_ups_pb2.UConnect()
    worldid = amazon.getWorldID()
    uconnect.worldid = worldid
    uconnect.isAmazon = False
    
    #init and add trucks
    for i in range(0, truck_num):
      truck = uconnect.trucks.add()
      truck.id = i
      truck.x = 0
      truck.y = 0
      query = "INSERT INTO TRUCKS (TRUCK_ID, STATUS, WAREHOUSE_ID, POSITION_X, POSITION_Y) VALUES (" + i + ", 'idle', -1, 0, 0);"
      cur.execute(query)
    database.commitAndClose(dbconn, cur)
    
    #send init message to world and receive message
    message.sendMsgToWorld(world_socket, uconnect)
    uconnected = world_ups_pb2.UConnected()
    msg = message.recMsgFromWorld(world_socket)
    uconnected.ParseFromString(msg)
    
    if uconnected.result != "connected!":
      raise Exception(uconnected.result)
    
    return True
  except Exception as e:
    try:
      if dbconn:
        dbconn.rollback()
    except Exception as rberr:
      print("Error occurs while rolling back the database: ", rberr)
    print("Error occurs while communicating with the world: ", e)
    return False
  finally:
    if dbconn:
      dbconn.close()

#receive world responses
def recvWResponse():
  global world_socket
  uresponses = world_ups_pb2.UResponses()
  msg = message.recMsgFromWorld(world_socket)
  uresponses.ParseFromString(msg)
  return uresponses

#respond world with acks
def respWorldWithACK(seqnum):
  global world_socket
  ucommands = world_ups_pb2.UCommands()
  ucommands.acks[:] = [seqnum]
  message.sendMsgToWorld(world_socket, ucommands)

#route world responses with threads (select)
def worldRespRouter():
  global world_socket
  global ackset
  try: 
    uresponses = world_ups_pb2.UResponses()
    uresponses = recvWResponse()
    dbconn = database.connectToDB()
    for completion in uresponses.completions:
      thread = threading.Thread(target = UCompletionHandler, args = (dbconn, completion))
      thread.start()
    for delivered in uresponses.delivered:
      thread = threading.Thread(target = UDeliveredHandler, args = (dbconn, delivered))
      thread.start()
    for ack in uresponses.acks:
      ackset.add(ack)
    for truckstatus in uresponses.truckstatus:
      thread = threading.Thread(target = UTruckStatusHandler, args = (dbconn, truckstatus, getASeqnum()))
      thread.start()
    for error in uresponses.error:
      thread = threading.Thread(target = UErrHandler, args = (dbconn, error))
      thread.start()
    dbconn.close()
  except Exception as e:
    print(e)
  finally:
    if dbconn:
      dbconn.close()
  
#@thread
def UCompletionHandler(dbconn, completion):
  try:
    #get basic information
    truckid = completion.truckid
    x = completion.x
    y = completion.y
    status = completion.status
    seqnum = completion.seqnum
  
    #response world with acks
    respWorldWithACK(seqnum)
    if checkSeqnum(seqnum):
      return
    
    #database cursor
    cur = dbconn.cursor()
    
    if status == "idle":
      query = "UPDATE TRUCKS SET STATUS = 'idle' AND POSITION_X = " + x + " AND POSITION_Y = " + y + " WHERE TRUCK_ID = " + truckid + ";"
      cur.execute(query)
      
    elif status == "arrive warehouse":
      query = "UPDATE TRUCKS SET STATUS = 'arrive_warehouse' AND POSITION_X = " + x + " AND POSITION_Y = " + y + " WHERE TRUCK_ID = " + truckid + ";"
      cur.execute(query)
      
      query = "SELECT WAREHOUSE_ID FROM TRUCKS WHERE TRUCK_ID = " + truckid + ";"
      cur.execute(query)
      whid = cur.fetchone()[0]
      
      ua_messages = ups_amazon_pb2.UAMessages()
      truck = ua_messages.truckArrived.add()
      truck.truckid = truckid
      truck.whid = whid
      amazon_seqnum = getASeqnum()
      truck.seqnum = amazon_seqnum
        
      #send message to amazon
      aackset = amazon.getAAckSet()
      while amazon_seqnum not in aackset:
        amazon.sendMsgToAmazon(ua_messages) 
        time.sleep(TIME_WAIT)
        aackset = amazon.getAAckSet()
      
    dbconn.commit()
    cur.close()
  except Exception as e:
    try:
      dbconn.rollback()
    except Exception as rberr:
      print("Error occurs while rolling back the database: ", rberr)
    print("Error occurs while communicating with the world: ", e)

#@thread
def UDeliveredHandler(dbconn, delivered):
  try:
    #get basic information
    truckid = delivered.truckid
    packageid = delivered.packageid
    seqnum = delivered.seqnum
    
    #response world with acks
    respWorldWithACK(seqnum)
    if checkSeqnum(seqnum):
      return
    
    #database cursor
    cur = dbconn.cursor()
    
    #update package status
    query = "UPDATE PACKAGES SET STATUS = 'delivered' WHERE PACKAGE_ID = " + packageid + ";"
    cur.execute(query)
    
    #equip message (##UAMessages)
    ua_messages = ups_amazon_pb2.UAMessages()
    finishedpackage = ua_messages.updatePackageStatus.add()
    finishedpackage.shipid = packageid
    finishedpackage.status = "delivered"
    amazon_seqnum = getASeqnum()
    finishedpackage.seqnum = amazon_seqnum
    
    #send message to amazon
    aackset = amazon.getAAckSet()
    while amazon_seqnum not in aackset:
      amazon.sendMsgToAmazon(ua_messages) 
      time.sleep(TIME_WAIT)
      aackset = amazon.getAAckSet()
    
    dbconn.commit()
    cur.close()
  except Exception as e:
    try:
      dbconn.rollback()
    except Exception as rberr:
      print("Error occurs while rolling back the database: ", rberr)
    print("Error occurs while communicating with the world: ", e)

#@thread
def UTruckStatusHandler(dbconn, truckstatus):
  try:
    #get basic information
    truckid = truckstatus.truckid
    status = truckstatus.status
    x = truckstatus.x
    y = truckstatus.y
    seqnum = truckstatus.seqnum
    
    #response world with acks
    respWorldWithACK(seqnum)
    if checkSeqnum(seqnum):
      return
    
    print("The queried truck status is: ", truckstatus)
    
    #database cursor
    cur = dbconn.cursor()
    
    #update truck status
    query = "UPDATE TRUCKS SET STATUS = '" + str(status) + "' AND POSITION_X = " + x + " AND POSITION_Y = " + y + " WHERE TRUCK_ID = " + truckid + ";"
    cur.execute(query)
    '''
    #get packageid based on truckid
    query = "SELECT PACKAGE_ID FROM PACKAGES WHERE TRUCK_ID = " + truckstatus.truckid + ";";
    cur.execute(query)
    package = cur.fetchone()
    
    #send queried package location (truck) to amazon (##UAMessages)
    ua_messages = ups_amazon_pb2.UAMessages()
    
    amazon_seqnum = getASeqnum()
    deliveringpackage.seqnum = amazon_seqnum
    
    #send message to amazon
    aackset = amazon.getAAckSet()
    while amazon_seqnum not in aackset:
      amazon.sendMsgToAmazon(ua_messages) 
      time.sleep(TIME_WAIT)
      aackset = amazon.getAAckSet()
    '''
    dbconn.commit()
    cur.close()
  except Exception as e:
    print(e)
    
#@thread
def UErrHandler(dbconn, error):
  try:
    seqnum = error.seqnum
    #response world with acks
    respWorldWithACK(seqnum)    
    print(error.err)
  except Exception as e:
    print(e)
    
def checkSeqnum(seqnum):
  global received_seqnum
  if seqnum in received_seqnum:
    return True
  received_seqnum.add(seqnum)
  return False
    
def getAckSet():
  global ackset
  return ackset
  
def getASeqnum():
  global amazon_seqnum
  with mutex:
    amazon_seqnum += 1
    return amazon_seqnum - 1

def getWorldID():
  global worldid
  return worldid
  

