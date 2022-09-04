#!/usr/bin/env python3
#
#  A hierarchical OO diag framework to organize the information and tools

diag_version = "0.0.0"

import argparse
import re
import os

from hood.diag_session import Session

from pdb import set_trace as stop


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description = "Unified Diag Framework.  Version {diag_version}",
        formatter_class = argparse.RawTextHelpFormatter,
    )

    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-p", "--path")
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

    if args.path:
        src_file_path_prefix = os.path.abspath(os.path.expanduser(args.path))
    else:
        src_file_path_prefix = os.getcwd()
    session = Session(args.node, args.node_args, 
        src_file_path_prefix=src_file_path_prefix, verbose=args.verbose)

    session.cli_cmd(args.command, args.cmd_args, args.tree)

