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
            for i in range(2, len(msg)):
                link = msg[i].split()
                if len(link) != 3:
                    break
                end_id = int(link[0])
                addr1 = link[1]  # hostname
                addr2 = int(link[2])  # port

                edge_table[end_id] = {
                    "state": True,
                    "next_hop": -1,
                    "addr": (addr1, addr2),
                    "refresh": False
                }
            # add 自己到自己
            edge_table[my_id] = {
                "state": True,
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
    lock_k = threading.Lock() #第k秒，接收keep alive的优先级比向ctrl发送table的优先级高

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
        # 向活邻居发alive
        msg = "KEEP_ALIVE\n{0}\n".format(my_id)
        for end_id in edge_table:
            if end_id == my_id:
                continue
            addr = edge_table[end_id]["addr"]
            lock.release()
            switch_socket.sendto(msg.encode(), addr)
            prompt(msg, "send keep alive to "+str(end_id))
            lock.acquire()
        lock.release()

    def send_link():
      # 向控制器发送自己的邻居死活情况
        lock_k.acquire()
        lock.acquire()
        msg = "routing_table_update\n"
        msg += str(my_id)+'\n'
        for end_id in edge_table:
            if end_id == my_id:
                continue
            msg += "{0} {1}\n".format(end_id, edge_table[end_id]["state"])
        lock.release()
        switch_socket.sendto(msg.encode(), host_addr)
        prompt(msg, "send route table to ctrl")
        lock_k.release()

    def refresh_edge_table(msg=None, is_init=False, end_id=None, flag=None):
      # 传入 对\n split后的msg
        lock.acquire()
        if msg != None:  # 根据msg进行更新
            if msg[0] == 'routing_table_update':
                start_id = int(msg[1])
                if start_id != my_id:
                    exit(-1)

                edge_table_temp = edge_table

                # 若不是初始化
                if not is_init:
                    for end_id in edge_table:
                        edge_table[end_id]["state"] = False

                for i in range(2, len(msg)):
                    link = msg[i].split()
                    if len(link) != 2:
                        break
                    end_id = int(link[0])
                    next_hop = int(link[1])
                    edge_table[end_id]["next_hop"] = next_hop
                    edge_table[end_id]["state"] = True
                    if end_id not in edge_table_temp:
                        edge_table[end_id]["refresh"] = False

                if not is_init:
                    # 若不是初始化，如果table无变动，不需要log
                    if operator.eq(edge_table_temp, edge_table):
                        lock.release()
                        return
        else:  # 根据state=flag进行更新
            edge_table[end_id]["refresh"] = True  # 刷新
            if edge_table[end_id]["state"] == flag:  # 若state不变，则退出,不log
                lock.release()
                return
            edge_table[end_id]["state"] = flag

        if not is_init:  # 如果不是初始化，既要log也要将更新的路由表发送给控制器
            lock.release()
            send_link()
            lock.acquire()

        # log
        routing_table = make_routing_table_update(edge_table, my_id)
        print("log routing_table:\n", routing_table)
        routing_table_update(routing_table)
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

    def rec_infor():
        while True:
            lock_k.acquire()
            # 接收来自邻居交换机的活信息与来自控制器的路由更新表
            msg, switch_addr = switch_socket.recvfrom(1024)
            lock_k.release()
            msg = msg.decode()
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
        lock.acquire()
        for end_id in edge_table:
            # 若未刷新，则置死
            if edge_table[end_id]["state"] == True and edge_table[end_id]["refresh"] != True:
                lock.release()
                refresh_edge_table(msg=None, is_init=None,
                                   end_id=end_id, flag=False)
                lock.acquire()
            edge_table[end_id]["refresh"] = False
        lock.release()

    # 定时进程
    class RepeatingTimer(threading.Timer):
        def run(self):
            while not self.finished.is_set():
                self.function(*self.args, **self.kwargs)
                self.finished.wait(self.interval)

    t_send_alive = RepeatingTimer(K, send_alive)
    t_send_alive.start()
    # t_send_alive.cancel() #when to kill this thread?

    t_send_link = RepeatingTimer(K, send_link)
    t_send_link.start()

    t_rec_infor = threading.Thread(target=rec_infor)
    t_rec_infor.start()

    t_check_dead = RepeatingTimer(Timeout, check_dead)
    t_check_dead.start()


if __name__ == "__main__":
    main()
