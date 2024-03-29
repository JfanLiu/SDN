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
import json
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


switch_socket = None


def main():

    global LOG_FILE
    global switch_socket
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
    K = 2  # period
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
    # switch_socket.connect(host_addr)

    def udp_register_request_sent():
        msg_dict = {
          "msg": "register_request",
          "id":my_id,
          "f_ls":f_neighbors,
          "addr": host_addr
        }
        prompt(str(msg_dict), "send")
        switch_socket.sendto(json.dumps(msg_dict).encode(), host_addr)
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
                
                #register_response发送的都是邻居

                edge_table[end_id] = {
                    "state": True,
                    # "is_neighbor": True,
                    "is_neighbor": end_id not in f_neighbors,
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
    # lock_k = threading.Lock()  # 第k秒，接收keep alive的优先级比向ctrl发送table的优先级高

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

    def send_alive():
        lock.acquire()

        def send_alive_thread():
            # 向除了自己的、活的、邻居发alive
            msg = "KEEP_ALIVE\n{0}\n".format(my_id)
            for end_id in edge_table:
                if end_id == my_id:
                    continue
                if not edge_table[end_id]["is_neighbor"]:
                    continue
                if not edge_table[end_id]["state"]:
                    continue
                addr = edge_table[end_id]["addr"]

                msg_dict = {
                    "msg": msg,
                    "addr": addr,#这个地址不能用，仅用来表明要通过ctrl转发
                    "addr_id": end_id,#用id从控制器获取新地址
                }
                switch_socket.sendto(json.dumps(msg_dict).encode(), host_addr)
                prompt(msg, "send keep alive to "+str(end_id))

        send_alive_thread()
        lock.release()

    def send_link_simple():
      # 向控制器发送自己所有的邻居死活情况
        msg = "routing_table_update\n"
        msg += str(my_id)+'\n'
        for end_id in edge_table:
            if end_id == my_id:
                continue
            if not edge_table[end_id]["is_neighbor"]:
                continue
            msg += "{0} {1}\n".format(end_id, edge_table[end_id]["state"])

        msg_dict = {
            "msg": msg,
            "addr": host_addr
        }
        switch_socket.sendto(json.dumps(msg_dict).encode(), host_addr)
        prompt(msg, "send route table to ctrl")

    def send_link():
      # 向控制器发送自己所有的邻居死活情况
        lock.acquire()
        send_link_simple()
        lock.release()

    def refresh_edge_table(msg=None, is_init=False, end_id=None, flag=None):
      # 传入 对\n split后的msg
        if msg != None:  # 根据msg进行更新
            if msg[0] == 'routing_table_update':
                start_id = int(msg[1])
                if start_id != my_id:
                    exit(-1)

                # edge_table_temp = edge_table

                # # 若不是初始化
                # if not is_init:
                #     for end_id in edge_table:  # 先把所有点置死
                #         edge_table[end_id]["state"] = False

                #接受所有路由表
                for i in range(2, len(msg)):
                    link = msg[i].split()
                    if len(link) != 2:
                        break
                    end_id = int(link[0])
                    next_hop = int(link[1])

                    if is_init:  # 如果是初始化，要对非邻居的点先初始化
                        if end_id not in edge_table:
                            edge_table[end_id] = {
                                "state": True,#非邻居的死活不重要
                                "is_neighbor": False,
                                "next_hop": -1,
                                # "addr": (addr1, addr2),
                                # "refresh": False
                            }

                    edge_table[end_id]["next_hop"] = next_hop
                    # edge_table[end_id]["is_neighbor"] = next_hop==end_id#-f
                    
                    #用next_hop表示这个交换机的死活.对于连通图而言成立
                    if edge_table[end_id]["state"]==True and next_hop==-1 and edge_table[end_id]["is_neighbor"]:
                      neighbor_dead(end_id)#对于邻居置死，log dead
                    edge_table[end_id]["state"] = next_hop!=-1#让重连的图死而复生
                    
                    edge_table[end_id]["refresh"] = True#更新路由表时姑且认为刷新了
                #     if end_id not in edge_table_temp:
                #         edge_table[end_id]["refresh"] = False

                # if not is_init:
                #     # 若不是初始化，如果table无变动，不需要log
                #     if operator.eq(edge_table_temp, edge_table):
                #         return
        else:  # 根据state=flag进行更新
            edge_table[end_id]["refresh"] = True  # 刷新
            if edge_table[end_id]["state"] != flag:  
                #若state改变，由于switch没有计算能力，sendlink，让ctrl来做更新广播
                edge_table[end_id]["state"] = flag
                send_link_simple()
            return# 若state不变，直接退出

        if not is_init:  # 如果不是初始化，既要log也要将更新的路由表发送给控制器
            send_link_simple()

        # log
        routing_table = make_routing_table_update(edge_table, my_id)
        print("log routing_table:\n", routing_table)
        routing_table_update(routing_table)

    def udp_routing_table_update_received():
        msg, _ = switch_socket.recvfrom(1024)
        msg = msg.decode()
        prompt(msg, "recv route table firstly")
        # Parse the message
        msg = msg.split('\n')
        lock.acquire()
        if msg[0] == 'routing_table_update':
            refresh_edge_table(msg, True)
        lock.release()

    # 第一次接收路由表
    udp_routing_table_update_received()

    def rec_infor():
        global switch_socket
        while True:
            # 接收来自邻居交换机的活信息与来自控制器的路由更新表
            try:
                msg, _ = switch_socket.recvfrom(1024)
            except:
                switch_socket.close()
                switch_socket = socket.socket(
                    socket.AF_INET, socket.SOCK_DGRAM)  # IPv4,for UDP
                msg_dict = {
                    "msg": f"update_addr\n{my_id}\n",
                    "addr": host_addr
                }
                switch_socket.sendto(json.dumps(msg_dict).encode(), host_addr)
                print("error!!!!!!!")
                continue
            msg = msg.decode()
            msg_temp = msg
            msg = msg.split('\n')

            lock.acquire()

            # 可以通过发送地址或信息头来确定信息类别
            if msg[0] == 'routing_table_update':
                prompt(msg_temp, "rec route uptate from ctrl")
                refresh_edge_table(msg, False)
            elif msg[0] == 'KEEP_ALIVE':
                prompt(msg_temp, "rec alive from "+str(msg[1]))
                refresh_edge_table(msg=None, is_init=None,
                                   end_id=int(msg[1]), flag=True)

            lock.release()

    def check_dead():
        # 检测是否所有活邻居都alive刷新了
        lock.acquire()
        for end_id in edge_table:
            if not edge_table[end_id]["is_neighbor"]:
                continue
            if not edge_table[end_id]["state"]:
                continue
            if end_id == my_id:  # 不查自己
                continue
            # 若未刷新，则置死
            if edge_table[end_id]["refresh"] != True:
                neighbor_dead(end_id)
                refresh_edge_table(msg=None, is_init=None,
                                   end_id=end_id, flag=False)
            edge_table[end_id]["refresh"] = False
        lock.release()

    # 定时进程
    class RepeatingTimer(threading.Timer):
        def run(self):
            while not self.finished.is_set():
                self.function(*self.args, **self.kwargs)
                self.finished.wait(self.interval)

    # 先启动接收
    t_rec_infor = threading.Thread(target=rec_infor)
    t_rec_infor.start()

    t_send_alive = RepeatingTimer(K, send_alive)
    t_send_alive.start()

    time.sleep(K)
    t_send_link = RepeatingTimer(K, send_link)
    t_send_link.start()

    time.sleep(Timeout-K)
    t_check_dead = RepeatingTimer(Timeout, check_dead)
    t_check_dead.start()


if __name__ == "__main__":
    main()
