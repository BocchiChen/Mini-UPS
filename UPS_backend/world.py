import socket
import psycopg2
from protobuf import world_ups_pb2
import threading

from message import *
from database import *

#world settings
WORLD_HOST = ''
WORLD_PORT = 12345

#message settings
#MAX_MSG_LEN = 65536

#global variables
world_socket = None
world_id = None

#connect to the world
def connectToWorld():
  try:
    world_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    #world_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    address = (WORLD_HOST, WORLD_PORT)
    world_socket.connect(address)
    return world_socket
  except Exception as e:
    print("Error occurs while connecting the world: ", e)
    
#create new world (send message to world without worldid)
def createNewWorld():
  global world_socket
  global world_id
  try:
    data = world_ups_pb2.UConnect()
    data.isAmazon = False
    sendMsg(world_socket, data)
    resp = world_ups_pb2.UConnected()
    resp.ParseFromString(recMsg(world_socket))
    print("Received response from World says: ", resp)
    world_id = resp.worldid
  except Exception as e:
    print("Error occurs while creating new world: ", e)

#communicate with world
def communicateWithWorld(truck_num):
  global world_socket
  global world_id
  try:
    conn = connectToDB()
    clearDB()
    
    data = world_ups_pb2.UConnect()
    data.worldid = world_id
    data.isAmazon = False
    
    #init and add trucks
    for i in range(0, truck_num):
      truck = data.trucks.add()
      truck.id = i
      truck.x = 0
      truck.y = 0
      query = "INSERT INTO TRUCKS " + "(TRUCK_ID, TRUCK_STATUS)" + "VALUES (" + i + ", '" + str(idle) + "');"
      executeQuery(query)
    conn.commit()
    
    sendMsg(world_socket, data)
    resp = world_ups_pb2.UConnected()
    resp = recMsg(world_socket)
    
    return resp
  except Exception as e:
    print("Error occurs while communicating with the world: ", e)

def recvWResponse():
  global world_socket
  resp = world_ups_pb2.UResponses()
  msg = recMsg(world_socket)
  resp.ParseFromString(msg)
  return resp
  
  
