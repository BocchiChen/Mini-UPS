import socket
import psycopg2
from protobuf import world_ups_pb2
from protobuf import ups_amazon_pb2
from concurrent.futures import ThreadPoolExecutor
import threading
import time

import message
import database
import amazon

#world settings
WORLD_HOST = 'vcm-30507.vm.duke.edu'
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

#thread pool
executor = ThreadPoolExecutor(max_workers = 50)

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
   
#connect to world or create new world
def sayHelloToWorld(truck_num):
  global world_socket
  global world_id
  global dbconn
  try:
    uconnect = world_ups_pb2.UConnect()
    uconnect.isAmazon = False
    
    if amazon.getWorldID():
      world_id = amazon.getWorldID()
      uconnect.worldid = world_id
    dbconn = database.connectToDB()
    database.clearDB(dbconn)
    cur = dbconn.cursor()
    #init and add trucks
    for i in range(0, truck_num):
      truck = uconnect.trucks.add()
      truck.id = i
      truck.x = 0
      truck.y = 0
      query = f"""INSERT INTO trucks (TRUCK_ID, STATUS, WAREHOUSE_ID, POSITION_X, POSITION_Y) VALUES ({i}, 'idle', -1, 0, 0);"""
      cur.execute(query)
    
    database.commitAndClose(dbconn, cur)
    
    #send init message to world and receive message
    message.sendMsgToWorld(world_socket, uconnect)
    uconnected = world_ups_pb2.UConnected()
    msg = message.recMsgFromWorld(world_socket)
    uconnected.ParseFromString(msg)
    
    print(uconnected)
    
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

#check whether received seqnum already been used
def checkSeqnum(seqnum):
  global received_seqnum
  if seqnum in received_seqnum:
    return True
  with mutex:
    received_seqnum.add(seqnum)
  return False

#get amazon seqnum to send
def getASeqnum():
  global amazon_seqnum
  with mutex:
    amazon_seqnum += 1
    return amazon_seqnum - 1
  
#@thread
def UCompletionHandler(completion):
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
    dbconn = database.connectToDB()
    cur = dbconn.cursor()

    print(status)
    
    if status == "IDLE":
      while True:
        query = f"""SELECT STATUS FROM trucks WHERE TRUCK_ID = {truckid};"""
        cur.execute(query)
        sts = cur.fetchone()
        if sts[0] == "delivering":
          query = f"""UPDATE trucks SET STATUS = 'idle', POSITION_X = {x}, POSITION_Y = {y} WHERE TRUCK_ID = {truckid};"""
          cur.execute(query)
          break
      
    else:
      query = f"""UPDATE trucks SET STATUS = 'arrive_warehouse', POSITION_X = {x}, POSITION_Y = {y} WHERE TRUCK_ID = {truckid};"""
      cur.execute(query)      
      
      query = f"""SELECT WAREHOUSE_ID FROM trucks WHERE TRUCK_ID = {truckid};"""
      cur.execute(query)
      wh = cur.fetchone()
      whid = wh[0]

      #update package status (added)
      query = f"""SELECT PACKAGE_ID FROM packages WHERE WAREHOUSE_ID = {whid} AND TRUCK_ID = {truckid} AND STATUS = 'truck_en_route_to_warehouse';"""
      cur.execute(query)
      packages = cur.fetchall()
      for p in packages:
        query2 = f"""UPDATE packages SET STATUS = 'truck_waiting_for_package' WHERE PACKAGE_ID = {p[0]};"""
        print(query2)
        cur.execute(query2)
      
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
  finally:
    dbconn.close()

#@thread
def UDeliveredHandler(delivered):
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
    dbconn = database.connectToDB()
    cur = dbconn.cursor()
    
    #update package status
    while True:
      query = f"""SELECT STATUS FROM packages WHERE SHIP_ID = {packageid};"""
      cur.execute(query)
      status = cur.fetchone()
      if status[0] == 'out_for_delivery':
        query = f"""UPDATE packages SET STATUS = 'delivered' WHERE SHIP_ID = {packageid};"""
        print(query)
        cur.execute(query)
        break
    
    #equip message (##UAMessages)
    ua_messages = ups_amazon_pb2.UAMessages()
    finishedpackage = ua_messages.updatePackageStatus.add()
    finishedpackage.shipid = packageid
    finishedpackage.status = "DELIVERED"
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
  finally:
    dbconn.close()

#@thread
def UTruckStatusHandler(truckstatus):
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
    dbconn = database.connectToDB()
    cur = dbconn.cursor()
    
    #update truck status
    query = f"""UPDATE trucks SET STATUS = '{status.lower()}', POSITION_X = {x}, POSITION_Y = {y} WHERE TRUCK_ID = {truckid};"""
    cur.execute(query)
    
    dbconn.commit()
    cur.close()
  except Exception as e:
    try:
      dbconn.rollback()
    except Exception as rberr:
      print("Error occurs while rolling back the database: ", rberr)
    print("Error occurs while communicating with the world: ", e)
  finally:
    dbconn.close()
    
#@thread
def UErrHandler(error):
  try:
    #get basic information
    seqnum = error.seqnum
    
    #response world with acks
    respWorldWithACK(seqnum)
    if checkSeqnum(seqnum):
      return
    print(error)
  except Exception as e:
    print(e)
    
#route world responses with threads (select)
def worldRespRouter():
  global world_socket
  global ackset
  global executor
  try: 
    uresponses = world_ups_pb2.UResponses()
    uresponses = recvWResponse()
    for completion in uresponses.completions:
      args = [completion]
      task = executor.submit(lambda p: UCompletionHandler(*p),args)
    for delivered in uresponses.delivered:
      args = [delivered]
      task = executor.submit(lambda p: UDeliveredHandler(*p),args)
    for ack in uresponses.acks:
      ackset.add(ack)
    for truckstatus in uresponses.truckstatus:
      args = [truckstatus]
      task = executor.submit(lambda p: UTruckStatusHandler(*p),args)
    for error in uresponses.error:
      args = [error]
      task = executor.submit(lambda p: UErrHandler(*p),args)
  except Exception as e:
    print(e)
    
def getAckSet():
  global ackset
  return ackset

def getWorldID():
  global worldid
  return worldid