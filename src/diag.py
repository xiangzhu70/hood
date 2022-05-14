#!/usr/bin/env python3
#
#  A hierarchical OO diag framework to organize the information and tools

diag_version = "0.0.0"

import argparse
import re
import os

import diag_node
from diag_node import *


verbose = False



class Session:

    sessions_count = 0

    def __init__(self, node_path, node_args):
        self.session_id = Session.sessions_count
        Session.sessions_count += 1

        self.nodes_visited = {}

        # Examples:
        # fboss:system.platform -- entry module is fboss.py
        # :system.platform -- not entry module.  go into sub diretory.
        m = re.match(r"(?P<entry_module>\S+)?\:(?P<node_path>\S+)", node_path)
        if not m:
            raise Exception("Invalid node path")
        entry_module =  m.group("entry_module")
        node_path = m.group("node_path")
        nodes_in_path = node_path.split(".")

        diag_node.verbose = verbose
        if entry_module:
            diag_node.import_node_module(entry_module)

        self.enter_node(node_path, node_args)
        
    # TBD move to a util file or Node?
    def parse_args(node_args):
        if not node_args:
            return {}
        args_dict = {}
        for pair in node_args:
            m = re.match("(?P<key>\S+)=(?P<val>\S+)", pair)
            if not m:
                print(f"parse_args: ignore {pair}")
                continue
            args_dict[m.group("key")] = m.group("val")
        return args_dict

    def enter_node(self, node_path, node_args):
        node_args_dict = Session.parse_args(node_args)
        self.top_node = NodeDiag(inst_name="top")
        self.curr_node = self.top_node
        self.top_node.node_file_path = os.getcwd()
        self.top_node.node_module_path = ""
        nodes_in_path = node_path.split(".")
        curr_node_path = ""
        for node_name in nodes_in_path:
            if curr_node_path:
                curr_node_path += "."
            curr_node_path += node_name
            new_node = self.curr_node.enter_sub_node(node_name, input_dict=node_args_dict)
            if not new_node:
                raise Exception(f"Failed to reach {curr_node_path}")
            self.nodes_visited[curr_node_path] = new_node
            self.curr_node = new_node
 
            
    def run(self, args):
        print(args)
        print(f"cmd is {args.command}\n\n")
        if (args.command == "show"):
            if (args.tree):
                tree_level = args.tree
                if len(args.cmd_args):
                    show_type = args.cmd_args[0]
                else:
                    show_type = "node"
                self.curr_node.show_tree(
                    tree_level, indent="", show_type=show_type)     
            else:
                self.curr_node.show(args.cmd_args)
        elif (args.command == "check"):
            self.curr_node.check(args.cmd_args)
        elif (args.command == "cmd"):
            self.curr_node.cmd(args.cmd_args)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description = "Unified Diag Framework.  Version {diag_version}",
        formatter_class = argparse.RawTextHelpFormatter,
    )

    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("node", help="node path")
    parser.add_argument("-n", "--node_args", nargs='*',
        help="args to pass to node\n"
        "any number of <key>=<value> pairs terminated by -x\n",
    )
    parser.add_argument("-x", help="dummpy to terminate node_args", action="store_true")
    parser.add_argument("-t", "--tree", type=int, const=-1, nargs="?", help="")

    parser.add_argument(
        "command",
        help="[shell|check|show] -- global commands\n"
        "shell -- Enter a command shell at the node\n"
        "check -- Run check functions\n"
        "show [sub|commands|locals|checks]\n"
        "      sub -- show sub systems. the default\n"
        "      commands -- show commands at this node\n"
        "      cmd, cmds -- alias to commands\n"
        "      locals -- local variables at this node\n"
        "      checks -- checks at this node\n"
        "<node-specific commands>, as listed by 'show cmds'\n",
    )

    parser.add_argument(
        #'-c', '--cmd_args',
        "cmd_args",
        help="command arguments\n" "any number of <key>=<value> pairs",
        nargs="*",
    )

    args = parser.parse_args()

    if args.verbose:
        verbose = args.verbose


    #TBD 
    import os, sys
    sys.path.insert(0, os.getcwd())

    session = Session(args.node, args.node_args)

    session.run(args)

