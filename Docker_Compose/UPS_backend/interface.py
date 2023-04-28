import socket
import psycopg2
import time
import threading
from protobuf import world_ups_pb2
from protobuf import ups_amazon_pb2
from concurrent.futures import ThreadPoolExecutor

import world
import amazon
import database

#net
INTERFACE_HOST = 'localhost'
INTERFACE_PORT = 34568
BACK_LOG = 100

#time
TIME_WAIT = 5

#message
MAX_MSG_LEN = 65535

#thread pool
executor = ThreadPoolExecutor(max_workers = 50)

#accept front connection
def acceptFConnection():
  try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    address = (INTERFACE_HOST, INTERFACE_PORT)
    sock.bind(address)
    sock.listen(BACK_LOG)
    conn = database.connectToDB()
    while True:
      conn_socket, address = sock.accept()
      print("Received front connection from: ", address)
      msg = conn_socket.recv(MAX_MSG_LEN).decode()
      lt = msg.split(',')
      print(lt)
      if len(lt) == 3:
        args = [conn, int(lt[0]), int(lt[1]), int(lt[2])]
        task = executor.submit(lambda p: AUpdatePackageAddress(*p),args)
      else:
        args = [int(lt[0])]
        task = executor.submit(lambda p: UQueryTruckStatus(*p),args)
      conn_socket.close()
  except Exception as e:
    print("Error occurs while creating and binding to the listening address: ", e)
  finally:
    if conn: 
      conn.close()

#@interface (send package address to amazon)
def AUpdatePackageAddress(conn, shipid, dst_x, dst_y):
  try:
    cur = conn.cursor()
    #query the truck id
    query = "SELECT TRUCK_ID FROM packages WHERE SHIP_ID = " + str(shipid) + ";"
    cur.execute(query)
    truckid = cur.fetchone()[0]
    #notice world to change the destination of package
    ucommands = world_ups_pb2.UCommands()
    delivery = ucommands.deliveries.add()
    delivery.truckid = truckid
    package = delivery.packages.add()
    package.packageid = shipid
    package.x = dst_x
    package.y = dst_y
    world_seqnum = amazon.getWorldSeqnum()
    delivery.seqnum = world_seqnum
    
    #send message to world and wait ack
    ackset = world.getAckSet()
    while world_seqnum not in ackset:
      world.sendMsgToWorld(ucommands)
      time.sleep(TIME_WAIT)
      ackset = world.getAckSet()

    #notice amazon that the destinatin has been changed
    ua_messages = ups_amazon_pb2.UAMessages()
    pa = ua_messages.updatePackageAddress.add()
    pa.shipid = shipid
    pa.x = dst_x
    pa.y = dst_y
    amazon_seqnum = world.getASeqnum()
    pa.seqnum = amazon_seqnum
  
    #send message to amazon
    aackset = amazon.getAAckSet()
    while amazon_seqnum not in aackset:
      amazon.sendMsgToAmazon(ua_messages) 
      time.sleep(TIME_WAIT)
      aackset = amazon.getAAckSet()
    
  except Exception as e:
    print(e)

#@interface (query truck status to world)
def UQueryTruckStatus(truckid):
  try:
    ucommands = world_ups_pb2.UCommands()
    query = ucommands.queries.add()
    query.truckid = truckid
    world_seqnum = amazon.getWorldSeqnum()
    query.seqnum = world_seqnum
    
    #send message to world and wait ack
    ackset = world.getAckSet()
    while world_seqnum not in ackset:
      world.sendMsgToWorld(ucommands)
      time.sleep(TIME_WAIT)
      ackset = world.getAckSet()
      
  except Exception as e:
    print(e)
      
  
