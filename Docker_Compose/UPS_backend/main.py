import socket
import select
import threading

import world
import amazon
import interface

#truck num
TRUCK_NUM = 10

def connectToFrontend():
  print("Starting listening frontend request ...")
  thread = threading.Thread(target = interface.acceptFConnection)
  thread.start()

if __name__ == "__main__":
  try:
    #connect to world and amazon
    print("Starting UPS Backend ...")
    world_socket = world.connectToWorldServer()
    connectToFrontend()

    print("Starting interacting with world and amazon ...")
    #amazon_socket = amazon.acceptAConnection() #block
  
    #while amazon.getWorldID() is None:
    #amazon.synchronizeWithAmazon()
    
    connect = False
    while connect is False:
      connect = world.sayHelloToWorld(TRUCK_NUM)

    '''
    #select
    fdset = [world_socket, amazon_socket]
  
    while True:
      rl, wl, error = select.select(fdset, [], [])
      if len(rl) != 0:
        for fd in rl:
          if fd is world_socket:
            print("process world socket")
            world.worldRespRouter()
          else:
            print("process amazon socket")
            amazon.amazonRespRouter()
            
    world_socket.close()
    amazon_socket.close()
    '''
  except Exception as e:
    print(e)
  
