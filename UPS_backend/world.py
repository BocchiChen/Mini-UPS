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
      query = "INSERT INTO TRUCKS (TRUCK_ID, TRUCK_STATUS) VALUES (" + i + ", 'idle');"
      cur.execute(query)
    database.commitAndClose(dbconn, cur)
    
    #send init message to world and receive message
    message.sendMsgToWorld(world_socket, uconnect)
    uconnected = world_ups_pb2.UConnected()
    msg = message.recMsgFromWorld(world_socket)
    uconnected.ParseFromString(msg)
    
    if uconnected.result != "connected!":
      raise Exception(uconnected.result)
    
    return uconnected
  except Exception as e:
    try:
      if dbconn:
        dbconn.rollback()
    except Exception as rberr:
      print("Error occurs while rolling back the database: ", rberr)
    print("Error occurs while communicating with the world: ", e)
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
  global amazon_seqnum
  global ackset
  try: 
    uresponses = world_ups_pb2.UResponses()
    uresponses = recvWResponse()
    dbconn = database.connectToDB()
    for completion in uresponses.completions:
      thread = threading.Thread(target = UCompletionHandler, args = (dbconn, completion, amazon_seqnum))
      thread.start()
      amazon_seqnum += 1
    for delivered in uresponses.delivered:
      thread = threading.Thread(target = UDeliveredHandler, args = (dbconn, delivered, amazon_seqnum))
      thread.start()
      amazon_seqnum += 1
    for ack in uresponses.acks:
      ackset.add(ack)
    for truckstatus in uresponses.truckstatus:
      thread = threading.Thread(target = UTruckStatusHandler, args = (dbconn, truckstatus, amazon_seqnum))
      thread.start()
      amazon_seqnum += 1
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
def UCompletionHandler(dbconn, completion, amazon_seqnum):
  try:
    status = completion.status
    seqnum = completion.seqnum
  
    #response world with acks
    respWorldWithACK(seqnum)
    cur = dbconn.cursor()
    
    if status == "idle":
      query = "UPDATE TRUCKS SET TRUCK_STATUS = 'idle' WHERE TRUCK_ID = " + truckid + ";"
      cur.execute(query)
    elif status == "arrive warehouse":
      query = "UPDATE TRUCKS SET TRUCK_STATUS = 'arrive_warehouse' WHERE TRUCK_ID = " + truckid + ";"
      cur.execute(query)
      #init UAResponse (##UAMessages)
      ua_messages = ups_amazon_pb2.UAMessages()
      t = ua_messages.trucks.add()
      t.truck.truckid = completion.truckid
      t.truck.x = completion.x
      t.truck.y = completion.y
      t.truck.status = "loading"
      t.seqnum = amazon_seqnum
      #load packages
      query = "SELECT PACKAGE_ID FROM PACKAGES WHERE TRUCK_ID = " + truckid + " AND PACKAGE_STATUS = 'prepare_for_delivery';"
      cur.execute(query)
      packages = cur.fetchall()
      for package in packages:
        p = truck.pack.add()
        p.packageid = package[0]
        p.status = "loaded"
        #update package status (##Database)
        query = "UPDATE PACKAGES SET PACKAGE_STATUS = 'loaded' WHERE PACKAGE_ID = " + package[0] + ";"
        cur.execute(query)
        
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
def UDeliveredHandler(dbconn, delivered, amazon_seqnum):
  try:
    #get basic information
    truckid = delivered.truckid
    packageid = delivered.packageid
    seqnum = delivered.seqnum
    
    #response world with acks
    respWorldWithACK(seqnum)
    cur = dbconn.cursor()
    
    #update package status
    query = "UPDATE PACKAGES SET PACKAGE_STATUS = 'delivered' WHERE PACKAGE_ID = " + packageid + ";"
    cur.execute(query)
    
    #equip message (##UAMessages)
    ua_messages = ups_amazon_pb2.UAMessages()
    finishedpackage = ua_messages.finishes.add()
    finishedpackage.truckid = truckid
    finishedpackage.packageid = packageid
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
def UTruckStatusHandler(dbconn, truckstatus, amazon_seqnum):
  try:
    seqnum = truckstatus.seqnum
    #response world with acks
    respWorldWithACK(seqnum)
    
    print("The queried truck status is: ", truckstatus)
    
    #get packageid based on truckid
    cur = dbconn.cursor()
    query = "SELECT PACKAGE_ID FROM PACKAGES WHERE TRUCK_ID = " + truckstatus.truckid + ";";
    cur.execute(query)
    package = cur.fetchone()
    
    #send queried package location (truck) to amazon (##UAMessages)
    ua_messages = ups_amazon_pb2.UAMessages()
    deliveringpackage = ua_messages.deliveries.add()
    deliveringpackage.packageid = package[0]
    deliveringpackage.truck.truckid = truckstatus.truckid
    deliveringpackage.truck.x = truckstatus.x
    deliveringpackage.truck.y = truckstatus.y
    deliveringpackage.truck.status = truckstatus.status
    deliveringpackage.seqnum = amazon_seqnum
    
    #send message to amazon
    aackset = amazon.getAAckSet()
    while amazon_seqnum not in aackset:
      amazon.sendMsgToAmazon(ua_messages) 
      time.sleep(TIME_WAIT)
      aackset = amazon.getAAckSet()
    
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
    
def getAckSet():
  global ackset
  return ackset
  
def getASeqnum():
  global amazon_seqnum
  amazon_seqnum += 1
  return amazon_seqnum - 1

def getWorldID():
  global worldid
  return worldid
  

