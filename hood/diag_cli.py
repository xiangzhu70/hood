#!/usr/bin/env python3
from pdb import set_trace as stop

import cmd2

from .diag_session import Session


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
        host = self.session.node_args["host"]
        self.prompt = f"{host} {self.session.obj_path.path}> "

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

    def do_run(self, args):
        """
        Run command or a check
        """
        curr_obj = self.session.curr_obj
        stop()
        curr_obj.cli_cmd("run", args)

    def do_ls(self, args):
        """
        list nodes
        """
        node = self.session.curr_node
        if len(args.arg_list):
            if args.arg_list[0] == "-t":
                node.traverse_tree(show_node=True)
            return
        if len(node.subs):
            for sub in node.subs:
                print(f"  .{sub}")
        else:
            print("No sub node here")

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


class CliNameSpace:
    def __init__(self, name=None):
        self.name = name
        self.allowed_entries = []
        self.parse_func = None
        self.help = None

    def expand_shortcut(self, shortcut):
        if shortcut in self.shortcuts:
            return self.shortcuts[shortcut]
