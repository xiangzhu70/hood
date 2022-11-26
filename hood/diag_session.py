#!/usr/bin/env python3
#
#  A hierarchical OO diag framework to organize the information and tools

diag_version = "0.0.0"

import sys
import logging

from pdb import set_trace as stop

from hood.diag_check import Check
from hood.diag_node import NodeDiag
from hood.diag_obj import DiagObjType, DiagObj
from hood.diag_utils import parse_key_val_pairs, ShellCommand
from hood.diag_state import DiagState

verbose = False


class Session:

    sessions_count = 0

    def __init__(
        self,
        entry_obj_path,
        node_args_str,
        import_path_prefix="",
        top_node_name=None,
        src_file_path_prefix="",
        conf_file=None,
        state_file_path="/tmp/diag_state",
        verbose=False
    ):
        self.session_id = Session.sessions_count
        Session.sessions_count += 1

        self.verbose = verbose
        self.setup_logging()
        self.sh_cmd = ShellCommand(self.logger)

        self.state = DiagState(conf_file, state_file_path)

        if not top_node_name:
            top_node_name = entry_obj_path.partition('.')[0]
        self.top_node_name = top_node_name
        self.src_file_path_prefix = src_file_path_prefix

        sys.path.append(src_file_path_prefix)

        if import_path_prefix != "" and not import_path_prefix.endswith("."):
            import_path_prefix += "."
        self.import_path_prefix = import_path_prefix

        self.nodes_visited = {}
        self.mock_patchers = {}

        self.node_args = parse_key_val_pairs(node_args_str)

        self.obj_path = DiagObj.Path(init_path=":", top_node_name=top_node_name)
        self.setup_top_node(top_node_name, node_file_path=src_file_path_prefix)
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

    def setup_top_node(self, top_node_name, node_file_path=""):
        top_empty_node = NodeDiag(
            context_node=None, inst_name="top", node_file_path=node_file_path, import_path=""
        )
        top_empty_node.subs.append(top_node_name)
        top_empty_node.session = self
        top_empty_node.import_path = ""
        self.curr_node = top_empty_node
        self.curr_obj = top_empty_node
        self.top_node = top_empty_node
        self.nodes_visited[":"] = top_empty_node
        return top_empty_node

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

        (top, parent_count, sub_node_path) = self.obj_path.move(
            obj_path_str, obj_type=obj_type
        )
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
                fields = sub_node_path.split(".", maxsplit=1)
                sub = fields[0]
                if len(fields) >= 2:
                    sub_node_path = fields[1]  # remaining node path
                else:
                    sub_node_path = ""
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

    def cli_cmd(self, arg_cmd, args, tree):
        return self.curr_obj.cli_cmd(arg_cmd, args, tree)
