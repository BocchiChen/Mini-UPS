import socket
import select
import threading
import time

import world
import amazon
import interface
import database

#truck num
TRUCK_NUM = 10

def connectToFrontend():
  print("Starting listening frontend request ...")
  thread = threading.Thread(target = interface.acceptFConnection)
  thread.start()


if __name__ == "__main__":
  #connect to world and amazon
  print("Starting UPS Backend ...")
  world_socket = world.connectToWorldServer()
  connectToFrontend()

  print("Starting interacting with world and amazon ...")
    
  amazon_socket = amazon.acceptAConnection() #block

  #while amazon.getWorldID() is None:
  amazon.synchronizeWithAmazon()
  
  #connect = False
  #while connect is False:
  connect = world.sayHelloToWorld(TRUCK_NUM)
    
  epoll = select.epoll()
  epoll.register(world_socket.fileno(), select.EPOLLIN)
  epoll.register(amazon_socket.fileno(), select.EPOLLIN)
  try:
    while True:
      events = epoll.poll()
      for fileno, event in events:
        if fileno == world_socket.fileno():
          print("Starting processing world socket ...")
          world.worldRespRouter()
        elif fileno == amazon_socket.fileno():
          print("Starting processing amazon socket ...")
          amazon.amazonRespRouter()
  except Exception as e:
    print(e)
  finally:
    epoll.unregister(world_socket.fileno())
    epoll.unregister(amazon_socket.fileno())
    epoll.close()
    world_socket.close()
    amazon_socket.close()
  