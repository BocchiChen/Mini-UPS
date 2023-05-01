import socket
import psycopg2
from protobuf import world_ups_pb2
from protobuf import ups_amazon_pb2
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
import threading
import time

import message
import database
import world

#world settings
AMAZON_HOST = ''
AMAZON_PORT = 34567
UPS_HOST = socket.gethostname()
UPS_PORT = 34567
BACK_LOG = 100

#time
TIME_WAIT = 5

#global variables
amazon_socket = None
worldid = None
world_seqnum = 0
aackset = set()
received_seqnum = set()

#thread pool
executor = ThreadPoolExecutor(max_workers = 50)

#lock
mutex = threading.Lock()

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

#accept amazon connection
def acceptAConnection():
  global amazon_socket
  try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    address = (UPS_HOST, UPS_PORT)
    sock.bind(address)
    sock.listen(BACK_LOG)
    conn_socket, address = sock.accept()
    print("Received amazon connection from: ", address)
    amazon_socket = conn_socket
    sock.close()
    return conn_socket
  except Exception as e:
    print("Error occurs while connecting the amazon: ", e)
    
#send message to amazon
def sendMsgToAmazon(ua_messages):
  global amazon_socket
  message.sendMsgToAmazon(amazon_socket, ua_messages)
  
#send worldid to amazon, if UPS starts the deal
def sendWorldIDToAmazon():
  global amazon_socket
  global worldid
  try:
    result = ""
    worldid = world.getWorldID()
    if worldid is not None:
      au_connect = ups_amazon_pb2.AUConnect()
      au_connect.worldid = worldid
      sendMsgToAmazon(au_connect)
        
      #response
      ua_connected = ups_amazon_pb2.UAConnected()
      ua_connected.ParseFromString(message.recMsgFromAmazon(amazon_socket))
      result = ua_connected.result
      return result
  except Exception as e:
     print("Error occurs while trying to send worldid to amazon: ",e)
  
#receive worldid provided by the amazon 
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
  au_messages = ups_amazon_pb2.AUMessages()
  msg = message.recMsgFromAmazon(amazon_socket)
  au_messages.ParseFromString(msg)
  return au_messages
  
#respond world with acks
def respAmazonWithACK(seqnum):
  global amazon_socket
  ua_messages = ups_amazon_pb2.UAMessages()
  ua_messages.acks[:] = [seqnum]
  message.sendMsgToAmazon(amazon_socket, ua_messages)

#check whether the seqnum already been received
def checkSeqnum(seqnum):
  global received_seqnum
  print(seqnum, received_seqnum)
  if seqnum in received_seqnum:
    return True
  with mutex:
    received_seqnum.add(seqnum)
  return False

#send error message to amazon
def sendErrMsgToAmazon(err, originseqnum, seqnum):
  global amazon_socket
  global aackset
  while seqnum not in aackset: 
    ua_messages = ups_amazon_pb2.UAMessages()
    error = ua_messages.error.add()
    error.err = err
    error.originseqnum = originseqnum
    error.seqnum = seqnum
    message.sendMsgToAmazon(amazon_socket, ua_messages)
    time.sleep(TIME_WAIT)

#get the world seqnum to send
def getWorldSeqnum():
  global world_seqnum
  with mutex:
    world_seqnum += 1
    return world_seqnum - 1

#@thread (amazon sends message to ups for creating new package in the database)
def AOrderHandler(deal):
  try:
    #get basic information
    userid = deal.userid
    packageid = deal.order.id
    description = deal.order.description
    count = deal.order.count
    dst_x = deal.order.x
    dst_y = deal.order.y
    whid = deal.order.whid
    shipid = deal.shipid
    seqnum = deal.seqnum
    
    #response amazon with acks
    respAmazonWithACK(seqnum)
    if checkSeqnum(seqnum):
      return
    #database cursor
    dbconn = database.connectToDB()
    cur = dbconn.cursor()
    
    #insert order
    if userid == "":
      query = f"""INSERT INTO packages (PACKAGE_ID, STATUS, DESCRIPTION, COUNT, DESTINATION_X, DESTINATION_Y, WAREHOUSE_ID, SHIP_ID, USER_ID, TRUCK_ID) 
                  VALUES ({shipid}, 'created', '{description}', {count}, {dst_x}, {dst_y}, {whid}, {shipid}, NULL, NULL);"""
      cur.execute(query)
    else:
      #check if userid exists
      query = f"""SELECT UPS_ACCOUNT_NUMBER FROM upsaccount WHERE UPS_ACCOUNT_NUMBER = '{userid}';"""
      cur.execute(query)
      user = cur.fetchone()
      if user is None:
        err = "error: cannot find the user id: " + str(userid)
        print(err)
        sendErrMsgToAmazon(err, seqnum, getWorldSeqnum())
        return
      query = f"""INSERT INTO packages (PACKAGE_ID, STATUS, DESCRIPTION, COUNT, DESTINATION_X, DESTINATION_Y, WAREHOUSE_ID, SHIP_ID, USER_ID, TRUCK_ID) 
                  VALUES ({shipid}, 'created', '{description}', {count}, {dst_x}, {dst_y}, {whid}, {shipid}, {userid}, NULL);"""
      cur.execute(query)
    dbconn.commit()
    print("New Amazon package created in UPS database: ", deal)
    cur.close()
  except Exception as e:
    try:
      dbconn.rollback()
    except Exception as rberr:
      print("Error occurs while rolling back the database: ", rberr)
    print("Error occurs while communicating with the amazon: ", e)
  finally:
    db.close()

#@thread (amazon wants to associate the order within its UPS userid after placing its order)
def AAssociateIDHandler(assuserid):
  try:
    #get basic information
    userid = assuserid.userid
    shipid = assuserid.shipid
    seqnum = assuserid.seqnum
    
    #response amazon with acks
    respAmazonWithACK(seqnum)
    if checkSeqnum(seqnum):
      return
    
    #database cursor
    dbconn = database.connectToDB()
    cur = dbconn.cursor()
    
    #check if userid exists
    query = f"""SELECT UPS_ACCOUNT_NUMBER FROM upsaccount WHERE UPS_ACCOUNT_NUMBER = '{userid}';"""
    cur.execute(query)
    user = cur.fetchone()
    if user is None:
      err = "error: cannot find the user id: " + str(userid)
      print(err)
      sendErrMsgToAmazon(err, seqnum, getWorldSeqnum())
      return 
    
    #find package and modify its user_id (***)
    query = f"""SELECT SHIP_ID FROM packages WHERE SHIP_ID = {shipid};"""
    cur.execute(query)
    shd = cur.fetchone()
    while shd is None:
      query = f"""SELECT SHIP_ID FROM packages WHERE SHIP_ID = {shipid};"""
      cur.execute(query)
      shd = cur.fetchone()
    #associate user id
    query = f"""UPDATE packages SET USER_ID = '{userid}' WHERE SHIP_ID = {shipid};"""
    cur.execute(query)
    
    dbconn.commit()
    cur.close()
  except Exception as e:
    try:
      dbconn.rollback()
    except Exception as rberr:
      print("Error occurs while rolling back the database: ", rberr)
    print("Error occurs while communicating with the amazon: ", e)
  finally:
    dbconn.close()
    
#@thread (amazon call ups to schedule truck)
def AScheduleTruckHandler(calltruck):
  global aackset
  try:
    #get basic information
    whid = calltruck.whnum
    shipids = calltruck.shipid #many
    seqnum = calltruck.seqnum
    
    #response amazon with acks
    respAmazonWithACK(seqnum)
    if checkSeqnum(seqnum):
      return
    
    #database cursor
    dbconn = database.connectToDB()
    cur = dbconn.cursor()
    
    print("SELECT TRUCKS!!!!!!!!!!!!")

    truckid = 0
    with mutex:
      #find available truck (block) (***)
      while True:
        query = "SELECT TRUCK_ID FROM trucks WHERE STATUS = 'idle';"
        cur.execute(query)
        truck = cur.fetchone()
        if truck is not None:
          truckid = truck[0]
          break
        else:
          query2 = "SELECT TRUCK_ID FROM trucks WHERE STATUS = 'delivering';"
          cur.execute(query2)
          truck2 = cur.fetchone()
          if truck2 is not None:
            truckid = truck2[0]
            break

      print("SELECTED TRUCKS: ", truckid)
      query = f"""UPDATE trucks SET STATUS = 'traveling', WAREHOUSE_ID = {whid} WHERE TRUCK_ID = {truckid};"""
      cur.execute(query)

    #add packages belonging to the selected truck
    for shipid in shipids:
      query = f"""UPDATE packages SET TRUCK_ID = {truckid}, STATUS = 'truck_en_route_to_warehouse' WHERE SHIP_ID = {shipid};"""
      cur.execute(query)
   
    ucommands = world_ups_pb2.UCommands()
    pickup = ucommands.pickups.add()
    pickup.truckid = truckid
    pickup.whid = whid
    world_seqnum = getWorldSeqnum()
    pickup.seqnum = world_seqnum
    #testing ***
    #ucommands.simspeed = 50
    
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
  finally:
    dbconn.close()

#@thread (amazon send message to update truck status)
def AUpdateTStatusHandler(updatestatus):
  try:
    #get basic information
    truckid = updatestatus.truckid
    status = updatestatus.status
    seqnum = updatestatus.seqnum

    #response amazon with acks
    respAmazonWithACK(seqnum)
    if checkSeqnum(seqnum):
      return
    
    #database cursor
    dbconn = database.connectToDB()
    cur = dbconn.cursor()

    #check if the truckid exists
    query = f"""SELECT TRUCK_ID FROM trucks WHERE TRUCK_ID = {truckid};"""
    cur.execute(query)
    truck = cur.fetchone()
    #print('truckid:', truck[0])
    if truck is None:
      err = "error: cannot find the truck id: " + str(truckid)
      print(err)
      sendErrMsgToAmazon(err, seqnum, getWorldSeqnum())
      return 
    
    #update truck status
    query = f"""UPDATE trucks SET STATUS = '{status.lower()}' WHERE TRUCK_ID = {truckid};"""
    cur.execute(query)
    
    #update package status
    ships = None
    if status == "LOADING":
      query = f"""SELECT SHIP_ID FROM packages WHERE TRUCK_ID = {truckid} AND STATUS = 'truck_waiting_for_package';"""
      print(query)
      cur.execute(query)
    else:
      query = f"""SELECT SHIP_ID FROM packages WHERE TRUCK_ID = {truckid} AND STATUS = 'truck_loading';"""
      print(query)
      cur.execute(query)
    ships = cur.fetchall()
    for ship in ships:
      shipid = ship[0]
      if status == "LOADING":
        query = f"""UPDATE packages SET STATUS = 'truck_loading' WHERE SHIP_ID = {shipid};"""
        print(query)
        cur.execute(query)
      else:
        query = f"""UPDATE packages SET STATUS = 'truck_loaded' WHERE SHIP_ID = {shipid};"""
        print(query)
        cur.execute(query)
        
    dbconn.commit()
    cur.close()
  except Exception as e:
    try:
      dbconn.rollback()
    except Exception as rberr:
      print("Error occurs while rolling back the database: ", rberr)
    print("Error occurs while communicating with the amazon: ", e)
  finally:
    dbconn.close()

#@thread (amazon tell ups to deliver packages, possibly adding more packages to deliver) 
def ATruckGoDeliverHandler(godeliver):
  global aackset
  try:
    #get basic information
    truckid = godeliver.truckid
    shipids = godeliver.shipid
    seqnum = godeliver.seqnum
    #print('in AtrcukGoDelivery:', truckid)
    #response amazon with acks
    respAmazonWithACK(seqnum)
    #print("Go Delivered Seqnum: ",seqnum)
    if checkSeqnum(seqnum):
      return
    
    #database cursor
    dbconn = database.connectToDB()
    cur = dbconn.cursor()
    
    #error message (check valid condition)
    #check truck status
    query = f"""SELECT STATUS, WAREHOUSE_ID FROM trucks WHERE TRUCK_ID = {truckid};"""
    cur.execute(query)
    status = cur.fetchone()
    st = status[0]
    whnum = status[1]
    while st != 'idle' and st != 'loaded' and st != 'delivering':
      query = f"""SELECT STATUS FROM trucks WHERE TRUCK_ID = {truckid};"""
      cur.execute(query)
      status = cur.fetchone()
      st = status[0]
    
    #check package status
    for shipid in shipids:
      query = f"""SELECT STATUS, WAREHOUSE_ID FROM packages WHERE SHIP_ID = {shipid};"""
      cur.execute(query)
      pack = cur.fetchone()
      pack_whnum = pack[1]
      while pack[0] != "truck_loaded" and (not (pack[0] == "created" and st == 'loaded' and pack_num == whnum)):
        query = f"""SELECT STATUS FROM packages WHERE SHIP_ID = {shipid};"""
        cur.execute(query)
        pack = cur.fetchone()

    #update status
    haveSomethingToSend = False
    for shipid in shipids:
      #update package status
      query = f"""SELECT STATUS FROM packages WHERE SHIP_ID = {shipid};"""
      cur.execute(query)
      sts = cur.fetchone()[0]
      if sts != 'delivered':
        query2 = f"""UPDATE packages SET STATUS = 'out_for_delivery', TRUCK_ID = {truckid} WHERE SHIP_ID = {shipid};"""
        print(query2)
        cur.execute(query2)
        haveSomethingToSend = True
    
    #update truck status
    if haveSomethingToSend:
      query2 = f"""UPDATE trucks SET STATUS = 'delivering' WHERE TRUCK_ID = {truckid};"""
      print(query2)
      cur.execute(query2)
    
    #notice world to deliver packages
    ucommands = world_ups_pb2.UCommands()
    delivery = ucommands.deliveries.add()
    delivery.truckid = truckid
    for shipid in shipids: 
      package = delivery.packages.add()
      package.packageid = shipid
      query = f"""SELECT DESTINATION_X, DESTINATION_Y FROM packages WHERE SHIP_ID = {shipid};"""
      cur.execute(query)
      p = cur.fetchone()
      package.x = p[0]
      package.y = p[1]
    world_seqnum = getWorldSeqnum()
    delivery.seqnum = world_seqnum
    
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
  finally:
    dbconn.close()
    
#route amazon responses with threads
def amazonRespRouter():
  global amazon_socket
  global aackset
  global executor
  try:
    au_messages = ups_amazon_pb2.AUMessages()
    au_messages = recvAResponse()
    for deal in au_messages.order:
      args = [deal]
      task = executor.submit(lambda p: AOrderHandler(*p),args)
    for assuserid in au_messages.associateUserId:
      args = [assuserid]
      task = executor.submit(lambda p: AAssociateIDHandler(*p),args)
    for calltruck in au_messages.callTruck:
      args = [calltruck]
      task = executor.submit(lambda p: AScheduleTruckHandler(*p),args)
    for updatestatus in au_messages.updateTruckStatus:
      args = [updatestatus]
      task = executor.submit(lambda p: AUpdateTStatusHandler(*p),args)
    for godeliver in au_messages.truckGoDeliver:
      args = [godeliver]
      task = executor.submit(lambda p: ATruckGoDeliverHandler(*p),args)
    for ack in au_messages.acks:
      aackset.add(ack)
  except Exception as e:
    print(e)

def getAAckSet():
  global aackset
  return aackset

def getWorldID():
  global worldid
  return worldid
  