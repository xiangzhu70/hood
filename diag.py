#!/usr/bin/env python3
#
#  A hierarchical OO diag framework to organize the information and tools

from pdb import set_trace as stop
from hood.diag_cli import CmdShell
import os
import argparse
diag_version = "0.0.0"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=f"Hierarchical Diag Framework.  Version {diag_version}",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("-v", "--verbose", action="store_true")
    #parser.add_argument("-c", "--conf")
    #parser.add_argument("--state_path")
    parser.add_argument(
        "-j", "--json", action="store_true", help="output json")

    parser.add_argument("node", help="[file_path/]node_path")
    # parser.add_argument("-n", "--node_args", nargs='*',
    #                     help="args to pass to node when entering the node\n"
    #                     "any number of <key>=<value> pairs terminated by -x\n",
    #                     )
    # parser.add_argument(
    #     "-x", help="dummpy to terminate node_args", action="store_true")
    # parser.add_argument("-t", "--tree", type=int, const=-1, nargs="?", help="")

    parser.add_argument(
        "command",
        help=
        "shell -- Enter a command shell at the node\n"
        "show  -- Show node details\n"
        "map   -- Show the hierarchy map\n"
        "help  -- Help info on this node\n"
        "<node-specific commands>, as listed by 'show'\n",
    )

    parser.add_argument(
        # '-c', '--cmd_args',
        "cmd_args",
        help="command arguments\n" "any number of <key>=<value> pairs",
        nargs="*",
    )

    args = parser.parse_args()

    node_file_path = os.path.abspath(os.path.expanduser(args.node))

    shell_mode = args.command == "shell"

    cmd_shell = CmdShell(
        node_file_path,
        shell_mode = shell_mode,
        #args.node_args,
        #conf_file=args.conf,
        #state_file_path=args.state_path,
        verbose=args.verbose,
        flag_output_json=args.json)

    ret = None
    if args.command == "shell":
        ret = cmd_shell.cmdloop()
    elif args.command in ["show", "map", "help"]:
        cmd = args.command + " ".join(args.cmd_args)
        ret = cmd_shell.onecmd(cmd)
    else:
        # if args.tree:
        #     tree_arg = "-d " + str(args.tree)
        # else:
        #     tree_arg = ""
        cmd = "cmd " + args.command 
        #cmd += " " tree_arg
        cmd += " " + " ".join(args.cmd_args)
        # Always go through the Cmd2 module, even not in shell mode
        ret = cmd_shell.onecmd(cmd)
    if args.json:
        print(f"output_dict = {cmd_shell.output_dict}")
        print(f"output_json: {cmd_shell.output_json}")
