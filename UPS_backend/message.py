import socket

#message settings
MAX_MSG_LEN = 65536

def sendMsgToWorld(world_socket, data):
  try:
    if world_socket is not None:
      msg = data.SerializeToString()
      world_socket.sendall(msg)
  except Exception as e:
    print("Error occurs while sending the message: ", e)

def recMsgFromWorld(world_socket):
  try:
    if world_socket is not None:
      resp = world_socket.recv(MAX_MSG_LEN, socket.MSG_WAITALL)
      return resp
  except Exception as e:
    print("Error occurs while receiving the message: ", e)

#send message to the world
def sendMsgToAmazon(amazon_socket, data):
  try:
    if amazon_socket is not None:
      msg_string = data.SerializeToString()
      msg = '%s\n%s'%(len(msg_string), msg_string)
      amazon_socket.sendall(msg)
  except Exception as e:
    print("Error occurs while sending the message: ", e)
    
#receive message from the world
def recMsgFromAmazon(amazon_socket):
  try:
    if amazon_socket is not None:
      resp_header = amazon_socket.recv(100, socket.MSG_WAITALL)
      resp_len,resp = resp_header.split('\n',1)
      rem_len = int(resp_len)-len(resp)
      if rem_len > 0:
        resp += amazon_socket.recv(rem_len, socket.MSG_WAITALL)
      return resp
  except Exception as e:
    print("Error occurs while receiving the message: ", e)
    

