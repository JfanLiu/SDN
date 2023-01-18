#!/usr/bin/env python

"""This is the Controller Starter Code for ECE50863 Lab Project 1
Author: Xin Du
Email: du201@purdue.edu
Last Modified Date: December 9th, 2021
"""

import sys
from datetime import date, datetime
import socket
import threading

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


def main():
    # Check for number of arguments and exit if host/port not provided
    num_args = len(sys.argv)
    if num_args < 3:
        print("Usage: python controller.py <port> <config file>\n")
        sys.exit(1)

    # Write your code below or elsewhere in this file
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
                    elif type(item) is bool:
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

    port = sys.argv[1]
    num_links = 0
    links = []
    switch_ids = []
    # Parse the config file
    with open(sys.argv[2], 'r') as config_file:
        config = config_file.readlines()
        num_links = int(config[0].strip())
        for i in range(1, num_links + 1):
            link = config[i].strip().split()
            link.append(True)
            link = [int(i) for i in link]
            # alive = True
            links.append(link)

    for link in links:
        if link[0] not in switch_ids:
            switch_ids.append(link[0])
        if link[1] not in switch_ids:
            switch_ids.append(link[1])
    switch_ids.sort()

    print("port: ", port)
    print("switch_ids: ", switch_ids)
    print("num_links: ", num_links)
    print("links: ", links)

    ctrl_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ctrl_addr = ('', int(port))

    ctrl_socket.bind(ctrl_addr)

    switch_addrs = {}
    switch_count = 0

    # Loop for waiting for all switches to register
    # Once all switches have registered, send register_response to all switches
    while True:
        msg, switch_addr = ctrl_socket.recvfrom(1024)
        msg = Message().from_str(msg.decode())
        msg.print()

        # Parse the message
        if msg.get_type() == "register_request":
            req_id = msg.get_objects()[0][0]
            switch_addrs[int(req_id)] = switch_addr
            switch_count += 1
            register_request_received(req_id)
        else:
            print("Unknown message type")
            sys.exit(1)

        if switch_count == len(switch_ids):
            break

    def get_neighbors(switch_id):
        neighbors = []
        for link in links:
            if switch_id == link[0]:
                neighbors.append(link[1])
            elif switch_id == link[1]:
                neighbors.append(link[0])
            else:
                continue
        neighbors = list(set(neighbors))
        return neighbors

    def get_links(switch_id, links):
        switch_links = []
        for link in links:
            if switch_id == link[0]:
                switch_links.append(link)
            elif switch_id == link[1]:
                switch_links.append(link)
            else:
                continue
        return switch_links

    def get_otherside(switch_id, link):
        if switch_id == link[0]:
            return link[1]
        elif switch_id == link[1]:
            return link[0]
        else:
            return None

    def udp_register_response_sent(switch_id):
        msg = Message()
        msg.set_type("register_response")
        neighbors = get_neighbors(switch_id)

        for neighbor in neighbors:
            msg.add_object([neighbor, switch_addrs[neighbor]
                            [0], switch_addrs[neighbor][1]])

        ctrl_socket.sendto(bytes(msg), switch_addrs[switch_id])
        register_response_sent(switch_id)

    for switch_id in switch_addrs:
        udp_register_response_sent(switch_id)

    # Path computation using Dijkstra's algorithm
    def compute_path(src, switch_ids, links):
        visited = {}
        unvisited = {}

        for switch_id in switch_ids:
            if switch_id != src:
                unvisited[switch_id] = {
                    "id": switch_id,
                    "distance": 9999,
                    "hop": -1
                }
            else:
                unvisited[switch_id] = {
                    "id": switch_id,
                    "distance": 0,
                    "hop": switch_id
                }
        # Loop for finding the shortest path
        while len(unvisited) > 0:
            current_id = list(unvisited.keys())[0]
            for switch_id in unvisited:
                if unvisited[switch_id]["distance"] < unvisited[current_id]["distance"]:
                    current_id = switch_id

            current = unvisited.pop(current_id)
            neighbor_links = get_links(current["id"], links)

            for link in neighbor_links:
                next = get_otherside(current_id, link)
                if visited.get(next) is not None:
                    continue
                new_distance = current["distance"] + link[2]
                if new_distance < unvisited[next]["distance"]:
                    unvisited[next]["distance"] = new_distance
                    unvisited[next]["hop"] = current_id

            visited[current_id] = current
            if len(unvisited) == 0:
                break

        # next_hop此时记录的是链路上的倒数第2个结点，需要回溯，使其记录链路上的第2个结点
        visited_temp = visited

        for end_id in visited:

            if end_id == src:  # 结点本身是链路上第1个结点
                continue  # 初始化时处理过了
            elif visited[end_id]["hop"] == -1:
                continue  # 始终不可达则不回溯

            while True:  # 循环回溯
                last = visited_temp[end_id]["hop"]
                if last == src:  # 结点本身是链路上第2个结点
                    visited_temp[end_id]["hop"] = end_id
                    break
                if visited[last]["hop"] == src:  # 结点本身是链路上第3个结点
                    break
                visited_temp[end_id]["hop"] = visited[last]["hop"]

        return visited_temp

    def udp_routing_table_update(switch_ids, links):
        routing_table = []
        for switch_id in switch_ids:
            path = compute_path(switch_id, switch_ids, links)
            for next_id in switch_ids:
                routing_table.append(
                    [switch_id, next_id, path[next_id]["hop"], path[next_id]["distance"]])

        routing_table_update(routing_table)

        # Sending routing table to all switches
        for switch_id in switch_ids:
            msg = Message()
            msg.set_type("routing_table_update")
            for entry in routing_table:
                msg.add_object(entry)

            ctrl_socket.sendto(bytes(msg), switch_addrs[switch_id])

    udp_routing_table_update(switch_ids, links)

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
    info_dist["topology_update"] = {}
    info_dist["keep_alive"] = {}
    info_dist["link"] = {}
    for id in switch_ids:
        info_dist["topology_update"][id] = 1
        info_dist["keep_alive"][id] = 1
    for link in links:
        if info_dist["link"].get(link[0]) is None:
            info_dist["link"][link[0]] = {}
        if info_dist["link"].get(link[1]) is None:
            info_dist["link"][link[1]] = {}
        info_dist["link"][int(link[0])][int(link[1])] = 1
        info_dist["link"][int(link[1])][int(link[0])] = 1
    info_dist_lock = threading.Lock()
    # Lock for other resources
    origin_lock = threading.Lock()

    def udp_topologychange_detected():
        origin_lock.acquire()
        info_dist_lock.acquire()

        new_links = []

        def exist_link(link):
            for l in new_links:
                if link[0] == l[0] and link[1] == l[1]:
                    return True
                elif link[0] == l[1] and link[1] == l[0]:
                    return True
            return False

        def node_alive(link):
            if info_dist["keep_alive"][link[0]] and info_dist["keep_alive"][link[1]]:
                return True
            else:
                return False

        def get_distance(link):
            for link in links:
                if link[0] == link[0] and link[1] == link[1]:
                    return link[2]
                elif link[0] == link[1] and link[1] == link[0]:
                    return link[2]
            return 9999

        for n1 in info_dist["link"]:
            for n2 in info_dist["link"][n1]:
                if info_dist["link"][n1][n2] == 1:
                    if not exist_link([n1, n2]):
                        if node_alive([n1, n2]):
                            new_links.append([n1, n2, get_distance([n1, n2])])

        udp_routing_table_update(switch_ids, new_links)

        info_dist_lock.release()
        origin_lock.release()

    def udp_topologyupdate_timeout():
        info_dist_lock.acquire()
        for id in info_dist["keep_alive"]:
            if info_dist["topology_update"][id]:
                info_dist["topology_update"][id] = 0
            else:
                info_dist["keep_alive"][id] = 0
                # Topology changed
                create_thread(udp_topologychange_detected, [])
        info_dist_lock.release()

        create_timer(udp_topologyupdate_timeout, [], TIMEOUT)

    def udp_message_received():
        while True:
            msg, addr = ctrl_socket.recvfrom(1024)
            msg = Message().from_str(msg.decode())
            msg.print()
            info_dist_lock.acquire()

            if msg.get_type() == "topology_update":
                switch_id = msg.get_objects()[0][0]
                info_dist["topology_update"][switch_id] = 1

                for [id, reachable] in msg.get_objects()[1:]:
                    old_reachable = info_dist["link"][switch_id][id]
                    if reachable != old_reachable:
                        info_dist["link"][switch_id][id] = reachable
                        info_dist["link"][id][switch_id] = reachable
                        # Topology changed
                        create_thread(udp_topologychange_detected, [])
            elif msg.get_type() == "register_request":
                req_id = msg.get_objects()[0][0]

                if not info_dist["keep_alive"][req_id]:
                    info_dist["keep_alive"][req_id] = 1
                    info_dist["topology_update"][req_id] = 1
                    switch_addrs[req_id] = addr
                    # Topology changed
                    create_thread(udp_topologychange_detected, [])

            info_dist_lock.release()

    create_thread(udp_topologyupdate_timeout, [])
    udp_message_received()


if __name__ == "__main__":
    main()
