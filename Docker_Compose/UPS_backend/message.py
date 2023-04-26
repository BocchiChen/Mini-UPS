import socket
from google.protobuf.internal.encoder import _EncodeVarint
from google.protobuf.internal.decoder import _DecodeVarint32

def sendMsgToWorld(world_socket, data):
  try:
    if world_socket is not None:
      sendMsg(world_socket, data)
  except Exception as e:
    print("Error occurs while sending the message: ", e)

def recMsgFromWorld(world_socket):
  try:
    if world_socket is not None:
      recMsg(world_socket)
  except Exception as e:
    print("Error occurs while receiving the message: ", e)

#send message to the amazon
def sendMsgToAmazon(amazon_socket, data):
  try:
    if amazon_socket is not None:
      sendMsg(amazon_socket, data)
  except Exception as e:
    print("Error occurs while sending the message: ", e)
    
#receive message from the amazon
def recMsgFromAmazon(amazon_socket):
  try:
    if amazon_socket is not None:
      recMsg(amazon_socket)
  except Exception as e:
    print("Error occurs while receiving the message: ", e)
    
def sendMsg(socket, data):
  msg = data.SerializeToString()
  _EncodeVarint(socket.sendall, len(msg), None)
  socket.sendall(msg)

def recMsg(socket):
  var_int_buff = []
  while Ture:
    buf = socket.recv(1)
    var_int_buff += buf
    msg_len, new_pos = _DecodeVarint32(var_int_buff, 0)
    if new_pos != 0:
      break
  whole_message = socket.recv(msg_len)
  return whole_message
    

