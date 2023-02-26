#!/usr/bin/env python3
#
#  A hierarchical OO diag framework to organize the information and tools

from hood.diag_state import DiagState
from hood.diag_utils import parse_key_val_pairs, ShellCommand
from hood.diag_obj import DiagObjType, DiagObj
from hood.diag_node import NodeDiag
from hood.diag_check import Check
from pdb import set_trace as stop
import logging
import sys
import os
diag_version = "0.0.0"


verbose = False


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

        self.setup_logging()
        self.sh_cmd = ShellCommand(self.logger)

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

        if node_args_str:
            print("Got node_args, should this still be supported?")
            exit(-1)
        # self.node_args = parse_key_val_pairs(node_args_str)

        self.obj_path = DiagObj.Path(
            init_path=":", top_node_name=self.top_node_name)
        # self.setup_top_node(self.top_node_name, node_file_path=dir_path)
        # self.goto_obj(entry_obj_path)
        self.setup_top_empty_node(
            sub_node=self.top_node_name, node_file_path=dir_path)
        self.goto_obj(entry_obj_path)

    def setup_logging(self):
        logger = logging.getLogger('diag log')
        logger.setLevel(logging.DEBUG)
        if not self.verbose:
            # Remove console output.  The logging to the file is still on.
            logger.handlers.clear()
            logger.propagate = False
        fh = logging.FileHandler("/tmp/diag_run.log", mode='w')
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

    def goto_obj(self, obj_path_str, obj_type=None):
        # shortcut case
        # 'cd inband_ping" will go to .:[check]inband_ping.
        # since the names are already in the dict, easy to look up, to save some typing
        if (
            isinstance(self.curr_obj, NodeDiag)
            and obj_path_str in self.curr_obj.obj_names_dict
        ):
            class_type = self.curr_obj.obj_names_dict[obj_path_str]
            if class_type in [DiagObjType.Check, DiagObjType.Command]:
                obj_path_str = f".:[{class_type.value}]{obj_path_str}"

        move_action = self.obj_path.move_path(
            obj_path_str, obj_type=obj_type
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
        elif obj_type == "check" or obj_type == "cmd":
            curr_obj = getattr(self.curr_node, obj_name)
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
    def cli_cmd(self, arg_cmd, args, tree=-1):
        return self.curr_obj.cli_cmd(arg_cmd, args, tree)
