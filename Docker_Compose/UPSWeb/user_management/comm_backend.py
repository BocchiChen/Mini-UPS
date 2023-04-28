import socket

def connectToBackEndServer():
  try:
    backend_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    backend_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    address = ("localhost", 34568)
    backend_socket.connect(address)
    return backend_socket
  except Exception as e:
    print("Error occurs while connecting the world: ", e)

def sendAddrMSgToBackEnd(backend_socket, msg): # ship, dst_x, dst_y str
  try:
    backend_socket.sendall(msg.encode())
  except:
    raise Exception('Please check connection with backend server!')

def sendTruckIdMsgToBackEnd(backend_socket, msg): # truckid str
  try:
    backend_socket.sendall(msg.encode())
  except:
    raise Exception('Please check connection with backend server!')