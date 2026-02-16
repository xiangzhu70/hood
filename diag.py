#!/usr/bin/env python3
#
#  A hierarchical OO diag framework to organize the information and tools

from pdb import set_trace as stop
from hood.diag_cli import CmdShell
import os
import sys
import argparse
diag_version = "0.0.0"
diag_desc = f"Hierarchical Diag Framework.  Version {diag_version}"

def env_fetch():
    file_path = None
    node_path = None
    if "HIER_FILE_PATH" in os.environ:
        file_path = os.environ["HIER_FILE_PATH"]
    if "HIER_NODE_PATH" in os.environ:
        node_path = os.environ["HIER_NODE_PATH"]
    return (file_path, node_path)

def env_show():
    (file_path, node_path) = env_fetch()
    if file_path:
        print(f"HIER_FILE_PATH={file_path}")
    else:
        print("Missing env HIER_FILE_PATH")
    if node_path:
        print(f"HIER_NODE_PATH={node_path}")
    else:
        print("Missing env HIER_NODE_PATH")
    
if __name__ == "__main__":

    print("\n" + "="*50 +f"\n    {diag_desc}\n" + "-"*50 + "\n")

    first_arg = sys.argv[1]
    if first_arg == "env":
        env_show()
        exit(0)
    
    parser = argparse.ArgumentParser(
        description=diag_desc,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("-v", "--verbose", action="store_true")
    #parser.add_argument("-c", "--conf")
    #parser.add_argument("--state_path")
    parser.add_argument(
        "-j", "--json", action="store_true", help="output json")

    parser.add_argument("-n", "--node", help="[file_path/]node_path")
    # parser.add_argument("-n", "--node_args", nargs='*',
    #                     help="args to pass to node when entering the node\n"
    #                     "any number of <key>=<value> pairs terminated by -x\n",
    #                     )

    parser.add_argument(
        "command",
        help=
        "shell  -- Enter a command shell at the node\n"
        "show   -- Show node details\n"
        "map    -- Show the hierarchy map\n"
        "help   -- Help info on this node\n"
        "run    -- Run a command or a check\n"
        "triage -- Run a check recursively following the dep tree"
        "bring  -- Run the proc for a check recursivly"
        "<node-specific commands>, as listed by 'show'\n",
    )

    parser.add_argument(
        # '-c', '--cmd_args',
        "cmd_args",
        help="command arguments\n" "any number of <key>=<value> pairs",
        nargs="*",
    )

    args = parser.parse_args()

    node_file_path = None
    if args.node:
        node_file_path = os.path.abspath(os.path.expanduser(args.node))
    else:
        # get node_file_path from env
        (file_path, node_path) = env_fetch()
        if not file_path:
            print("-n <node> missing, not finding it from env either")
            print("env HIER_FILE_PATH not set.")
            exit(-1)
        if not node_path:
            node_path = ":"
        node_file_path = f"{file_path}/{node_path}"      

    shell_mode = args.command == "shell"

    cmd_shell = CmdShell(
        node_file_path,
        shell_mode = shell_mode,
        verbose=args.verbose,
        flag_output_json=args.json)

    ret = None
    if args.command == "shell":
        ret = cmd_shell.cmdloop()
    elif args.command in ["show", "map", "help"]:
        cmd = args.command + " " + " ".join(args.cmd_args)
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
        print(f"output_json: {cmd_shell.output_json}")
