import socket
from google.protobuf.internal.encoder import _VarintEncoder
from google.protobuf.internal.decoder import _DecodeVarint32

#message
MAX_MSG_LEN = 65535

def sendMsgToWorld(world_socket, data):
  try:
    if world_socket is not None:
      sendMsg(world_socket, data)
  except Exception as e:
    print("Error occurs while sending the message: ", e)

def recMsgFromWorld(world_socket):
  try:
    if world_socket is not None:
      return recMsg(world_socket)
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
      return recMsg(amazon_socket)
  except Exception as e:
    print("Error occurs while receiving the message: ", e)
    
def processEncode(msg_len):
    buf = []
    _VarintEncoder()(buf.append, msg_len, None)
    return b''.join(buf)

def sendMsg(socket, data):
  msg = data.SerializeToString()
  message_size = processEncode(len(msg))
  socket.sendall(message_size + msg)

def recMsg(socket):
  data_size = b''
  while True:
    try:
        data_size += socket.recv(1)
        data_size = _DecodeVarint32(data_size, 0)[0]
        break
    except IndexError as e:
        continue
  message = socket.recv(data_size)
  return message