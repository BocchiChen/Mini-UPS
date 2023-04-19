import socket
import psycopg2
from protobuf import ups_amazon_pb2
import threading

from message import *
from database import *

#world settings
AMAZON_HOST = ''
AMAZON_PORT = 12345

#message settings
#MAX_MSG_LEN = 65536

#global variables
amazon_socket = None

#connect to the world
def connectToAmazon():
  try:
    amazon_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    #amazon_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    address = (AMAZON_HOST, AMAZON_PORT)
    amazon_socket.connect(address)
    return amazon_socket
  except Exception as e:
    print("Error occurs while connecting the amazon: ", e)

#communicate with amazon
def communicateWithAmazon():
  global world_socket
  global world_id
  try:
    
  except Exception as e:
    print("Error occurs while communicating with the amazon: ", e)

