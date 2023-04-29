import socket
from google.protobuf.internal.encoder import _EncodeVarint, _VarintEncoder
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
    
def encode_varint(varint):
    data_buffer = []
    _VarintEncoder()(data_buffer.append, varint, None)
    return b''.join(data_buffer)

def sendMsg(socket, data):
  msg = data.SerializeToString()
  message_size = encode_varint(len(msg))
  socket.sendall(message_size + msg)
  # _EncodeVarint(socket.send, len(msg), None)
  # socket.send(msg)

def recMsg(socket):
  raw_data_size = b''
  while True:
    try:
        raw_data_size += socket.recv(1)
        data_size = _DecodeVarint32(raw_data_size, 0)[0]
        break
    except IndexError as e:
        continue
  raw_data_msg = socket.recv(data_size)
  return raw_data_msg