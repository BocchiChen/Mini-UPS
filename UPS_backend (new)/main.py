import socket
import select

import world
import amazon

if __name__ == "__main__":
  try:
    #connect to world and amazon
    world_socket = world.connectToWorldServer()
    amazon_socket = amazon.connectToAmazon()
  
    while amazon.getWorldID() is None:
      amazon.synchronizeWithAmazon()
    
    connect = False
    while connect is False:
      connect = world.sayHelloToWorld(20)
    
    #select
    fdset = [world_socket, amazon_socket]
  
    while True:
      rl, rl, error = select.select(fdset, [], [])
      if len(rl) != 0:
        for fd in rl:
          if fd is world_socket:
            world.worldRespRouter()
          else:
            amazon.amazonRespRouter()

  except Exception as e:
    print(e)
  finally:
    world_socket.close()
    amazon_socket.close()
  
