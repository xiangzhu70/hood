#!/usr/bin/env python3
#
#  A hierarchical OO diag framework to organize the information and tools

from hood.diag_state import DiagState
from hood.diag_utils import parse_key_val_pairs
from pltm.sh_cmd import ShellCommand
from pltm.ssh_cmd import SshCommand
from hood.diag_obj import DiagObjType, DiagObj
from hood.diag_node import NodeDiag
from hood.diag_check import Check
from pdb import set_trace as stop
import logging
import sys
import os
import re
diag_version = "0.0.0"


verbose = False

#TBD Session contains lots of platform and environment logic.  separate them out?
class Session:

    sessions_count = 0

    def __init__(
        self,
        file_path,
        node_args_str=None,
        conf_file=None,
        state_file_path="/tmp/diag_state",
        verbose=False,
        output_json=False,
    ):
        self.session_id = Session.sessions_count
        Session.sessions_count += 1

        self.verbose = verbose
        self.output_json = output_json
        self.node_args = {}

        self.setup_logging()
        self.sh_cmd = ShellCommand(self.logger)
        self.ssh_cmd = SshCommand(self.logger)

        self.state = DiagState(conf_file, state_file_path)

        dir_path, entry_obj_path = os.path.split(file_path)
        self.top_node_name = entry_obj_path.partition('.')[0]

        self.src_file_path_prefix = dir_path
        sys.path.append(dir_path)
        self.import_path_prefix = ""
        # TBD why do we need this?
        # the dir_path is already in sys.path, so the import path should be
        # relative to the the dir_path.  No need to prefix it.

        self.nodes_visited = {}
        self.mock_patchers = {}

        # it really means the session_args, used by not only
        # the nodes, but also all the other components.
        if node_args_str:
            self.node_args = parse_key_val_pairs(node_args_str)

        self.obj_path = DiagObj.Path(
            init_path=":", top_node_name=self.top_node_name)
        # self.setup_top_node(self.top_node_name, node_file_path=dir_path)
        # self.goto_obj(entry_obj_path)
        self.setup_top_empty_node(
            sub_node=self.top_node_name, node_file_path=dir_path)
        try:
            self.goto_obj(entry_obj_path, verbose=verbose)
        except Exception as e:
            print(f"Exception: {e}")
            exit(-1)

    def setup_logging(self):
        cmd_run_log_file = "/tmp/diag_run.log"
        if self.verbose:
            print(f"diag_session: Set up cmd run log {cmd_run_log_file}")
        logger = logging.getLogger()
        # Removes the console handler
        logger.removeHandler(logger.handlers[0])
        # handler = logging.StreamHandler()
        # formatter = logging.Formatter('%(message)s')
        # handler.setFormatter(formatter)
        # logger.addHandler(handler)
        if not self.verbose:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(cmd_run_log_file, mode='w')
        logger.addHandler(fh)
        self.logger = logger

    def setup_top_empty_node(self, sub_node, node_file_path=""):
        top_empty_node = NodeDiag(
            context_node=None, inst_name="top", node_file_path=node_file_path, import_path=""
        )
        top_empty_node.subs.append(sub_node)
        top_empty_node.session = self
        top_empty_node.import_path = ""
        self.curr_node = top_empty_node
        self.curr_obj = top_empty_node
        self.top_node = top_empty_node
        self.nodes_visited[":"] = top_empty_node
        return top_empty_node

    # def setup_and_goto_top_node(self, top_node_name, node_file_path=""):
    #     top_node = NodeDiag(
    #         context_node=None, inst_name=top_node_name, node_file_path=node_file_path, import_path=""
    #     )
    #     top_node.session = self
    #     top_node.import_path = ""
    #     self.curr_node = top_node
    #     self.curr_obj = top_node
    #     self.top_node = top_node
    #     self.nodes_visited[":"] = top_node
    #     return top_node

    def goto_obj(self, obj_path_str, obj_type=None, verbose=False):
        if verbose:
            print(f"goto_obj: obj_path_str {obj_path_str}, type {obj_type}")
        # shortcut case
        # 'cd inband_ping" will go to .:[check]inband_ping.
        # since the names are already in the dict, easy to look up, to save some typing
        if (
            isinstance(self.curr_obj, NodeDiag)
            and obj_path_str in self.curr_obj.obj_names_dict
        ):
            class_type = self.curr_obj.obj_names_dict[obj_path_str]
            if class_type in [DiagObjType.Check, DiagObjType.Command, DiagObjType.Property]:
                obj_path_str = f".:[{class_type.value}]{obj_path_str}"

        move_action = self.obj_path.move_path(
            obj_path_str, obj_type=obj_type, verbose=verbose
        )
        (top, parent_count, sub_node_path) = (move_action.is_top,
                                              move_action.parent_count, move_action.sub_node_path)

        obj_type = self.obj_path.obj_type
        obj_name = self.obj_path.obj_name
        if self.obj_path.path != self.curr_node.node_path:
            if top:
                curr = self.top_node
            else:
                curr = self.curr_node
                while parent_count > 0:
                    curr = curr.node_parent
                    parent_count -= 1
            while sub_node_path:
                find_start_pos = 0
                while True:
                    idx = sub_node_path.find(".", find_start_pos)
                    if idx == -1:
                        sub = sub_node_path
                        sub_node_path = ""
                        break
                    elif sub_node_path[idx+1] != ".":
                        sub = sub_node_path[:idx]
                        sub_node_path = sub_node_path[idx + 1:]
                        break
                    find_start_pos = idx + 2

                curr = curr.enter_sub_node(sub)
            self.curr_node = curr

        if obj_type == "node":
            curr_obj = self.curr_node
        elif obj_type == "check" or obj_type == "cmd" or obj_type=="prop":
            curr_obj = self.curr_node.get_obj_by_attr_name(obj_name)
        else:
            stop()
            raise Exception("unknown target type")

        if not curr_obj:
            raise Exception("Failed to set up curr_obj")

        self.curr_obj = curr_obj
        return curr_obj

    # On the current node obj, run the command with the given args
    # tree is the bool flag to indicate the command is on the tree mode
    # only or all the nodes underneath.
    # TBD - should this bool flag be specific, or should it be a here?
    def cli_cmd(self, arg_cmd, args_list, tree=-1, console_show=True):
        #print(f"-- diag_session: arg_cmd {arg_cmd}, args {args_list}, tree {tree}, node_args {self.node_args}")
        # logger_level = self.logger.level
        # raising logger level is not really needed, because the default log()
        # does self.logger.info()
        # will consider how to seperate internal logging level and command
        # logging level later.
        # if console_show:
        #     self.logger.setLevel(logging.DEBUG)
        args = {}
        for arg in args_list:
            m = re.match(r"(?P<key>\S+)=(?P<val>\S+)", arg)
            if not m:
                print("Invalid arg")
                continue
            args[m.group("key")] = m.group("val")
        ret = self.curr_obj.cli_cmd(arg_cmd, args, tree)
        # self.logger.setLevel(logger_level)
        return ret
