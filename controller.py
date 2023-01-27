#!/usr/bin/env python

"""This is the Controller Starter Code for ECE50863 Lab Project 1
Author: Xin Du
Email: du201@purdue.edu
Last Modified Date: December 9th, 2021
"""

import json
import sys
from datetime import date, datetime
import socket
import threading
import operator
import time

# Please do not modify the name of the log file, otherwise you will lose points because the grader won't be able to find your log file
LOG_FILE = "Controller.log"

# Those are logging functions to help you follow the correct logging standard

# "Register Request" Format is below:
#
# Timestamp
# Register Request <Switch-ID>


def register_request_received(switch_id):
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append(f"Register Request {switch_id}\n")
    write_to_log(log)

# "Register Responses" Format is below (for every switch):
#
# Timestamp
# Register Response <Switch-ID>


def register_response_sent(switch_id):
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append(f"Register Response {switch_id}\n")
    write_to_log(log)

# For the parameter "routing_table", it should be a list of lists in the form of [[...], [...], ...].
# Within each list in the outermost list, the first element is <Switch ID>. The second is <Dest ID>, and the third is <Next Hop>, and the fourth is <Shortest distance>
# "Routing Update" Format is below:
#
# Timestamp
# Routing Update
# <Switch ID>,<Dest ID>:<Next Hop>,<Shortest distance>
# ...
# ...
# Routing Complete
#
# You should also include all of the Self routes in your routing_table argument -- e.g.,  Switch (ID = 4) should include the following entry:
# 4,4:4,0
# 0 indicates ‘zero‘ distance
#
# For switches that can’t be reached, the next hop and bandwidth should be ‘-1’ and ‘9999’ respectively. (9999 means infinite distance so that that switch can’t be reached)
#  E.g, If switch=4 cannot reach switch=5, the following should be printed
#  4,5:-1,9999
#
# For any switch that has been killed, do not include the routes that are going out from that switch.
# One example can be found in the sample log in starter code.
# After switch 1 is killed, the routing update from the controller does not have routes from switch 1 to other switches.


def routing_table_update(routing_table):
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append("Routing Update\n")
    for row in routing_table:
        log.append(f"{row[0]},{row[1]}:{row[2]},{row[3]}\n")
    log.append("Routing Complete\n")
    write_to_log(log)

# "Topology Update: Link Dead" Format is below: (Note: We do not require you to print out Link Alive log in this project)
#
#  Timestamp
#  Link Dead <Switch ID 1>,<Switch ID 2>


def topology_update_link_dead(switch_id_1, switch_id_2):
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append(f"Link Dead {switch_id_1},{switch_id_2}\n")
    write_to_log(log)

# "Topology Update: Switch Dead" Format is below:
#
#  Timestamp
#  Switch Dead <Switch ID>


def topology_update_switch_dead(switch_id):
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append(f"Switch Dead {switch_id}\n")
    write_to_log(log)

# "Topology Update: Switch Alive" Format is below:
#
#  Timestamp
#  Switch Alive <Switch ID>


def topology_update_switch_alive(switch_id):
    log = []
    log.append(str(datetime.time(datetime.now())) + "\n")
    log.append(f"Switch Alive {switch_id}\n")
    write_to_log(log)


def write_to_log(log):
    with open(LOG_FILE, 'a+') as log_file:
        log_file.write("\n\n")
        # Write to log
        log_file.writelines(log)


def prompt(msg, msg_name):
    print(msg_name+"\n"+msg)


def pretty(d):
    print(json.dumps(d, indent=4, ensure_ascii=False))


def main():
    # Check for number of arguments and exit if host/port not provided
    num_args = len(sys.argv)
    if num_args < 3:
        print("Usage: python controller.py <port> <config file>\n")
        sys.exit(1)

    port = int(sys.argv[1])
    num_switch = 0  # the num of switch
    switch_table = {}
    K = 2  # period
    Timeout = K*3

    # Parse the config file
    with open(sys.argv[2], 'r') as config_file:
        config = config_file.readlines()
        num_switch = int(config[0].strip())
        for i in range(1, len(config)):
            link = config[i].strip().split()
            if len(link) != 3:
                continue
            start_id = int(link[0])
            end_id = int(link[1])
            dis = int(link[2])
            # 无向边 存储两份，空间换时间

            # init vertice
            if start_id not in switch_table:
                switch_table[start_id] = {
                    "edge": {},
                    "state": True,
                    "addr": "",
                    "refresh": False
                }
            if end_id not in switch_table:
                switch_table[end_id] = {
                    "edge": {},
                    "state": True,
                    "addr": "",
                    "refresh": False
                }

            # add edge
            switch_table[start_id]["edge"][end_id] = {
                "dis": dis,
                "next_hop": -1,
                "state": True
            }
            switch_table[end_id]["edge"][start_id] = {
                "dis": dis,
                "next_hop": -1,
                "state": True
            }

    print("port: ", port)
    pretty(switch_table)
    print("num_switch: ", num_switch)

    ctrl_socket = socket.socket(
        socket.AF_INET, socket.SOCK_DGRAM)  # IPv4,for UDP
    # bind as server
    ctrl_socket.bind(('', port))

    switch_count = 0
    
    ls_id=[]

    # Loop for waiting for all switches to register
    # Once all switches have registered, send register_response to all switches
    while True:
        msg, switch_addr = ctrl_socket.recvfrom(1024)
        msg = msg.decode()
        prompt(msg, "recv")

        # Parse the message
        msg = msg.split()
        if msg[0] == "register_request":
            req_id = int(msg[1])
            switch_table[req_id]["addr"] = switch_addr
            ls_id.append(req_id)
            # print(switch_addr)
            switch_count += 1
            register_request_received(req_id)
        else:
            print("Unknown message type")
            sys.exit(1)

        if switch_count == num_switch:
            break

    # register response
    # 广播switch的所有出边与对应地址
    for switch_id in ls_id:
        msg = "register_response\n"
        msg += str(len(switch_table[switch_id]["edge"]))+"\n"
        for end_id in switch_table[switch_id]["edge"]:
            msg += "{0} {1} {2}\n".format(end_id,
                                          switch_table[end_id]["addr"][0],
                                          switch_table[end_id]["addr"][1])
        prompt(msg, "send")
        ctrl_socket.sendto(msg.encode(), switch_table[switch_id]["addr"])
        register_response_sent(switch_id)

    # 至此，并发加锁
    lock = threading.Lock()

    # Path computation using Dijkstra's algorithm
    def compute_path(src):
        visited = {}
        unvisited = {}

        # init
        for switch_id in switch_table:
            if not switch_table[switch_id]["state"]:
                continue  # 若已死，则不入网
            if switch_id != src:
                unvisited[switch_id] = {
                    "dis": 9999,
                    "next_hop": -1
                }
            else:
                unvisited[switch_id] = {
                    "dis": 0,
                    "next_hop": switch_id
                }

        # Loop for finding the shortest path
        while len(unvisited) > 0:

            # 从unvisited表找到当前路径最短的节点
            current_id = list(unvisited.keys())[0]
            for switch_id in unvisited:
                if unvisited[switch_id]["dis"] < unvisited[current_id]["dis"]:
                    current_id = switch_id

            # 从unvisited表弹出这个节点，放入visit表
            current = unvisited.pop(current_id)
            visited[current_id] = current

            # 从current_id出发，更新unvisited表中其出边的最短距离
            for end_id in switch_table[current_id]["edge"]:
                if not switch_table[end_id]["state"]:
                    continue  # 若已死，则不入网
                if end_id in visited:  # 若出点已visit，则不更新
                    continue
                new_distance = current["dis"] + switch_table[current_id]["edge"][end_id]["dis"]
                if new_distance < unvisited[end_id]["dis"]:
                    unvisited[end_id]["dis"] = new_distance
                    unvisited[end_id]["next_hop"] = current_id

        # next_hop此时记录的是链路上的倒数第2个结点，需要回溯，使其记录链路上的第2个结点
        visited_temp = visited

        for end_id in visited:

            if end_id == src:  # 结点本身是链路上第1个结点
                continue  # 初始化时处理过了
            elif visited[end_id]["next_hop"] == -1:
                continue  # 始终不可达则不回溯

            while True:  # 循环回溯
                last = visited_temp[end_id]["next_hop"]
                if last == src:  # 结点本身是链路上第2个结点
                    visited_temp[end_id]["next_hop"] = end_id
                    break
                if visited[last]["next_hop"] == last:  # 结点本身是链路上第3个结点
                    break
                visited_temp[end_id]["next_hop"] = visited[last]["next_hop"]

        return visited_temp

    def udp_routing_table_update_sent():
        # 读取table，make 路由表，按序广播，log

        # cal the shortest path and make routing_table
        routing_table = []
        for switch_id in switch_table:
            if not switch_table[switch_id]["state"]:  # 死了就不作起点
                continue
            path = compute_path(switch_id)
            for s_id in switch_table:
                # 死了可以做出点
                if not switch_table[s_id]["state"]:
                    routing_table.append(
                        [switch_id, s_id, -1, 9999])
                else:
                    routing_table.append(
                        [switch_id, s_id, path[s_id]["next_hop"], path[s_id]["dis"]])

        routing_table.sort(key=lambda x: (x[0], x[1]))
        print("routing_table: ", routing_table)

        # Sending routing table to all switches
        for switch_id in switch_table:
            if not switch_table[switch_id]["state"]:  # 死了就不送
                continue
            msg = "routing_table_update\n"
            msg += str(switch_id) + "\n"
            for edge in routing_table:
                if edge[0] == switch_id:
                    msg += "{0} {1}\n".format(edge[1], edge[2])
            prompt(msg, "send route table")
            addr = switch_table[switch_id]["addr"]
  
            ctrl_socket.sendto(msg.encode(), addr)
  
        # log
        routing_table_update(routing_table)


    udp_routing_table_update_sent()

    def refresh_switch_table(msg=None, id=None, flag=None):
        if msg != None:
            if msg[0] == 'routing_table_update':
                start_id = int(msg[1])

                switch_table[start_id]["refresh"] = True

                switch_table_temp = switch_table

                for end_id in switch_table[start_id]["edge"]:
                    switch_table[start_id]["edge"][end_id]["state"] = False

                for i in range(2, len(msg)):
                    link = msg[i].split()
                    if len(link) != 2:
                        break
                    end_id = int(link[0])
                    state = link[1] == True

                    switch_table[start_id]["edge"][end_id]["state"] = state

                if operator.eq(switch_table, switch_table_temp):
                    return
        else:
            if switch_table[id]["state"] == flag:
                return
            switch_table[id]["state"] = flag

        # table有变，刷新，广播，log
        udp_routing_table_update_sent()

    def rec_infor():
        while True:
            # 接收来自邻居交换机的活信息与来自控制器的路由更新表
            msg, switch_addr = ctrl_socket.recvfrom(1024)
            msg = msg.decode()
            msg_tmep = msg
            msg = msg.split('\n')
            
            lock.acquire()
            
            # 可以通过发送地址或信息头来确定信息类别
            if msg[0] == 'routing_table_update':
                prompt(msg_tmep, str(switch_addr)+"rev route update from "+msg[1])
                refresh_switch_table(msg)
            elif msg[0] == "register_request":
                req_id = int(msg[1])
                prompt(msg_tmep, "rev register request from "+req_id)
                refresh_switch_table(None, req_id, True)
                
            lock.release()

    def check_dead():

        lock.acquire()

        # 检测是否所有活邻居都alive刷新了
        for start_id in switch_table:
            # 若未刷新，则置死
            if switch_table[start_id]["state"] == True and switch_table[start_id]["refresh"] != True:
                print("#{0} switch dead".format(start_id))
                refresh_switch_table(None, start_id, False)#will log
                
            switch_table[start_id]["refresh"] = False

        lock.release()

    # 定时进程
    class RepeatingTimer(threading.Timer):
        def run(self):
            while not self.finished.is_set():
                self.function(*self.args, **self.kwargs)
                self.finished.wait(self.interval)
                
    t_rec_infor = threading.Thread(target=rec_infor)
    t_rec_infor.start()
    
    time.sleep(Timeout)
    t_check_dead = RepeatingTimer(Timeout, check_dead)
    t_check_dead.start()

if __name__ == "__main__":
    main()
