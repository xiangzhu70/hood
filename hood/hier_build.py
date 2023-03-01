#!/usr/bin/env python3

import re
import os
import argparse

from pdb import set_trace as stop


class HierNode:

    def __init__(self, name):
        m = re.match(r"(?P<node_name>[^\[^ ]+)(?P<range_str>\[\S+\])?", name)
        if not m:
            raise Exception(f"invalid node name {name}")
        self.node_name = m.group("node_name")
        range_str = m.group("range_str")
        self.range_str = range_str if range_str else ""
        self.sub_nodes = []
        self.checks_list = []
        self.commands_list = []
        self.parent_node = None

    def add_sub_node(self, node):
        self.sub_nodes.append(node)
        node.node_path = f"{self.node_path}.{node.node_name}{node.range_str}"
        node.os_path = f"{self.os_path}/{node.node_name}"
        node.parent_node = self
        # create directory here, to allow adding cmds and checks
        # the node_diag file will be created later after having subs[]
        os.makedirs(node.os_path, exist_ok=True)

    def underscrore_to_camel(node_name):
        fragments = node_name.split("_")
        fragments_upper = [(frag[0]).upper() + frag[1:] for frag in fragments]
        joined = "".join(fragments_upper)
        return joined

    def create_node_file(self):
        node_file = f"{self.os_path}/node_diag.py"
        class_name = HierNode.underscrore_to_camel(self.node_name)
        if not os.path.exists(node_file):
            with open(node_file, "w") as f:
                f.write("from hood.diag_node import NodeDiag\n\n")
                f.write(f"class Node{class_name}(NodeDiag):\n\n")
                f.write(f"    def init(self):\n")
                subs_line = "        self.subs = ["
                for sub in self.sub_nodes:
                    subs_line += f"\"{sub.node_name}{sub.range_str}\", "
                subs_line += "]"
                f.write(f"{subs_line}\n")

    def sub_nodes_list_check(self):
        # TBD
        return True

    def end_setup(self):
        if self.node_name == "top":
            stop()
        print(f"end setup, node {self.node_name}")
        self.create_node_file()
        ret = self.sub_nodes_list_check()
        if not ret:
            print("sub_nodes list checking failed")
            return

    def add_check(self, check):
        self.checks_list.append(check)
        class_name = HierNode.underscrore_to_camel(check)
        file_name = f"{self.os_path}/checks.py"

        found = False
        if not os.path.exists(file_name):
            with open(file_name, "w") as f:
                f.write("from hood.diag_check import Check\n\n")
        else:
            with open(file_name, "r") as f:
                for line in f:
                    if f"class Check{class_name}" in line:
                        found = True

        if not found:
            with open(file_name, "a") as f:
                f.write(f"\nclass Check{class_name}(Check):\n\n")
                f.write(f"    def run(self, cmd_args=None):\n")
                f.write(f"        pass\n")

    def add_command(self, command):
        self.commands_list.append(command)
        class_name = HierNode.underscrore_to_camel(command)
        file_name = f"{self.os_path}/commands.py"

        found = False
        if not os.path.exists(file_name):
            with open(file_name, "w") as f:
                f.write("from hood.diag_cmd import Command\n\n")
        else:
            with open(file_name, "r") as f:
                for line in f:
                    if f"class Command{class_name}" in line:
                        found = True

        if not found:
            with open(file_name, "a") as f:
                f.write(f"\nclass Command{class_name}(Command):\n\n")
                f.write(f"    def run(self, cmd_args=None):\n")
                f.write(f"        pass\n")


class Hier:

    def __init__(self, conf_file, top_path):
        conf_f = open(conf_file, "r")
        self.conf_lines = conf_f.readlines()
        # add the ending empty line to bring level back to 0
        self.conf_lines.append("end")
        self.top_path = top_path
        self.num_conf_lines = len(self.conf_lines)
        conf_f.close()

    def build_hier(self):

        line_idx = 0

        top_node = HierNode("top")
        top_node.node_path = ":"
        top_node.os_path = self.top_path

        # The nodes start at level 1, with at least one "|--" ahead of it.
        level = 0

        node_curr = top_node
        prev_sibling_node = top_node

        # one pass to scan through the lines
        while line_idx < self.num_conf_lines:
            line = self.conf_lines[line_idx]

            if line.startswith("#"):
                line_idx += 1
                continue

            pattern = r"(?P<marks>(\|\-\-)*)(\[(?P<entry_type>\S+)\])?(?P<entry_name>\S+)?"
            m = re.match(pattern, line)
            line_idx += 1

            if not m:
                raise Exception(f"line {line_idx} <{line} invalid")

            len_marks = len(m.group("marks"))
            if (len_marks % 3):
                raise Exception("invalid format, should be multiple of 3")

            entry_type = m.group("entry_type")
            entry_name = m.group("entry_name")
            if entry_type:
                if len_marks != 3 * (level + 1):
                    print(f"line is <{line}>")
                    print(
                        f"line {line_idx}: entry_type {entry_type}, entry_name {entry_name}, len_marks {len_marks}, level {level}")
                    raise Exception(
                        f"At level {level } there should be {level+1} indent marks, found {len_marks}")
                if entry_type == "chk" or entry_type == "check":
                    if entry_name == None:
                        entry_name = "over_all"
                    prev_sibling_node.add_check(entry_name)
                elif entry_type == "cmd":
                    prev_sibling_node.add_command(entry_name)
                continue

            # the entry is a node
            node_name = entry_name
            try:
                node = HierNode(node_name)
            except Exception as e:
                print(f"line {line_idx}, failed to init node {node_name}")
                print(e)
                exit(-1)

            if len_marks == 3 * level:
                node_curr.add_sub_node(node)
                prev_sibling_node.end_setup()
                prev_sibling_node = node
            elif len_marks == 3 * (level + 1):
                if not prev_sibling_node:
                    print("invalid format")
                    return False
                node_curr = prev_sibling_node
                level += 1
                print(f"down to level {level}, curr {node_curr.node_name}")
                node_curr.add_sub_node(node)
                prev_sibling_node = node
            elif len_marks < 3 * level:
                new_level = int(len_marks / 3)
                print(f"-- new_level {new_level}, < level {level}")
                while level > new_level:
                    print(f"-- level {level}, curr {node_curr.node_name}")
                    if not node_curr:
                        raise Exception("Invalid node")
                    prev_sibling_node.end_setup()
                    if not node_curr.parent_node:
                        break  # reached top.
                    node_curr = node_curr.parent_node
                    if len(node_curr.sub_nodes) < 1:
                        stop()
                    prev_sibling_node = node_curr.sub_nodes[-1]
                    level -= 1
                    print(
                        f"up to level {level}, node_curr {node_curr.node_name}")
                if node.node_name != "end":
                    prev_sibling_node.end_setup()
                    node_curr.add_sub_node(node)
                    prev_sibling_node = node

        top_node.sub_nodes[0].create_node_file()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Diag hierarchy builder")
    parser.add_argument("hier_conf")
    parser.add_argument("top_dir")

    args = parser.parse_args()
    top_dir = os.path.expanduser(args.top_dir)
    hier_conf = args.hier_conf
    os.makedirs(top_dir, exist_ok=True)
    hier = Hier(hier_conf, top_dir)
    hier.build_hier()
