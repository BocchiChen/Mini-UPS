import socket
from protobuf import world_ups_pb2
from protobuf import ups_amazon_pb2
import message
import time
UPS_HOST = "vcm-30507.vm.duke.edu"
UPS_PORT = 34567

if __name__ == "__main__":
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    address = (UPS_HOST, UPS_PORT)
    sock.connect(address)

    au_connect = ups_amazon_pb2.AUConnect()
    au_connect.worldid = 1
    message.sendMsg(sock, au_connect)

    #resp = message.recMsg(sock)
    #print(resp)
    
    au_messages = ups_amazon_pb2.AUMessages()
    o = au_messages.order.add()
    #o.userid = "chen"
    o.order.id = 121
    o.order.description = "car"
    o.order.count = 1
    o.order.x = 10
    o.order.y = 10
    o.order.whid = 1
    o.shipid = 121
    o.seqnum = 2
    print(au_messages)
    message.sendMsg(sock, au_messages)
    msg = message.recMsg(sock)
    ua_messages = ups_amazon_pb2.UAMessages()
    ua_messages.ParseFromString(msg)
    print(ua_messages.acks)
    time.sleep(2)
    #msg = message.recMsg(sock)
    #ua_messages = ups_amazon_pb2.UAMessages()
    #ua_messages.ParseFromString(msg)
    #print(ua_messages)
   #time.sleep(5)
    au_messages = ups_amazon_pb2.AUMessages()
    o = au_messages.order.add()
    #o.userid = "chen"
    o.order.id = 121
    o.order.description = "car"
    o.order.count = 1
    o.order.x = 10
    o.order.y = 10
    o.order.whid = 1
    o.shipid = 121
    o.seqnum = 2
    print(au_messages)
    message.sendMsg(sock, au_messages)
    #msg = message.recMsg(sock)
    #ua_messages = ups_amazon_pb2.UAMessages()
    #ua_messages.ParseFromString(msg)
    #print(ua_messages)
    #time.sleep(2)
    time.sleep(10000)
    
