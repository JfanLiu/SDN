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
    K = 0  # period

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
    my_addr = (ctrl_hostname, ctrl_port)
    switch_socket.connect(my_addr)

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
                "addr": my_addr,
                "refresh": False
            }
        register_response_received()

    udp_register_request_sent()
    udp_register_response_received()

    def make_routing_table_update(edge_table, my_id):
        # <Switch ID>,<Dest ID>:<Next Hop>
        routing_table = []
        for end_id in edge_table:
            routing_table.append([
                my_id,
                end_id,
                edge_table[end_id]["next_hop"]
            ])
        routing_table.sort(key=lambda x: (x[0], x[1]))
        return routing_table

    def udp_routing_table_update_received():
        msg, _ = switch_socket.recvfrom(1024)
        msg = msg.decode()
        prompt(msg, "recv ")
        # Parse the message
        msg = msg.split('\n')
        if msg[0] == 'routing_table_update':

            start_id = int(msg[1])
            if start_id != my_id:
                exit(-1)

            for i in range(2, len(msg)):
                link = msg[i].split()
                if len(link) != 2:
                    break
                end_id = int(link[0])
                next_hop = int(link[1])

                edge_table[end_id]["next_hop"] = next_hop
                edge_table[end_id]["refresh"] = True

        routing_table = make_routing_table_update(edge_table, my_id)
        print("routing_table:\n", routing_table)
        routing_table_update(routing_table)

    udp_routing_table_update_received()
    return

    # Timer 在执行操作的时候会创建一个新的线程

    def send_alive():
        msg = "KEEP_ALIVE "+str(my_id)+'\n'

    # 定时进程
    class RepeatingTimer(threading.Timer):
        def run(self):
            while not self.finished.is_set():
                self.function(*self.args, **self.kwargs)
                self.finished.wait(self.interval)

    t_send_alive = RepeatingTimer(K, send_alive)
    t_send_alive.start()
    # t_send_alive.cancel() #when to kill this thread?


if __name__ == "__main__":
    main()
