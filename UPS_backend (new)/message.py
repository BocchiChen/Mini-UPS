import socket
from google.protobuf.internal.encoder import _EncodeVarient, _VarintBytes
from google.protobuf.internal.encoder import _DecodeVarint32

def sendMsgToWorld(world_socket, data):
  try:
    if world_socket is not None:
      
  except Exception as e:
    print("Error occurs while sending the message: ", e)

def recMsgFromWorld(world_socket):
  try:
    if world_socket is not None:
      
  except Exception as e:
    print("Error occurs while receiving the message: ", e)

#send message to the world
def sendMsgToAmazon(amazon_socket, data):
  try:
    if amazon_socket is not None:
      
  except Exception as e:
    print("Error occurs while sending the message: ", e)
    
#receive message from the world
def recMsgFromAmazon(amazon_socket):
  try:
    if amazon_socket is not None:
      
  except Exception as e:
    print("Error occurs while receiving the message: ", e)
    

