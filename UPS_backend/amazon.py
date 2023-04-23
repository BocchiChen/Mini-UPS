import socket
import psycopg2
from protobuf import world_ups_pb2
from protobuf import ups_amazon_pb2
import threading
import time

import message
import database
import world

#world settings
AMAZON_HOST = ''
AMAZON_PORT = 12345

#time
TIME_WAIT = 5

#global variables
amazon_socket = None
worldid = None
world_seqnum = 0
aackset = set()

#connect to the amazon
def connectToAmazon():
  global amazon_socket
  try:
    amazon_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    amazon_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    address = (AMAZON_HOST, AMAZON_PORT)
    amazon_socket.connect(address)
    return amazon_socket
  except Exception as e:
    print("Error occurs while connecting the amazon: ", e)

#send message to amazon
def sendMsgToAmazon(ua_messages):
  global amazon_socket
  message.sendMsgToAmazon(amazon_socket, ua_messages)
  
#send worldid to amazon
def sendWorldIDToAmazon():
  global amazon_socket
  global worldid
  try:
    result = ""
    worldid = world.getWorldID()
    if worldid is not None:
      au_connect = ups_amazon_pb2.AUConnect()
      au_connect.worldid = worldid
      amazon.sendMsgToAmazon(au_connect)
        
      #response
      ua_connected = ups_amazon_pb2.UAConnected()
      ua_connected.ParseFromString(message.recMsgFromAmazon(amazon_socket))
      result = ua_connected.result
      return result
   except Exception as e:
     print("Error occurs while trying to send worldid to amazon: ",e)
  
#receive and connect to the worldid provided by the amazon 
def synchronizeWithAmazon():
  global amazon_socket
  global worldid
  try:
    if worldid is None:
      #receive
      au_connect = ups_amazon_pb2.AUConnect()
      au_connect.ParseFromString(message.recMsgFromAmazon(amazon_socket))
      worldid = au_connect.worldid
    
      #response
      ua_connected = ups_amazon_pb2.UAConnected()
      ua_connected.worldid = worldid
      ua_connected.result = "connected!"
      sendMsgToAmazon(ua_connected)
   except:
     try:
       ua_connected = ups_amazon_pb2.UAConnected()
       ua_connected.worldid = worldid
       ua_connected.result = "error: cannot connect to the specified worldid: " + worldid 
       sendMsgToAmazon(ua_connected)
     except Exception as e:
       print(e)
  
#receive amazon messages
def recvAResponse():
  global amazon_socket
  au_messages = world_ups_pb2.AUMessages()
  msg = message.recMsgFromAmazon(amazon_socket)
  au_messages.ParseFromString(msg)
  return au_messages
  
#respond world with acks
def respAmazonWithACK(seqnum):
  global amazon_socket
  ua_messages = world_ups_pb2.UAMessages()
  ua_messages.acks[:] = [seqnum]
  message.sendMsgToAmazon(amazon_socket, ua_messages)
  
#route amazon responses with threads
def amazonRespRouter():
  global amazon_socket
  global world_seqnum
  global aackset
  try:
    au_messages = ups_amazon_pb2.AUMessages()
    au_messages = recvAResponse()
    dbconn = database.connectToDB()
    for warehouse in au_messages.warehouses:
      thread = threading.Thread(target = APickUpHandler, args = (dbconn, warehouse, world_seqnum))
      thread.start()
      world_seqnum += 1
    for destination in au_messages.destinations:
      thread = threading.Thread(target = ADeliverRequestHandler, args = (dbconn, destination, world_seqnum))
      thread.start()
      world_seqnum += 1
    for aquery in au_messages.queries:
      thread = threading.Thread(target = AQueryHandler, args = (dbconn, aquery, world_seqnum))
      thread.start()
      world_seqnum += 1
    for ack in au_messages.acks:
      aackset.add(ack)
    dbconn.close()
  except Exception as e:
    print(e)
  finally:
    if dbconn
      dbconn.close()

#@thread (send a truck to a warehouse for picking up packages)
def APickUpHandler(dbconn, warehouse, world_seqnum):
  try:
    seqnum = warehouse.seqnum
    #response amazon with acks
    respAmazonWithACK(seqnum)
    
    #database cursor
    cur = dbconn.cursor()
    
    truckid = 0
    #find available truck (block)
    while True:
      query = "SELECT TRUCK_ID FROM TRUCKS WHERE TRUCK_STATUS = 'idle' OR TRUCK_STATUS = 'arrive_warehouse' OR TRUCK_STATUS = 'delivering';"
      cur.execute(query)
      truck = cur.fetchone()
      if truck is not None:
        truckid = truck[0]
        break
        
    #add packages belonging to the selected truck
    for package in warehouse.packs:
      #may need more
      query = "INSERT INTO PACKAGES (PACKAGE_ID, TRUCK_ID, PACKAGE_STATUS) VALUES (" + package.packageid + ", " + truckid + ", 'prepare_for_delivery');"
      cur.execute(query)
          
    query = "UPDATE TRUCKS SET TRUCK_STATUS = 'traveling' WHERE TRUCK_ID = " + truckid + ";"
    cur.execute(query)
   
    ucommands = world_ups_pb2.UCommands()
    pickup = ucommands.pickups.add()
    pickup.truckid = truckid
    pickup.whid = warehouse.whid
    pickup.seqnum = world_seqnum
    
    #send message to world and wait ack
    ackset = world.getAckSet()
    while world_seqnum not in ackset:
      world.sendMsgToWorld(ucommands)
      time.sleep(TIME_WAIT)
      ackset = world.getAckSet()
    
    dbconn.commit()
    cur.close()
  except Exception as e:
    try:
      dbconn.rollback()
    except Exception as rberr:
      print("Error occurs while rolling back the database: ", rberr)
    print("Error occurs while communicating with the amazon: ", e)

#@thread   
def ADeliverRequestHandler(dbconn, destination, world_seqnum):
  try:
    seqnum = destination.seqnum
    #response amazon with acks
    respAmazonWithACK(seqnum)
    
    #database cursor
    cur = dbconn.cursor()
    
    #find the truck id for the package
    query = "SELECT TRUCK_ID, PACKAGE_STATUS FROM PACKAGES WHERE PACKAGE_ID = " + destination.packageid + ";"
    cur.execute(query)
    truck = cur.fetchone()
    if truck is None or truck[1] != "loaded":
      #handle error message
      err = "error: not able to deliver the package: " + destination.packageid
      sendErrMsgToAmazon(err, destination.seqnum, world.getASeqnum)
      return
    
    truckid = truck[0]
    
    #config message sent to world
    ucommands = world_ups_pb2.UCommands()
    delivery = ucommands.deliveries.add()
    delivery.truckid = truckid
    package = delivery.packages.add()
    package.packageid = destination.packageid
    package.x = destination.x
    package.y = destination.y
    delivery.seqnum = world_seqnum
    
    #send message to world and wait ack
    ackset = world.getAckSet()
    while world_seqnum not in ackset:
      world.sendMsgToWorld(ucommands)
      time.sleep(TIME_WAIT)
      ackset = world.getAckSet()
    
    query = "UPDATE PACKAGES SET PACKAGE_STATUS = 'delivering' WHERE PACKAGE_ID = " + destination.packageid + ";"
    cur.execute(query)
    
    query = "UPDATE TRUCKS SET TRUCK_STATUS = 'delivering' WHERE TRUCK_ID = " + truckid + ";"
    cur.execute(query)
    
    dbconn.commit()
    cur.close()
  except Exception as e:
    try:
      dbconn.rollback()
    except Exception as rberr:
      print("Error occurs while rolling back the database: ", rberr)
    print("Error occurs while communicating with the amazon: ", e)
  
#@thread (receive amazon query request to get package location)
def AQueryHandler(dbconn, aquery, world_seqnum):
  try:
    packageid = aquery.packageid
    seqnum = aquery.seqnum
    #response amazon with acks
    respAmazonWithACK(seqnum)
  
    #query database to get truckid based on the packageid
    cur = dbconn.cursor()
    query = "SELECT TRUCK_ID FROM PACKAGES WHERE PACKAGE_ID = " + packageid + ";"
    cur.execute(query)
    truck = cur.fetchone()
    
    if truck is None:
      #handle error message
      err = "error: cannot find the status of package: " + packageid
      sendErrMsgToAmazon(err, aquery.seqnum, world.getASeqnum)
      return
  
    #ask truck status to world
    ucommands = world_ups_pb2.UCommands()
    query = ucommands.queries.add()
    query.truckid = truck[0]
    query.seqnum = world_seqnum
    
    #send message to world and wait ack
    ackset = world.getAckSet()
    while world_seqnum not in ackset:
      world.sendMsgToWorld(ucommands)
      time.sleep(TIME_WAIT)
      ackset = world.getAckSet()
  
    cur.close()
  except Exception as e:
    print(e)

def sendErrMsgToAmazon(err, originseqnum, seqnum):
  global amazon_socket
  ua_messages = ups_amazon_pb2.UAMessages()
  error = ua_messages.errors.add()
  error.err = err
  error.originseqnum = originseqnum
  error.seqnum = seqnum
  message.sendMsgToAmazon(amazon_socket, ua_messages)

def getAAckSet():
  global aackset
  return aackset

def getWorldID():
  global worldid
  return worldid
  
  
