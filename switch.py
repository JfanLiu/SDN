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


def main():

    global LOG_FILE

    # Check for number of arguments and exit if host/port not provided
    num_args = len(sys.argv)
    if num_args < 4:
        print(
            "switch.py <Id_self> <Controller hostname> <Controller Port> -f <Neighbor ID>\n")
        sys.exit(1)

    my_id = int(sys.argv[1])
    LOG_FILE = 'switch' + str(my_id) + ".log"

    # Write your code below or elsewhere in this file
    ctrl_hostname = sys.argv[2]
    ctrl_port = int(sys.argv[3])

    # Support multiple -f arguments
    f_neighbors = []
    for i in range(4, num_args):
        if sys.argv[i] == '-f':
            f_neighbors.append(int(sys.argv[i+1]))

    print("controller hostname: ", ctrl_hostname)
    print("controller port: ", ctrl_port)
    print("f_neighbors: ", f_neighbors)

    my_addr = ('', my_id)
    ctrl_addr = (ctrl_hostname, ctrl_port)
    switch_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    class Message:
        def __init__(self):
            self.type = 'unknown'
            self.objs = []

        def set_type(self, type: str):
            self.type = type

        def add_object(self, obj):
            self.objs.append(obj)

        def get_type(self):
            return self.type

        def get_objects(self):
            return self.objs

        def from_str(self, text: str):
            lines = text.strip().splitlines()
            self.type = lines[0]
            for line in lines[1:]:
                if line == "":
                    continue
                arr = line.strip().split()
                items = []
                for item in arr:
                    if item.isdigit():
                        items.append(int(item))
                    else:
                        items.append(item)
                self.objs.append(items)
            return self

        def __str__(self) -> str:
            text = self.type+"\n"
            for obj in self.objs:
                if type(obj) is list:
                    str_obj = [str(item) for item in obj]
                    text += " ".join(str_obj)
                else:
                    text += str(obj)
                text += "\n"
            return text

        def __bytes__(self) -> bytes:
            return self.__str__().encode()

        def print(self):
            print("msg:")
            print(self.__str__())

    def udp_register_request_sent():
        msg = Message()
        msg.set_type("register_request")
        msg.add_object(my_id)
        switch_socket.sendto(bytes(msg), ctrl_addr)
        register_request_sent()

    neighbors = {}

    def udp_register_response_received():
        msg, _ = switch_socket.recvfrom(1024)

        msg = Message().from_str(msg.decode())
        msg.print()

        if msg.get_type() != "register_response":
            return

        for obj in msg.get_objects():
            switch_id = obj[0]
            switch_addr = (obj[1], obj[2])
            neighbors[switch_id] = {"id": switch_id,
                                    "addr": switch_addr, "alive": True}

        register_response_received()

    udp_register_request_sent()
    udp_register_response_received()

    def udp_routing_table_update_received():
        msg, _ = switch_socket.recvfrom(1024)
        msg = Message().from_str(msg.decode())
        msg.print()
        # routing_table_update(msg.decode())

    udp_routing_table_update_received()

    # Periodically send keep alive messages to neighbors and update routing table
    K = 2
    TIMEOUT = 3*K

    def create_timer(func, args, interval):
        timer = threading.Timer(interval, func, args)
        timer.start()
        return timer

    def create_thread(func, args):
        thread = threading.Thread(target=func, args=args)
        thread.start()
        return thread

    info_dist = {}
    info_dist["keep_alive"] = {}
    for id in neighbors:
        info_dist["keep_alive"][id] = 1
    info_dist["neighbors"] = neighbors

    info_dist_lock = threading.Lock()

    # 1 Each switch sends a Keep Alive message every K seconds to each of the neighboring switches that it thinks is ‘alive’.
    def udp_keep_alive_sent():
        info_dist_lock.acquire()
        for id in info_dist["neighbors"]:
            if info_dist["neighbors"][id]["alive"] == 0:
                continue
            msg = Message()
            msg.set_type("keep_alive")
            msg.add_object(my_id)
            switch_socket.sendto(
                bytes(msg), info_dist["neighbors"][id]["addr"])
        info_dist_lock.release()

        create_timer(udp_keep_alive_sent, [], K)

    # 2 Each switch sends a Topology Update message to the controller every K seconds. The Topology Update message includes a set of ‘live’ neighbors of that switch.
    def make_topology_update():
        msg = Message()
        msg.set_type("topology_update")
        msg.add_object(my_id)

        for id in info_dist["neighbors"]:
            reachable = info_dist["neighbors"][id]["alive"]
            msg.add_object([id, reachable])

        return msg

    def udp_topology_update_sent():
        info_dist_lock.acquire()
        msg = make_topology_update()
        switch_socket.sendto(bytes(msg), ctrl_addr)
        info_dist_lock.release()

        create_timer(udp_topology_update_sent, [], K)

    def udp_keepalive_timeout():
        info_dist_lock.acquire()
        for id in neighbors:
            if info_dist["neighbors"][id]["alive"]:
                if info_dist["keep_alive"][id]:
                    info_dist["keep_alive"][id] = 0
                else:
                    # Equivalent to a link failure.
                    # Send a topology update to the controller.
                    info_dist["neighbors"][id]["alive"] = False
                    msg = make_topology_update()
                    switch_socket.sendto(bytes(msg), ctrl_addr)
        info_dist_lock.release()

        create_timer(udp_keepalive_timeout, [], TIMEOUT)

    # 3
    def udp_message_received():
        while True:
            msg, addr = switch_socket.recvfrom(1024)
            msg = Message().from_str(msg.decode())
            msg.print()
            info_dist_lock.acquire()

            if msg.get_type() == "keep_alive":
                id = msg.get_objects()[0][0]

                info_dist["keep_alive"][id] = 1
                if not info_dist["neighbors"][id]["alive"]:
                    info_dist["neighbors"][id]["alive"] = True
                    # update neighbor address
                    info_dist["neighbors"][id]["addr"] = addr
                    msg = make_topology_update()
                    switch_socket.sendto(bytes(msg), ctrl_addr)
            elif msg.get_type() == "routing_table_update":
                # routing_table_update(msg.get_objects())
                pass
            info_dist_lock.release()

    udp_keep_alive_sent()
    create_thread(udp_topology_update_sent, [])
    create_timer(udp_keepalive_timeout, [], TIMEOUT)
    udp_message_received()


if __name__ == "__main__":
    main()
