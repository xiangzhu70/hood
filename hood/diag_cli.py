#!/usr/bin/env python3
from pdb import set_trace as stop

import cmd2
import json

from .diag_session import Session


from cmd2 import Cmd2ArgumentParser, with_argparser
cmd_argparser = Cmd2ArgumentParser()
cmd_argparser.add_argument("cmd", help="command to run")
cmd_argparser.add_argument("-d", "--depth", type=int, help="tree depth")
cmd_argparser.add_argument("args", nargs="*", help="command args")


class CmdShell(cmd2.Cmd):
    def __init__(self,
            node_file_path,
            shell_mode,
            #node_args,
            #conf_file,
            #state_file_path,
            verbose,
            flag_output_json,
            console_show = True):
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
        if not shell_mode:
            self.hidden_commands += ["cd", "cmd"]

        self.flag_output_json = flag_output_json
        self.output_json = None
        self.console_show = console_show

        self.session = Session(
            node_file_path,
            #node_args,
            #conf_file,
            #state_file_path,
            verbose,
            flag_output_json)

        self._set_prompt()

    def _set_prompt(self):
        self.prompt = f"{self.session.obj_path}> "

    def postcmd(self, stop: bool, line: str) -> bool:
        self._set_prompt()
        return stop

    def do_show(self, args):
        """
        Show node, command, or check context-specific info.
        """
        self.do_cmd(f"show {args}")

    def do_map(self, args):
        """
        Show node map
        """
        self.do_cmd(f"map {args}")

    def do_help(self, args):
        """
        Show Help
        """
        self.do_cmd(f"help {args}")

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

    # This is for testing the cmd received from the web server.
    @with_argparser(cmd_argparser)
    def do_cmd(self, args):
        """
        Run a command on the current node
        """
        # web server also calls session.cli_cmd() this way
        args_list = args.args
        self.output_dict = self.session.cli_cmd(
            args.cmd, args_list, tree=args.depth, console_show=self.console_show)
        if self.flag_output_json:
            self.output_json = json.dumps(self.output_dict)


class CliNameSpace:
    def __init__(self, name=None):
        self.name = name
        self.allowed_entries = []
        self.parse_func = None
        self.help = None

    def expand_shortcut(self, shortcut):
        if shortcut in self.shortcuts:
            return self.shortcuts[shortcut]
