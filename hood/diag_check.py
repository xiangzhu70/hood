import importlib
import re
import textwrap
import unittest
from pdb import set_trace as stop
from unittest.mock import patch

from hood.diag_cmd import Command
from hood.diag_obj import DiagObjType
from hood.diag_utils import gen_graphviz


class Check(Command):
    def __init__(self, context_node, inst_name, node_file_path, import_path):
        super().__init__(context_node, inst_name, node_file_path, import_path)
        self.node = context_node
        self.inst_name = inst_name
        self.check_path = f"{self.node.node_path}:[check]{inst_name}"
        self.obj_path = self.check_path

        # Check this first.  Save time in OK route.
        self.ok_sufficient_conditions = []

        # Check these to ensure the run() can work.
        # save time in the FAIL route which necessary
        # tool is not OK.
        self.prerequisite_conditions = []
        # dependency / causality conditions.
        self.ok_necessary_conditions = [
            # <check> == OK
        ]

        # str in these formats
        # [root_cause]<message>
        # [check]<next check path>
        # [investigate]<reason for further investigation>
        self.action_on_fail = None

        self.init()

    def init(self):
        pass

    def show(self):
        print(f"Check {self.check_path}")
        print(f"class name = {self.__class__.__name__}")
        print("-- ok_sufficient_conditions")
        for cond in self.ok_sufficient_conditions:
            print(f"  {cond}")
        print("-- prerequisite_conditions")
        for cond in self.prerequisite_conditions:
            print(f"  {cond}")
        print("-- ok_necessary_conditions")
        for cond in self.ok_necessary_conditions:
            print(f"  {cond}")

    def run(self, cmd_args=None):
        # The default is to check the dependent factors.
        return "DEP"

    def triage(self, level=0, branch="", indent="  ", remediate=False):
        session = self.node.session

        if level == 0:
            session.triage_visited = {}

        check_path = f"{self.node.node_path}:[check]{self.inst_name}"

        if check_path in session.triage_visited:
            (branch_point, ret) = session.triage_visited[check_path]
            print(f"{indent}{branch[-3:]} |-> {check_path} = {ret}")
            local_indent_len = len(indent) + 8
            print(f"{indent:<{local_indent_len}} -- visited earlier at {branch_point}")
            return ret

        # save the entry into visited[].  at this point, there is
        # no conclusion yet.  but it should be saved to avoid
        # dep<->suff circles.
        session.triage_visited[check_path] = (branch, None)

        # sufficient conditions
        if len(self.ok_sufficient_conditions):
            print(f"{indent}{branch[-3:]} |-> {check_path}")
        indent_in_loop = indent + "  "
        for idx, cond in enumerate(self.ok_sufficient_conditions):
            cond_check_path, cond_status_expect = Check.cond_parse(cond)
            cond_check_obj = session.goto_obj(
                cond_check_path, obj_type=DiagObjType.Check
            )
            check_path = session.obj_path.path
            branch_next = f"{branch}.s{idx}"
            if session.obj_path.path in session.triage_visited:
                # skip to avoid the dep<->suf circle
                # print(f"xx skip suf {session.obj_path.path}")
                (branch_point, earlier_ret) = session.triage_visited[check_path]
                print(
                    f"{indent_in_loop}{branch_next[-3:]} |-> {check_path} = {earlier_ret}"
                )
                local_indent_len = len(indent_in_loop) + 8
                print(
                    f"{indent_in_loop:<{local_indent_len}} -- visited earlier at {branch_point}"
                )
                session.goto_obj(self.node.node_path)
                if earlier_ret == "OK":
                    print(f"{indent}{branch[-3:]} |-> {check_path} = OK")
                    return "OK"
                continue
            ret = cond_check_obj.run()
            print(f"{indent_in_loop}{branch_next[-3:]}{session.obj_path.path} = {ret}")
            session.goto_obj(self.node.node_path)
            session.triage_visited[session.obj_path.path] = (branch_next, ret)
            if ret == "OK":
                # If any sufficient condition is good, then OK
                # print(f"{indent}{branch}{check_path} = {ret}")
                print(f"{indent_in_loop}{branch[-3:]}{check_path} = {ret}")
                session.triage_visited[check_path] = (branch, "OK")
                return "OK"

        # prerequisite conditions
        if len(self.prerequisite_conditions):
            print(f"{indent}{branch[-3:]} |-> {check_path}")
        for idx, cond in enumerate(self.prerequisite_conditions):
            cond_check_path, cond_status_expect = Check.cond_parse(cond)
            cond_check_obj = session.goto_obj(
                cond_check_path, obj_type=DiagObjType.Check
            )
            branch_next = f"{branch}.p{idx}"
            ret = cond_check_obj.triage(
                level=level + 1,
                branch=branch_next,
                indent=indent + "  ",
                remediate=remediate,
            )
            session.goto_obj(self.node.node_path)
            # If any prerequisite condition fails, then fail.
            if ret != "OK":
                print(f"{indent}{branch[-3:]} |-> {check_path} = {ret}")
                session.goto_obj(self.node.node_path)
                return "FAIL"

        # Now run own run()
        ret = self.run()

        if ret != "OK" and remediate and hasattr(self, "remediate_cmd"):
            print(f"{indent}{branch[-3:]} |-> {check_path} = {ret}")
            print(f"{indent}  -- Remediate.  {self.remediate_cmd}") 
            self.node.remote_run(self.remediate_cmd)
            print(f"{indent}  -- Retry")
            ret = self.run()

        session.triage_visited[check_path] = (branch, ret)
        print(f"{indent}{branch[-3:]} |-> {check_path} = {ret}")

        if ret == "OK":
            return "OK"

        dep_failure_found = False
        for idx, cond in enumerate(self.ok_necessary_conditions):
            cond_check_path, cond_status_expect = Check.cond_parse(cond)
            cond_check_obj = session.goto_obj(
                cond_check_path, obj_type=DiagObjType.Check
            )
            branch_next = f"{branch}.d{idx}"
            dep_ret = cond_check_obj.triage(
                level=level + 1,
                branch=branch_next,
                indent=indent + "  ",
                remediate=remediate
            )
            if dep_ret != "OK":
                dep_failure_found = True
            session.goto_obj(self.node.node_path)

        if ret == "DEP" and not dep_failure_found:
            return "OK"

        if hasattr(self, "action_on_fail") and self.action_on_fail:
            print(f"=>{indent}===>>> {self.action_on_fail}")
        elif not dep_failure_found:
            print(
                f"=>{indent}===>>> [investigate]check failed. but all dependency checks passed"
            )

        return "FAIL"

    def mock_check_start(self, check_path, return_val):
        # print(f"mock_check_start: check_path={check_path} == {return_val}")
        # print(f"mock_check_start, self is {self.inst_name}, check_path is {check_path}, run is {self.run}")
        curr_node = self.node
        curr_node_path = self.node.node_path
        session = curr_node.session

        check_obj = session.goto_obj(check_path)
        check_name = session.obj_path.obj_name
        node = check_obj.node
        check_class_name = node.obj_name_to_class_name(DiagObjType.Check, check_name)
        checks_mod_import_path = (
            session.import_path_prefix + node.node_path[1:] + ".checks"
        )
        mod = importlib.import_module(checks_mod_import_path)
        # if "asic_presence" in check_path:
        #    stop()
        patcher = patch.object(mod.__dict__[check_class_name], "run")
        mock_check_run = patcher.start()
        mock_check_run.return_value = return_val
        session.mock_patchers[check_path] = patcher
        session.goto_obj(curr_node_path)  # back to original position

    def mock_patchers_stop(self):
        patchers = self.node.session.mock_patchers
        for check_path in patchers:
            # print(f"stop patcher at {check_path}")
            patcher = patchers[check_path]
            patcher.stop()

    def test_triage(self, inject_str):
        ret = self.run()
        print(f"** Before mocking. {self.check_path} ret={ret}")
        session = self.node.session
        inject_pattern = r"inject=\[(?P<inject_cond>\S+)\]"
        m = re.match(inject_pattern, inject_str)
        if not m:
            print(f"Invalid inject_str <{inject_str}>")
            print(f"The expected pattern is <{inject_pattern}>")
            stop()
            raise Exception("invalid inject condition")
        inject_cond = m.group("inject_cond")
        (inject_check_path, inject_ret) = Check.cond_parse(inject_cond)
        top_node = session.goto_obj(":")
        all_checks = top_node.find_attr("check")
        session.goto_obj(inject_check_path, obj_type=DiagObjType.Check)
        inject_check_node = session.curr_node
        inject_check_dependents = inject_check_node.check_dependents_find(
            session.obj_path.obj_name
        )
        for check in inject_check_dependents:
            all_checks[check] = True
        for check in all_checks:
            if all_checks[check]:
                return_val = "FAIL"
            else:
                return_val = "OK"
            self.mock_check_start(check, return_val)
        print(f"** <{inject_check_path}> and all its dependencies are patched.")
        ret = self.run()
        print(f"{self.check_path} run ret={ret}")
        self.triage()
        self.mock_patchers_stop()
        ret = self.run()
        print(f"** All patches are cleared. {self.check_path} ret={ret}")

    # get valid label for graphviz.  no : or . allowed.
    def check_path_to_label(self, check_path: str):
        if check_path.startswith(".:"):
            # it could be too short and having naming conflicts
            check_path = self.node.inst_name + "." + check_path
        return Check.cls_check_path_to_label(check_path)

    # TBD will switch to python graphviz module
    def decision_graph(
        self,
        lines,
        visited,
        dep_parent_label=None,
        prev=None,
        prev_line_label=None,
        level=0,
    ):
        check_path = self.check_path
        session = self.node.session
        check = self
        check_name = self.inst_name
        check_label = self.check_path_to_label(check_path)
        if not check_name:
            check_name = "overall"
        if level == 0:
            lines.append("digraph {")
            lines.append("node [shape=Rectangle]")

        check_entry_label = check_label
        check_ok_label = check_label
        check_fail_label = check_label
        check_suf_label = check_label
        check_pre_label = check_label

        if check_label in visited:
            is_composite = visited[check_label]
            if is_composite:
                check_entry_label = f"{check_label}_entry"
            if dep_parent_label:
                # dashed lines shoe dependency
                lines.append(
                    f"{dep_parent_label} -> {check_entry_label} [style=dashed]"
                )
            if prev:
                lines.append(f"{prev} -> {check_entry_label} {prev_line_label}")
            return visited[check_label]

        if "presence" in check_label:
            stop()
        (suf_exist, pre_exist, internal_lines) = check.check_graph_internal(
            check_path, check_label
        )
        lines += internal_lines
        is_composite = suf_exist or pre_exist

        if is_composite:
            check_entry_label = f"{check_label}_entry"
            check_ok_label = f"{check_label}_ok"
            check_fail_label = f"{check_label}_fail"
        if suf_exist:
            check_suf_label = f"{check_label}_suf"
        if pre_exist:
            check_pre_label = f"{check_label}_pre"

        if dep_parent_label:
            # dashed lines shoe dependency
            lines.append(f"{dep_parent_label} -> {check_entry_label} [style=dashed]")
        if prev:
            lines.append(f"{prev} -> {check_entry_label} {prev_line_label}")

        if check_label in visited:
            return visited[check_label]

        if suf_exist:
            prev = check_suf_label
            for idx, cond in enumerate(check.ok_sufficient_conditions):
                cond_check_path, cond_status = Check.cond_parse(cond)
                cond_check_label = self.check_path_to_label(cond_check_path)
                lines.append(f'{cond_check_label} [label="{cond_check_path}"]')
                if idx == 0:
                    prev_line_label = ""
                else:
                    prev_line_label = '[label="N"]'
                lines.append(f"{prev}->{cond_check_label} {prev_line_label}")
                lines.append(f'{cond_check_label}->{check_ok_label} [label="Y"]')
                prev = cond_check_label
            lines.append(f'{prev}->{check_pre_label} [label="N"]')

        if pre_exist:
            prev = check_pre_label
            for idx, cond in enumerate(check.prerequisite_conditions):
                session.goto_obj(self.node.node_path)
                cond_check_path, cond_status = Check.cond_parse(cond)
                (cond_node_path, cond_check_name) = Check.check_path_parse(
                    cond_check_path
                )
                cond_check_label = self.check_path_to_label(cond_check_path)
                if idx == 0:
                    prev_line_label = ""
                else:
                    prev_line_label = '[label="Y"]'
                cond_check = session.goto_obj(
                    cond_check_path, obj_type=DiagObjType.Check
                )
                cond_check.decision_graph(
                    lines=lines,
                    visited=visited,
                    dep_parent_label=None,
                    prev=prev,
                    prev_line_label=prev_line_label,
                    level=level + 1,
                )
                prev = cond_check_label
            lines.append(f'{prev}->{check_label}_run [label="Y"]')

        # dep loop
        prev = check_fail_label
        dep_parent_label = check_fail_label
        prev_is_composite = False
        for idx, cond in enumerate(check.ok_necessary_conditions):
            session.goto_obj(self.node.node_path)
            (cond_check_path, cond_status) = Check.cond_parse(cond)
            (cond_node_path, cond_check_name) = Check.check_path_parse(cond_check_path)
            cond_check_label = self.check_path_to_label(cond_check_path)
            if idx == 0:
                if is_composite:
                    prev_line_label = ""
                else:
                    prev_line_label = '[label="N"]'
            else:
                if prev_is_composite:
                    prev_line_label = ""
                    prev = f"{prev}_ok"
                else:
                    prev_line_label = '[label="Y"]'
            cond_check = session.goto_obj(cond_check_path, obj_type=DiagObjType.Check)
            lines.append(
                f"# == level={level}, dep loop from {check.inst_name} to {cond_check_path}"
            )
            prev_is_composite = cond_check.decision_graph(
                lines=lines,
                visited=visited,
                dep_parent_label=dep_parent_label,
                prev=prev,
                prev_line_label=prev_line_label,
                level=level + 1,
            )
            prev = cond_check_label
        if len(check.ok_necessary_conditions):
            to_label = f"{check_fail_label}_no_failed_dep"
            to_text = f"[investigate]No failed dependency for {check_fail_label}"
            lines.append(f'{to_label} [label="{to_text}" shape=signature]')
            if prev_is_composite:
                lines.append(f"{prev}_ok->{to_label}")
            else:
                lines.append(f'{prev}->{to_label} [label="Y"]')
        if check.action_on_fail:
            to_label = f"{check_label}_on_fail"
            to_text = check.action_on_fail
            lines.append(f'{to_label} [label="{to_text}", shape=signature]')
            if (not len(check.ok_necessary_conditions)) and is_composite:
                lines.append(f"{prev}->{to_label}")
            elif prev_is_composite:
                lines.append(f"{prev}_fail->{to_label}")
            else:
                lines.append(f'{prev}->{to_label} [label="N"]')

        if level == 0:
            lines.append("}")
            # for line in lines:
            #    print(line)
            gen_graphviz(lines)

        visited[check_label] = is_composite
        return is_composite

    @staticmethod
    def cli_get_cmds():
        return ["show", "run", "triage", "check", "test"]

    @staticmethod
    def help_show():
        print(
            textwrap.indent(
                textwrap.dedent(
                    """
            show: show check info
            show cause: show conditions will can cause this check to fail.
            show consequence: show consequences when this check fails.
            show dep: alias to 'cause', because what it depends on are the 
                      failure causes
        """
                ),
                "  ",
            )
        )

    def cli_cmd(self, arg_cmd, cmd_args, tree=False, console_show=True):
        if arg_cmd == "show" and console_show: # to be cleaned up.
            if not len(cmd_args):
                self.show()
            elif cmd_args[0].startswith("dep") or cmd_args[0].startswith("cause"):
                self.show_deps()
            elif cmd_args[0].startswith("conseq"):
                self.show_consequences()
        elif arg_cmd == "run":
            ret = self.run(cmd_args)
            print(f"{self.node.node_path}:[check]{self.inst_name} = {ret}")
        elif arg_cmd == "dep_graph":
            self.node.dep_graph(self.inst_name, lines=[])
        elif arg_cmd == "decision_graph":
            stop()
            self.decision_graph(visited={}, lines=[])
        elif arg_cmd == "triage" or arg_cmd == "check":
            remediate = False
            if len(cmd_args) and cmd_args[0].startswith("rem"):
                remediate = True
            self.triage(remediate=remediate)
        elif arg_cmd == "test":
            if cmd_args[0] == "triage":
                if len(cmd_args) >= 2:
                    inject_str = cmd_args[1]
                else:
                    raise Exception("expecting cmd as: test triage <inject_condition>")
                self.test_triage(inject_str)
        else:
            raise Exception(f"Unknown command {arg_cmd}")

    @staticmethod
    def cond_extract_check_name(cond: str):
        (cond_check, cond_status) = Check.cond_parse(cond)
        (node_path, check_name) = Check.check_path_parse(cond_check)
        return check_name

    # get valid label for graphviz.  no : or . allowed.
    @staticmethod
    def cls_check_path_to_label(check_path: str):
        label = check_path.replace("[check]", "")
        label = label.replace(":", "_")
        label = label.replace(".", "_")
        label = label.replace("<", "_")
        label = label.replace(">", "_")
        return label

    @staticmethod
    def check_path_parse(check_path: str):
        m = re.match(r"^(?P<node_path>^(:)?\S+):(?P<check_name>\w*)", check_path)
        if not m:
            print(check_path)
            stop()
            raise Exception("invalid check_path")
        node_path = m.group("node_path")
        check_name = m.group("check_name")
        return (node_path, check_name)

    @staticmethod
    def cond_parse(cond: str):
        if not isinstance(cond, str):
            stop()
        m = re.match(r"(?P<cond_check>[^= ]+)\s*==\s*(?P<cond_status>.*)", cond)
        if not m:
            print(f"Invalid condition statement {cond}")
            stop()
            raise Exception
        cond_check = m.group("cond_check")
        cond_status = m.group("cond_status")
        return (cond_check, cond_status)

    def check_graph_internal(self, check_path, check_label):
        suf_exist = len(self.ok_sufficient_conditions) > 0
        pre_exist = len(self.prerequisite_conditions) > 0
        lines = []
        # lines.append(f'#\n-- inst_name={self.inst_name}, check_path={check_path}, check_label={check_label}')
        if suf_exist or pre_exist:
            lines.append(f"subgraph cluster_{check_label} {{")
            lines.append(f'label="{check_path}"')
            lines.append(f'{check_label}_entry [label="entry"]')
            lines.append(f'{check_label}_ok [label="OK"]')
            lines.append(f'{check_label}_run [label = "check.run()"]')
            lines.append(f'{check_label}_fail [label = "Fail"]')
            lines.append(f'{check_label}_run->{check_label}_ok [label="Y"]')
            lines.append(f'{check_label}_run->{check_label}_fail [label="N"]')
            if suf_exist:
                lines.append(f'{check_label}_suf [label="suff"]')
                lines.append(f"{check_label}_entry -> {check_label}_suf")
            if pre_exist:
                lines.append(f'{check_label}_pre [label="pre"]')
            if not suf_exist:
                lines.append(f"{check_label}_entry -> {check_label}_pre")

            lines.append("}")
        else:
            lines.append(f'{check_label} [label="{check_path}"]')
        # lines.append(f'# --> inst_name={self.inst_name}\n')
        return (suf_exist, pre_exist, lines)

    # dfs traverse and prints out the dependencies
    def show_deps(self, level=0, indent="", cause_dict=None):

        if level == 0:
            top_node = self.node.session.top_node
            cause_dict, consequence_dict = top_node.check_direct_deps_find()
            # for key in cause_dict:
            #    print(f"key={key}, deps={cause_dict[key]}")
            indent = "|--"

        session = self.node.session
        check_path = f"{self.node.node_path}:[check]{self.inst_name}"
        print(f"{indent}{check_path}")
        if check_path not in cause_dict:
            return
        deps = cause_dict[check_path]
        for dep in deps:
            check = session.goto_obj(dep, obj_type=DiagObjType.Check)
            check.show_deps(
                level=level + 1, indent=indent + "|--", cause_dict=cause_dict
            )

    # dfs traverse and prints out the consequences
    def show_consequences(self, level=0, indent="", consequence_dict=None):

        if level == 0:
            top_node = self.node.session.top_node
            cause_dict, consequence_dict = top_node.check_direct_deps_find()
            # for key in cause_dict:
            #    print(f"key={key}, deps={cause_dict[key]}")
            indent = "|--"

        session = self.node.session
        check_path = f"{self.node.node_path}:[check]{self.inst_name}"
        print(f"{indent}{check_path}")
        if check_path not in consequence_dict:
            return
        deps = consequence_dict[check_path]
        for dep in deps:
            check = session.goto_obj(dep, obj_type=DiagObjType.Check)
            check.show_consequences(
                level=level + 1,
                indent=indent + "|--",
                consequence_dict=consequence_dict,
            )

# A proc is a procedure to make a check condition happen.
class Proc:
    def __init__(
            self,
            init,           # a command as the initial step
            rept = None,    # a command as the intermediate steps
                            # running at an interval
            interval = 10   # the interval in seconds to run 'rept'
            ):
        self.init = init
        self.rept = rept
        self.interval = interval
