#!/usr/bin/env python

"""This is the Switch Starter Code for ECE50863 Lab Project 1
Author: Xin Du
Email: du201@purdue.edu
Last Modified Date: December 9th, 2021
"""

import sys
from datetime import date, datetime
import socket
import threading
import operator
import time

# Please do not modify the name of the log file, otherwise you will lose points because the grader won't be able to find your log file
# The log file for switches are switch#.log, where # is the id of that switch (i.e. switch0.log, switch1.log). The code for replacing # with a real number has been given to you in the main function.
LOG_FILE = "switch#.log"

# Those are logging functions to help you follow the correct logging standard

# "Register Request" Format is below:
#
# Timestamp
# Register Request Sent


def register_request_sent():
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append(f"Register Request Sent\n")
    write_to_log(log)

# "Register Response" Format is below:
#
# Timestamp
# Register Response Received


def register_response_received():
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append(f"Register Response received\n")
    write_to_log(log)

# For the parameter "routing_table", it should be a list of lists in the form of [[...], [...], ...].
# Within each list in the outermost list, the first element is <Switch ID>. The second is <Dest ID>, and the third is <Next Hop>.
# "Routing Update" Format is below:
#
# Timestamp
# Routing Update
# <Switch ID>,<Dest ID>:<Next Hop>
# ...
# ...
# Routing Complete
#
# You should also include all of the Self routes in your routing_table argument -- e.g.,  Switch (ID = 4) should include the following entry:
# 4,4:4


def routing_table_update(routing_table):
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append("Routing Update\n")
    for row in routing_table:
        log.append(f"{row[0]},{row[1]}:{row[2]}\n")
    log.append("Routing Complete\n")
    write_to_log(log)

# "Unresponsive/Dead Neighbor Detected" Format is below:
#
# Timestamp
# Neighbor Dead <Neighbor ID>


def neighbor_dead(switch_id):
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append(f"Neighbor Dead {switch_id}\n")
    write_to_log(log)

# "Unresponsive/Dead Neighbor comes back online" Format is below:
#
# Timestamp
# Neighbor Alive <Neighbor ID>


def neighbor_alive(switch_id):
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append(f"Neighbor Alive {switch_id}\n")
    write_to_log(log)


def write_to_log(log):
    with open(LOG_FILE, 'a+') as log_file:
        log_file.write("\n\n")
        # Write to log
        log_file.writelines(log)


def prompt(msg, msg_name):
    print(msg_name+"\n"+msg)

import json
def pretty(d):
    return (json.dumps(d, indent=4, ensure_ascii=False))
    
def main():

    global LOG_FILE

    # Check for number of arguments and exit if host/port not provided
    num_args = len(sys.argv)
    if num_args < 4:
        print(
            "switch.py <Id_self> <Controller hostname> <Controller Port> -f <Neighbor ID>\n")
        sys.exit(1)

    #global infor
    my_id = int(sys.argv[1])
    ctrl_hostname = sys.argv[2]
    ctrl_port = int(sys.argv[3])
    K = 10  # period
    Timeout = K*3

    edge_table = {}

    LOG_FILE = 'switch' + str(my_id) + ".log"

    # Support multiple -f arguments
    f_neighbors = []
    if num_args == 6:
        if sys.argv[4] == '-f':
            f_neighbors.append(int(sys.argv[5]))

    print("controller hostname: ", ctrl_hostname)
    print("controller port: ", ctrl_port)
    print("f_neighbors: ", f_neighbors)

    switch_socket = socket.socket(
        socket.AF_INET, socket.SOCK_DGRAM)  # IPv4,for UDP
    # switch as client, connect to controller as server
    host_addr = (ctrl_hostname, ctrl_port)
    switch_socket.connect(host_addr)

    def udp_register_request_sent():
        msg = "register_request "+str(my_id)
        prompt(msg, "send")
        switch_socket.sendall(msg.encode())
        register_request_sent()

    def udp_register_response_received():
        # Register Response message
        # <number-of-neighbors>
        # <neighboring switch id> <hostname of this switch> <port of this switch>
        msg, _ = switch_socket.recvfrom(1024)
        msg = msg.decode()
        prompt(msg, "recv")
        # Parse the message
        msg = msg.split('\n')
        if msg[0] == "register_response":
            # 忽略msg[1]number-of-neighbors 不需要
            # 此时会返回neighbor的信息，增添is_neighbor属性
            for i in range(2, len(msg)):
                link = msg[i].split()
                if len(link) != 3:
                    break
                end_id = int(link[0])
                addr1 = link[1]  # hostname
                addr2 = int(link[2])  # port

                edge_table[end_id] = {
                    "state": True,
                    "is_neighbor": True,
                    "next_hop": -1,
                    "addr": (addr1, addr2),
                    "refresh": False
                }
            # add 自己到自己
            edge_table[my_id] = {
                "state": True,
                "is_neighbor": True,
                "next_hop": my_id,
                "addr": "",  # 不需要知道自己的地址吧？如果后续报错视为错误
                "refresh": False
            }
        register_response_received()

    # 发生注册请求
    udp_register_request_sent()
    # 接收注册请求响应
    udp_register_response_received()

    # 接下来，要处理并发，加锁
    lock = threading.Lock()   
    lock_msg = threading.Lock()
    lock_rec_Queue=threading.Lock()
    # lock_socket=threading.Lock()
    # lock_k = threading.Lock()  # 第k秒，接收keep alive的优先级比向ctrl发送table的优先级高

    # 让一个线程专门负责发送
    # 让一个线程专门负责接收
    # 各功能线程将
    msgQueue = []  # 共享资源，消息队列
    msg_rev_Queue=[]

    def make_routing_table_update(edge_table, my_id):
        # <Switch ID>,<Dest ID>:<Next Hop>
        # 持锁进程调用此函数

        routing_table = []
        for end_id in edge_table:
            routing_table.append([
                my_id,
                end_id,
                edge_table[end_id]["next_hop"]
            ])
        routing_table.sort(key=lambda x: (x[0], x[1]))
        return routing_table

    def send_alive_simple():
      # 由持锁进程调用
        # 向除了自己的、活的、邻居发alive
        msg = "KEEP_ALIVE\n{0}\n".format(my_id)
        msgQueue_temp = []
        for end_id in edge_table:
            if end_id == my_id:
                continue
            if not edge_table[end_id]["is_neighbor"]:
                continue
            if not edge_table[end_id]["state"]:
                continue
            addr = edge_table[end_id]["addr"]
            # switch_socket.sendto(msg.encode(), addr)
            # prompt(msg, "send keep alive to "+str(end_id))
            msgQueue_temp.append({
                "msg": msg,
                "addr": addr
            })
        lock_msg.acquire()
        for i in msgQueue_temp:
            msgQueue.append(i)
        lock_msg.release()

    def send_alive_thread():
        lock.acquire()
        send_alive_simple()
        lock.release()

    def send_link_simple():
        # 由持锁进程调用
        # 向控制器发送自己所有的邻居死活情况
        msg = "routing_table_update\n"
        msg += str(my_id)+'\n'
        for end_id in edge_table:
            if end_id == my_id:
                continue
            if not edge_table[end_id]["is_neighbor"]:
                continue
            msg += "{0} {1}\n".format(end_id, edge_table[end_id]["state"])

        #switch_socket.sendto(msg.encode(), host_addr)
        lock_msg.acquire()
        msgQueue.append({
            "msg": msg,
            "addr": host_addr
        })
        lock_msg.release()
        # prompt(msg, "send route table to ctrl")

    def send_link_thread():
        lock.acquire()
        send_link_simple()
        lock.release()

    def refresh_edge_table_simple(msg=None, is_init=False, end_id=None, flag=None):
        # 传入 对\n split后的msg
        if msg != None:  # 根据msg进行更新
            if msg[0] == 'routing_table_update':
                start_id = int(msg[1])
                if start_id != my_id:
                    exit(-1)

                edge_table_temp = edge_table

                # 若不是初始化
                if not is_init:
                    for end_id in edge_table:  # 先把所有点置死
                        edge_table[end_id]["state"] = False

                for i in range(2, len(msg)):
                    link = msg[i].split()
                    if len(link) != 2:
                        break
                    end_id = int(link[0])
                    next_hop = int(link[1])

                    if is_init:  # 如果是初始化，要对非邻居的点先初始化
                        if end_id not in edge_table:
                            edge_table[end_id] = {
                                "state": True,
                                "is_neighbor": False,
                                "next_hop": -1,
                                # "addr": (addr1, addr2),
                                # "refresh": False
                            }

                    edge_table[end_id]["next_hop"] = next_hop
                    edge_table[end_id]["state"] = True
                    if end_id not in edge_table_temp:
                        edge_table[end_id]["refresh"] = False

                if not is_init:
                    # 若不是初始化，如果table无变动，不需要log
                    if operator.eq(edge_table_temp, edge_table):
                        return False
        else:  # 根据state=flag进行更新
            edge_table[end_id]["refresh"] = True  # 刷新
            if edge_table[end_id]["state"] == flag:  # 若state不变，则退出,不log
                return False
            edge_table[end_id]["state"] = flag

        if not is_init:  # 如果不是初始化，既要log也要将更新的路由表发送给控制器
            send_link_simple()

        # log
        routing_table = make_routing_table_update(edge_table, my_id)
        print("log routing_table:\n", routing_table)
        routing_table_update(routing_table)
        return True

    def refresh_edge_table(msg=None, is_init=False, end_id=None, flag=None):
      lock.acquire()
      refresh_edge_table_simple(msg,is_init,end_id,flag)
      lock.release()

    def udp_routing_table_update_received():
        msg, _ = switch_socket.recvfrom(1024)
        msg = msg.decode()
        prompt(msg, "recv route table firstly")
        # Parse the message
        msg = msg.split('\n')
        if msg[0] == 'routing_table_update':
            refresh_edge_table(msg, True)

    # 第一次接收路由表
    udp_routing_table_update_received()
        
    def send_infor():
      while True:
        lock_msg.acquire()
        if len(msgQueue)==0:
          lock_msg.release()
          time.sleep(K*0.1==0)
          continue
        else:
          msgQueue.sort(key=lambda x:x["msg"][0]=='r')
          print("\n msqQueue:\n",pretty(msgQueue))
          
          msg_dict=msgQueue.pop(0)
          print("\nsend to ",msg_dict["addr"],":")
          print(msg_dict["msg"])
          # lock_socket.acquire()
          switch_socket.sendto(msg_dict["msg"].encode(), msg_dict["addr"])
          # lock_socket.release()
          lock_msg.release()
          
    def rec_infor():
      while True:
        # print(9*'*')
        msg, switch_addr = switch_socket.recvfrom(1024)
        lock_rec_Queue.acquire()
        msg_rev_Queue.append({
          "msg":msg.decode(),
          "addr":switch_addr
        })
        
        lock_rec_Queue.release()
        
    def deal_rec_infor():
      while True:
        # 接收来自邻居交换机的活信息与来自控制器的路由更新表
        
        lock_rec_Queue.acquire()

        if len(msg_rev_Queue)==0:
          lock_rec_Queue.release()
          time.sleep(K*0.1)
          continue
        
        print("msg_rev_Queue:\n",msg_rev_Queue)
        
        msg_dict=msg_rev_Queue.pop(0)
    
        lock_rec_Queue.release()
        
        
        msg=msg_dict["msg"]
        msg_temp = msg
        msg = msg.split('\n')
        # 可以通过发送地址或信息头来确定信息类别
        if msg[0] == 'routing_table_update':
            prompt(msg_temp, "rec route uptate from ctrl")
            refresh_edge_table(msg, False)
        elif msg[0] == 'KEEP_ALIVE':
            prompt(msg_temp, "rec alive from "+str(msg[1]))
            refresh_edge_table(msg=None, is_init=None,
                                end_id=int(msg[1]), flag=True)

    def check_dead():
        # 检测是否所有活邻居都alive刷新了
        
        #把当前要发送的消息发完才能checkdead
        while True:
          lock_msg.acquire()
          if len(msgQueue)==0:
            lock_msg.release()
            break
          else:
            lock_msg.release()

        for end_id in edge_table:
            if not edge_table[end_id]["state"]:
                continue
            if not edge_table[end_id]["is_neighbor"]:
                continue
            # 若未刷新，则置死
            if edge_table[end_id]["refresh"] != True:
                print("make {0}# switch dead".format(end_id))
                refresh_edge_table_simple(msg=None, is_init=None,
                                   end_id=end_id, flag=False)
                neighbor_dead(end_id)
            edge_table[end_id]["refresh"] = False

    # 定时进程
    class RepeatingTimer(threading.Timer):
        def run(self):
            while not self.finished.is_set():
                self.function(*self.args, **self.kwargs)
                self.finished.wait(self.interval)
                
    
    # time.sleep(K)

    #将alive送到消息队列
    t_send_alive = RepeatingTimer(K, send_alive_thread)
    t_send_alive.start()
    # t_send_alive.cancel() #when to kill this thread?
    
    #将send消息队列中的消息出队、发送
    t_send_infor = threading.Thread(target=send_infor)
    t_send_infor.start()

    #接受信息，送入接受信息队列
    t_rec_infor = threading.Thread(target=rec_infor)
    t_rec_infor.start()
    
    #将接收信息队列中的信息取出，处理
    t_deal_rec_infor = threading.Thread(target=deal_rec_infor)
    t_deal_rec_infor.start()

    #处理dead的switch
    t_check_dead = RepeatingTimer(Timeout, check_dead)
    t_check_dead.start()
    
    #将拓扑更新信息送到消息队列
    t_send_link = RepeatingTimer(K, send_link_thread)
    t_send_link.start()



if __name__ == "__main__":
    main()
