#!/usr/bin/env python3
from pdb import set_trace as stop

import cmd2

from .diag_session import Session

# For now, directly call session.cli_cmd()
# Not sure if it is better to make use of cmd2's argparser.
# from cmd2 import Cmd2ArgumentParser, with_argparser
# argparser = Cmd2ArgumentParser()


class CmdShell(cmd2.Cmd):
    def __init__(self, session):
        super().__init__(allow_cli_args=False)
        self.allow_cli_args = False
        self.hidden_commands += [
            "alias",
            "edit",
            "history",
            "macro",
            "shell",
            "set",
            "shortcuts",
            "py",
            "run_pyscript",
            "run_script",
        ]
        self.session = session
        self._set_prompt()

    def _set_prompt(self):
        # host = self.session.node_args["host"]
        # self.prompt = f"{host} {self.session.obj_path.path}> "
        self.prompt = f"{self.session.obj_path.path}> "

    def postcmd(self, stop: bool, line: str) -> bool:
        self._set_prompt()
        return stop

    def help_show(self):
        curr_obj = self.session.curr_obj
        curr_obj.help_show()

    def do_show(self, args):
        """
        Show node, command, or check context-specific info.
        """
        curr_obj = self.session.curr_obj
        curr_obj.cli_cmd("show", args.arg_list)

    #  At the node level, there is show -t doing the same thing as ls -t.
    # def do_ls(self, args):
    #     """
    #     list nodes
    #     """
    #     node = self.session.curr_node
    #     if len(args.arg_list):
    #         if args.arg_list[0] == "-t":
    #             node.traverse_tree(show_node=True)
    #         return
    #     if len(node.subs):
    #         for sub in node.subs:
    #             print(f"  .{sub}")
    #     else:
    #         print("No sub node here")

    def do_cd(self, args):
        """
        change focus. could be at a node, or a check
        cd <node_path>
        cd top
        cd ..
        cd <check_name>
        """
        dest = args.arg_list[0]
        self.session.goto_obj(dest)

    # @with_argparser(argparser)
    # def do_runcmd(self, opts):

    # This is for testing the cmd received from the web server.
    def do_cmd(self, args):
        """
        Run a command on the current node
        """
        print(f"cmd: {args}")

        # web server also calls session.cli_cmd() this way
        tree = "-t" in args.arg_list
        self.session.cli_cmd(args.arg_list[0], args.arg_list[1:], tree=tree)


class CliNameSpace:
    def __init__(self, name=None):
        self.name = name
        self.allowed_entries = []
        self.parse_func = None
        self.help = None

    def expand_shortcut(self, shortcut):
        if shortcut in self.shortcuts:
            return self.shortcuts[shortcut]
