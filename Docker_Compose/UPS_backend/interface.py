import socket
import psycopg2
import time
from protobuf import world_ups_pb2
from protobuf import ups_amazon_pb2

import world
import amazon

TIME_WAIT = 5

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
      
  
