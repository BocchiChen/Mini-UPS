import socket
import select

import world
import amazon

if __name__ == "__main__":
  
  world_socket = world.connectToWorldServer()
  amazon_socket = amazon.connectToAmazon()
  
  amazon.synchronizeWithAmazon()
  world.sayHelloToWorld(10)
  
  fdset = [world_socket, amazon_socket]
  
  while True:
    rl, rl, error = select.select(fdset, [], [])
    if len(rl) != 0:
      for fd in rl:
        if fd is world_socket:
          world.worldRespRouter()
        else:
          amazon.amazonRespRouter()

  world_socket.close()
  amazon_socket.close()
  
