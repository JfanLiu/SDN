#!/usr/bin/env python

"""This is the Controller Starter Code for ECE50863 Lab Project 1
Author: Xin Du
Email: du201@purdue.edu
Last Modified Date: December 9th, 2021
"""

import sys
from datetime import date, datetime
import socket

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
            link[0] = int(link[0])
            link[1] = int(link[1])
            link[2] = int(link[2])
            # alive = True
            link.append(True)
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
        msg = msg.decode()
        print("msg: ", msg)

        # Parse the message
        msg = msg.split()
        if msg[0] == "register_request":
            req_id = msg[1]
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

    def get_links(switch_id):
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

    for switch_id in switch_addrs:
        msg = "register_response\n"
        neighbors = get_neighbors(switch_id)

        msg += str(len(neighbors)) + "\n"
        for neighbor in neighbors:
            msg += str(neighbor) + " " + \
                str(switch_addrs[neighbor][0]) + " " + \
                str(switch_addrs[neighbor][1]) + "\n"

        print("msg: \n", msg)
        ctrl_socket.sendto(msg.encode(), switch_addrs[switch_id])
        register_response_sent(switch_id)

    # Path computation using Dijkstra's algorithm
    def compute_path(src):
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
            neighbor_links = get_links(current["id"])

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
        return visited

    routing_table = []
    for switch_id in switch_ids:
        path = compute_path(switch_id)
        for s_id in switch_ids:
            routing_table.append(
                [switch_id, s_id, path[s_id]["hop"], path[s_id]["distance"]])

    print("routing_table: ", routing_table)

    routing_table_update(routing_table)

    # Sending routing table to all switches
    for switch_id in switch_ids:
        msg = "routing_table_update\n"
        msg += str(len(routing_table)) + "\n"
        for entry in routing_table:
            msg += str(entry[0]) + " " + str(entry[1]) + " " + \
                str(entry[2]) + " " + str(entry[3]) + "\n"

        ctrl_socket.sendto(msg.encode(), switch_addrs[switch_id])


if __name__ == "__main__":
    main()
