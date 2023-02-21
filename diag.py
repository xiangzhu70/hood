#!/usr/bin/env python3
#
#  A hierarchical OO diag framework to organize the information and tools

from pdb import set_trace as stop
from hood.diag_session import Session
from hood.diag_cli import CmdShell
import os
import re
import argparse
diag_version = "0.0.0"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Unified Diag Framework.  Version {diag_version}",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-c", "--conf")
    parser.add_argument("--state_path")
    parser.add_argument("node", help="[file_path/]node_path")
    parser.add_argument("-n", "--node_args", nargs='*',
                        help="args to pass to node when entering the node\n"
                        "any number of <key>=<value> pairs terminated by -x\n",
                        )
    parser.add_argument(
        "-x", help="dummpy to terminate node_args", action="store_true")
    parser.add_argument("-t", "--tree", type=int, const=-1, nargs="?", help="")
    parser.add_argument(
        "-j", "--json", action="store_true", help="output json")

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
        # '-c', '--cmd_args',
        "cmd_args",
        help="command arguments\n" "any number of <key>=<value> pairs",
        nargs="*",
    )

    args = parser.parse_args()

    node_file_path = os.path.abspath(os.path.expanduser(args.node))

    session = Session(node_file_path, args.node_args,
                      conf_file=args.conf,
                      state_file_path=args.state_path,
                      verbose=args.verbose,
                      output_json=args.json)

    if args.command == "shell":
        cmd_shell = CmdShell(session)
        cmd_shell.cmdloop()
    else:
        session.cli_cmd(args.command, args.cmd_args, args.tree)
