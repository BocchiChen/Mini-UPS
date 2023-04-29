import os
import socket
import select
import threading

import world
import amazon
import interface

#truck num
TRUCK_NUM = 10

if __name__ == "__main__":
  try:
    #connect to world and amazon
    print("Starting UPS...")
    world_socket = world.connectToWorldServer()
    pid = os.fork()
    if pid == 0:
      print("Entering child process work area")
      interface.acceptFConnection()
    else:
      print("Entering parent process work area")
      amazon_socket = amazon.acceptAConnection()
  
      while amazon.getWorldID() is None:
        amazon.synchronizeWithAmazon()
    
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
            world.worldRespRouter(dbconn)
          else:
            print("process amazon socket")
            amazon.amazonRespRouter(dbconn)
    '''
  except Exception as e:
    print(e)
  
