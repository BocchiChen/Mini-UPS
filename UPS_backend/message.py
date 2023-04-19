import socket

#send message to the world
def sendMsg(world_socket, data):
  try:
    msg_string = data.SerializeToString()
    msg = '%s\n%s'%(len(msg_string), msg_string)
    world_socket.sendall(msg.encode())
  except Exception as e:
    print("Error occurs while sending the message: ", e)
    
#receive message from the world
def recMsg(world_socket):
  try:
    resp_header = world_socket.recv(100).decode()
    resp_len,resp = resp_header.split('\n',1)
    rem_len = int(resp_len)-len(resp)
    if rem_len > 0:
      resp += world_socket.recv(rem_len, socket.MSG_WAITALL).decode()
    return resp
  except Exception as e:
    print("Error occurs while receiving the message: ", e)
    

