import socket
import psycopg2
import time
import threading
from protobuf import world_ups_pb2
from protobuf import ups_amazon_pb2
from concurrent.futures import ThreadPoolExecutor

import world
import amazon

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
    while True:
      conn_socket, address = sock.accept()
      print("Receive front connection from: ", address)
      msg = conn_socket.recv(MAX_MSG_LEN).decode()
      lt = msg.split(',')
      print(lt)
      if len(lt) == 3:
        task = executor.submit(AUpdatePackageAddress(lt[0], lt[1], lt[2]))
      else:
        task = executor.submit(UQueryTruckStatus(lt[0]))
  except Exception as e:
    print("Error occurs while creating and binding to the listening address: ", e)

#@interface (send package address to amazon)
def AUpdatePackageAddress(shipid, dst_x, dst_y):
  try:
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

#@interface (send package address to amazon)
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
      
  