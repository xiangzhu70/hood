#!/usr/bin/env python3

# Build the hierarchy code from a hierachy map text file
import re
import os
import argparse

from pdb import set_trace as stop

# util functions
def underscrore_to_camel(node_name):
    fragments = node_name.split("_")
    fragments_upper = [(frag[0]).upper() + frag[1:] for frag in fragments]
    joined = "".join(fragments_upper)
    return joined

class Entry:

    def __init__(self, type, name, parent, line_num, line):
        self.type = type
        self.name = name
        self.parent = parent # parent entry at higher level
        self.children = []
        self.line_num = line_num
        self.line = line
        if parent:
            parent.children.append(self)

class Prop:
    def __init__(self, entry, node):
        self.entry = entry
        self.node = node
        m = re.match(r"(?P<name>[^\[^ ]+)(?P<range_str>\[[^\]]*\])?", entry.name)
        if not m:
            raise Exception(f"invalid prop name {entry.name}")
        self.name = m.group("name")
        range_str = m.group("range_str")
        if "ip_address" in entry.line:
            print(entry.line)
        self.range_str = range_str if range_str else ""

    def write_class_to_file(self, f):
        class_name = underscrore_to_camel(self.name)
        f.write(f"\nclass Property{class_name}(Property):\n")
        f.write(" "*4 + f"pass\n")

class Command:
    def __init__(self, entry, node):
        self.entry = entry
        self.node = node
        self.name = entry.name

    def write_class_to_file(self, f):
        class_name = underscrore_to_camel(self.name)
        f.write(f"\nclass Command{class_name}(Command):\n\n")
        f.write(" "*4 + f"def run(self, cmd_args=None):\n")
        run_line = '{self.obj_path}: in run() function'
        f.write(" "*8 + f'self.log(f\"{run_line}\")\n')
        
class Check:
    def __init__(self, entry, node):
        self.entry = entry
        self.node = node
        self.name = entry.name
        self.pre_list = []
        self.dep_list = []
        self.proc = None
        for child_entry in entry.children:
            if child_entry.type == "pre":
                self.pre_list.append(child_entry.name)
            elif child_entry.type == "dep":
                self.dep_list.append(child_entry.name)
            elif child_entry.type == "proc":
                if self.proc:
                    ("Error: there can be only ONE proc for a check")
                    exit(-1)
                self.proc = Proc(child_entry, self)
            else:
                print(f"Error: check {self.name}. invalid entry {child_entry.type}")

    def write_class_to_file(self, f):
        class_name = underscrore_to_camel(self.name)
        f.write(f"\nclass Check{class_name}(Check):\n\n")

        num_pres = len(self.pre_list)
        num_deps = len(self.dep_list)

        if num_pres or num_deps or self.proc:
            f.write(" "*4 + "def init(self):\n")
            if num_pres:
                f.write(" "*8 + "self.pres = [\n")
                for pre in self.pre_list:
                    f.write(" "*12 + f'"{pre}",\n')
                f.write(" "*12 + "]\n")
            if num_deps:
                f.write(" "*8 + "self.deps = [\n")
                for dep in self.dep_list:
                    f.write(" "*12 + f'"{dep}",\n')
                f.write(" "*12 + "]\n")
            if self.proc:
                self.proc.write_construct_line(f, " "*8)
            f.write("\n")

        f.write(" "*4 + "def run(self, cmd_args=None):\n")
        run_line = '{self.obj_path}: in run() function'
        f.write(" "*8 + f'self.log(f\"{run_line}\")\n')
        f.write(" "*8 + 'return \"OK\"\n')

class Proc:
    def __init__(self, entry, check):
        self.entry = entry
        self.name = entry.name
        self.check = check # the parent check this proc is for
        self.init = None
        self.rept = None
        for child_entry in entry.children:
            if child_entry.type == "init":
                self.init = child_entry.name
            elif child_entry.type == "rept":
                self.rept = child_entry.name
            else:
                print(f"Error: proc {self.name}. invalid entry type {child_entry.type}")

    def write_construct_line(self, f, indent):
        args = f'"{self.init}"'
        if self.rept:
            args += f', rept="{self.rept}"'
        f.write(indent + f"self.proc = Proc({args})\n")

class HierNode:

    def __init__(self, entry, parent):
        print(f"entry {entry}, parent {parent}")
        if not entry:  # top empty node
            return

        m = re.match(r"(?P<node_name>[^\[^ ]+)(?P<range_str>\[\S+\])?", entry.name)
        if not m:
            raise Exception(f"invalid node name {entry.name}")
        self.node_name = m.group("node_name")
        range_str = m.group("range_str")
        self.range_str = range_str if range_str else ""

        self.sub_nodes = []
        self.checks_list = []
        self.commands_list = []
        self.props_list = []
        self.parent_node = parent

        node_path_parent_prefix = parent.node_path
        if node_path_parent_prefix != ":":
            node_path_parent_prefix += "."

        self.node_path = f"{node_path_parent_prefix}{self.node_name}{self.range_str}"
        self.os_path = f"{parent.os_path}/{self.node_name}"

        for child_entry in entry.children:
            if child_entry.type == "node":
                self.sub_nodes.append(HierNode(child_entry, self))
            elif child_entry.type == "prop":
                self.props_list.append(Prop(child_entry, self))
            elif child_entry.type == "cmd":
                self.commands_list.append(Command(child_entry, self))
            elif child_entry.type == "check" or child_entry.type == "chk":
                self.checks_list.append(Check(child_entry, self))
            else:
                print(f"line {entry.line_num}: {entry.line}")
                raise Exception(f"invalid sub entry type {child_entry.type} under node")

    def build_hier_code(self):
        # create directory here, to allow adding cmds and checks
        # the node_diag file will be created later after having subs[]
        print(f"mkdir {self.os_path}")
        os.makedirs(self.os_path, exist_ok=True)

        self.create_node_file()
        self.create_property_file()
        self.create_command_file()
        self.create_check_file()

        for sub in self.sub_nodes:
            sub.build_hier_code()
    
    def create_node_file(self):
        node_file = f"{self.os_path}/node_diag.py"
        class_name = underscrore_to_camel(self.node_name)
        if not os.path.exists(node_file):
            with open(node_file, "w") as f:
                f.write("from hood.diag_node import NodeDiag\n\n")
                f.write(f"class Node{class_name}(NodeDiag):\n\n")
                f.write(f"    def init(self):\n")
                # write subs
                subs_line = " "*8 + "self.subs = [\n"
                for sub in self.sub_nodes:
                    subs_line += " "*12 + f"\"{sub.node_name}{sub.range_str}\",\n"
                subs_line += " "*8 + "]"
                f.write(f"{subs_line}\n")
                # write props
                props_line = " "*8 + "self.props = [\n"
                for prop in self.props_list:
                    props_line += " "*12 + f"\"{prop.name}{prop.range_str}\",\n"
                props_line += " "*8 + "]"
                f.write(f"{props_line}\n")
                # write checks
                checks_line = " "*8 + "self.checks = [\n"
                for check in self.checks_list:
                    checks_line += " "*12 + f"\"{check.name}\",\n"
                checks_line += " "*8 + "]"
                f.write(f"{checks_line}\n")
                # write commands
                commands_line = " "*8 + "self.commands = [\n"
                for command in self.commands_list:
                    commands_line += " "*12 + f"\"{command.name}\",\n"
                commands_line += " "*8 + "]"
                f.write(f"{commands_line}\n")

    def create_property_file(self):
        if not len(self.props_list):
            return

        file_name = f"{self.os_path}/properties.py"
        f = open(file_name, "w")
        if not f:
            raise Exception(f"Failed to open file {file_name}")

        f.write("from hood.diag_prop import Property\n\n")

        for prop in self.props_list:
            prop.write_class_to_file(f)
            f.write(f"\n")

        f.close()

    def create_command_file(self):
        if not len(self.commands_list):
            return
        
        file_name = f"{self.os_path}/commands.py"
        f = open(file_name, "w")
        if not f:
            raise Exception(f"Failed to open file {file_name}")
            
        f.write("from hood.diag_cmd import Command\n\n")

        for command in self.commands_list:
            command.write_class_to_file(f)
            f.write(f"\n")

        f.close()

    def create_check_file(self):
        if not len(self.checks_list):
            return

        file_name = f"{self.os_path}/checks.py"
        f = open(file_name, "w")
        if not f:
            raise Exception(f"Failed to open file {file_name}")
            
        f.write("from hood.diag_check import Check, Proc\n\n")

        for check in self.checks_list:
            check.write_class_to_file(f)
            f.write(f"\n")

        f.close()

class Hier:

    def __init__(self, hier_map, top_path):
        map_f = open(hier_map, "r")
        self.map_lines = map_f.readlines()
        self.top_path = top_path
        self.num_map_lines = len(self.map_lines)
        map_f.close()

    def parse_and_create_entries(self):

        line_idx = 0

        # The nodes start at level 1, with at least one "|--" ahead of it.
        level = -1
        lowest_found_level = -1

        self.top_entry = None
        curr_entry = None
        parent = None

        # one pass to scan through the lines to generate the entries, so
        # the children list are available
        while line_idx < self.num_map_lines:
            line = self.map_lines[line_idx].strip()

            if line.startswith("#"):
                line_idx += 1
                continue

            print(f"--line {line_idx:#3d}: {line}")

            pattern = r"(?P<marks>(\|\-\-)*)(\[(?P<entry_type>[^\]]+)\])?(?P<entry_name>\S+)?"
            m = re.match(pattern, line)

            if not m:
                raise Exception(f"line {line_idx} <{line} invalid")

            len_marks = len(m.group("marks"))
            if (len_marks % 3):
                raise Exception("invalid format, should be multiple of 3")
            new_level  = int(len_marks / 3)
            if lowest_found_level == -1:
                lowest_found_level = new_level
            else:
                lowest_found_level = min(new_level, lowest_found_level)

            if not m.group("entry_type"):
                entry_type = "node"
            else:
                entry_type = m.group("entry_type")
            entry_name = m.group("entry_name")
            if entry_type == "chk" or entry_type == "check":
                if entry_name == None:
                    entry_name = "over_all"

            if new_level != level:
                print(f"    level change {level} -> {new_level}")
                if new_level == level + 1:
                    parent = curr_entry
                elif new_level > level + 1:
                    print(f"line is <{line}>")

                    raise Exception(
                        f"invalid new level {new_level}")
                else: # new_level <= level:
                    while level > new_level:
                        curr_entry = curr_entry.parent
                        level -= 1
                    if curr_entry:
                        parent = curr_entry.parent
            curr_entry = Entry(entry_type, entry_name, parent, line_idx, line)
           
            if new_level == lowest_found_level and (not self.top_entry):
                print(f"top entry: {curr_entry.name}")
                self.top_entry = curr_entry

            level = new_level

            print(f"    entry_type {entry_type}, entry_name {entry_name}, len_marks {len_marks}, level {level}")
            line_idx += 1

    def build_hier_objs_from_entries(self):

        top_empty_node = HierNode(None, None)
        top_empty_node.node_path = ":"
        top_empty_node.os_path = self.top_path

        top_entry = self.top_entry
        if top_entry.type != "node":
            raise Exception(f"The top entry should be a node")
        
        self.top_node = HierNode(top_entry, top_empty_node)
        print(f"top_node {self.top_node}")
    
    def build_hier_code(self):
        self.top_node.build_hier_code()

    def build_hier(self):
        self.parse_and_create_entries()
        self.build_hier_objs_from_entries()
        self.build_hier_code()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Diag hierarchy builder")
    parser.add_argument("hier_map")
    parser.add_argument("top_dir")

    args = parser.parse_args()
    top_dir = os.path.expanduser(args.top_dir)
    hier_map = args.hier_map
    os.makedirs(top_dir, exist_ok=True)
    hier = Hier(hier_map, top_dir)
    hier.build_hier()
