import socket
import select

import world
import amazon

TRUCK_NUM = 10

if __name__ == "__main__":
  try:
    #connect to world and amazon
    world_socket = world.connectToWorldServer()
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
            world.worldRespRouter()
          else:
            amazon.amazonRespRouter()
            
    world_socket.close()
    amazon_socket.close()
    '''
  except Exception as e:
    print(e)
    '''
  finally:
    if world_socket:
      world_socket.close()
    if amazon_socket:
      amazon_socket.close()
      '''
  
