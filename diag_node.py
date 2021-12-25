#!/usr/bin/env python3
import os
import inspect
import re

verbose = False

def import_node_file(node_module_name):
    if __package__:
        exec(f"from . import {node_module_name}", globals(), locals())
        exec(f"from {__package__}.{node_module_name} import *", globals(), locals())
    else:
        exec(f"import {node_module_name}", globals(), locals())
        exec(f"from {node_module_name} import *", globals(), locals())
    # importing only imports to func locals.  copy it to global so it can
    # be used outside of the function.
    globals()[node_module_name] = locals()[node_module_name]
    if node_module_name.startswith("node_"):
        node_module = eval(node_module_name)
        for key in dir(node_module):
            if key.startswith("Node") or key.startswith("Check"):
                globals()[key] = locals()[key]

def import_node_module(node_module_name):

    if verbose:
        print(f"Importing node_module {node_module_name}")
    import_node_file(f"node_{node_module_name}")
    #TBD remove impl_?
    impl_module_name = f"impl_{node_module_name}"
    if os.path.exists(impl_module_name + ".py"):
        import_node_file(impl_module_name)

class NodeDiag:

    map_sub_to_class = {}

    def __init__(self, inst_name=""):
        self.inst_name = inst_name
        self.node_args = {}
        # parent node, often the source of the structure information.
        self.parent = None
       
        # the local variables for the local cmd run environment.
        self.local_vars = []
        # the sub notes
        self.subs = []
        self.args_to_sub = {} 
        # functions needed?  could the class member functions acheive the purpose?
        # These are not exact python functions.  It is more a cmd helper to add
        # local variables for cmd excution.
        self.functions = []
        # Python inheritance is used for inheriting the structure (subs).
        # commands here do not implicitly inherit.
        self.cmds = []
        self.checks = []

        # save constructed children objects
        self.children_dict = {}

        # save initialized obj for fast lookup
        self.checks_dict = {}

        self.cmds_dict = {}

    def get_map_check_to_class(self):
        return {}

    def resolve_var(self, arg, input_dict):
        
        if arg in input_dict:
            return True, input_dict[arg]
        if arg in self.map_var_resolve:
            resolve_str = self.map_var_resolve[arg]
            if "self" in resolve_str:
                val = eval(resolve_str)
                return True, val
        #if arg in self.local_vars:
        #    return True, self.local_vars[arg]
        # TBD get from function.
        return False, None


    def call_func(self, func, input_dict = None):
        # find class name, get __init__ func, get parameters
        # resolve parameters.
        # eval class with (parameter values)
        if verbose:
            print(f"call_func: {func}")
        func_obj = eval(f"self.{func}")
        func_args = inspect.getargspec(func_obj)
        if verbose:
            print(func_args)
        args_str = ""
        for idx, arg in enumerate(func_args.args):
            if arg == "self":
                continue
            status, val = self.resolve_var(arg, input_dict)
            if (not status) and func_args.defaults:
                val = func_args.defaults[idx-1]
                if not val:
                    raise Exception(f"Failed to resolve {arg}")
            args_str += f"{arg}='{val}', "
        if args_str.endswith(", "):
            args_str = args_str[:-2]
        ret = None
        try:
            ret = eval(f"self.{func}({args_str})")
        except:
            import pdb; pdb.set_trace()
        return ret

    def constructClassObj(self, class_name, inst_name, input_dict = None):
        # find class name, get __init__ func, get parameters
        # resolve parameters.
        # eval class with (parameter values)
        if verbose:
            print(f"constructClassObj: {class_name}")
        init_func = eval(f"{class_name}.__init__")
        func_args = inspect.getargspec(init_func)
        if verbose:
            print(f"{class_name}.__init__ fucc_args: {func_args}")
        args_str = ""
        for idx, arg in enumerate(func_args.args):
            if arg == "self":
                continue
            if arg == "parent":
                args_str += "self, "
                continue
            if arg == "inst_name":
                args_str += f"'{inst_name}'" + ", "
                continue
            status, val = self.resolve_var(arg, input_dict)
            if (not status) and func_args.defaults:
                val = func_args.defaults[idx-1]
                if not val:
                    import pdb; pdb.set_trace()
                    raise Exception(f"Failed to resolve <{arg}>")
            args_str += f"{arg}='{val}', "
        if args_str.endswith(", "):
            args_str = args_str[:-2]
        classObj = None
        class_init_stmt = f"{class_name}({args_str})"
        try:
            classObj = eval(class_init_stmt)
        except:
            print(f"Failed in <{class_init_stmt}>")
            import pdb; pdb.set_trace()
        return classObj

    def sub_str_parse(self, sub_str):
        sub_name = None
        range_str = None
        inst = None
        if sub_str in self.map_sub_to_class:
            sub_name = sub_str
            return (sub_name, range_str, inst)
        # sub_name is before the first '['
        m = re.match(r"(?P<sub_name>[^\[]+)\[(?P<range_str>\S+)\]$", sub_str)
        if not m:
            m = re.match(r"(?P<sub_name>\S+)(?P<inst>\d+)$", sub_str)
            if m:
                # example: pim1
                sub_name = m.group("sub_name")
                inst = m.group("inst")
            else:
                sub_name = sub_str
        else:
            # range formats
            sub_name = m.group("sub_name")
            range_str = m.group("range_str")
            # Enter the group, not the instance.  In show_tree case.
            # example: pim[1..8]
            m = re.match("(?P<idx_start>\d+)\.\.(?P<idx_end>\d+)$", range_str)
            if m:
                idx_start = int(m.group("idx_start"))
                idx_end = int(m.group("idx_end"))
                # this range_str is ok, do nothing
            else:
                # func:<func>
                m = re.match(r"func:(?P<func>\S+)$", range_str)
                if m:
                     func = m.group("func")
                     range_str = self.call_func(func)
                     # update the sub_str with the output of the func
                     sub_str = f"{sub_name}[{range_str}]"
                # example: eth2/2/1, an inst with special char, wrapped with []
                elif ".." not in range_str:
                    inst = range_str
                    range_str = None
        return (sub_name, range_str, inst)

    def subs_dict_init(self):
        subs_dict = {}
        for sub_str in self.subs:
            (sub_name, range_str, inst) = self.sub_str_parse(sub_str)
            if inst:
                import pdb; pdb.set_trace()
                raise(Exception("Not expecting instance selection here"))
            subs_dict[sub_name] = range_str
        self.subs_dict = subs_dict

    def sub_validate_instance(self, sub_name, inst):
        range_str = self.subs_dict[sub_name]
        # TBD should be able to judge if eth2/1/1 fall into  eth[2..9]/[1..16]/1
        return True

    def enter_sub_node(self, sub_str, input_dict={}):
        (sub_name, range_str, inst) = self.sub_str_parse(sub_str)
        if not sub_name:
            import pdb; pdb.set_trace()
            raise Exception("Empty subname")
        if inst:
            valid = self.sub_validate_instance(sub_name, inst)
            if not valid:
                import pdb; pdb.set_trace()
                raise(Exception("Not a valid instance"))
        if sub_str in self.children_dict:
            # node visited before.  a child node object already present
            child = self.children_dict[sub_str]
            return child
        node_class_name = "Node" + sub_name[0].upper() + sub_name[1:]
        if not globals().get(node_class_name):
            if (sub_name in self.map_sub_to_class):
                node_class_name = self.map_sub_to_class[sub_name]
            elif ("*" in self.map_sub_to_class):
                node_class_name = self.map_sub_to_class["*"]
            else:
                print(f"sub_name={sub_name} missing from {self.inst_name}")
                import pdb; pdb.set_trace()
                print(f"sub_name={sub_name}")
                raise Exception(f"Cannot resolve class for {sub_name}")
        child = self.constructClassObj(node_class_name, inst_name=sub_str, input_dict=input_dict)
        if not child:
            raise(Exception(f"failed to construct a class obj for {sub_str}"))
        child.parent = self
        self.children_dict[sub_str] = child
        child.node_args = input_dict
        child.subs_dict_init()
        child.checks_init()

        return child

    
    def enter_node(self, node_path, input_dict={}):
        '''
        Enter node by path
        The formats are:
        .n1.n2 or n1.n2  relative to current node
        :top.n1.n2  go to domain top first.
        ../..n_parent
        '''
        curr = self
        if node_path == ".":
            return curr
        if node_path.startswith(":"):
            while curr.parent and (curr.parent.inst_name != "top"):
                curr = curr.parent
            node_path = node_path[1:] # remove ":"
        else:
            while node_path.startswith(".."):
                curr = curr.parent
                node_path = node_path[2:] # remove ".."
                # remove "/" used to separate ".."
                if node_path.startswith("/"):
                   node_path = node_path[1:]
        while node_path:
            fields = node_path.split(".", maxsplit=1)
            sub = fields[0]
            if len(fields) >= 2:
                node_path = fields[1] # remaining node path
            else:
                node_path = ""
            curr = curr.enter_sub_node(sub, input_dict=input_dict)
            if not curr:
               raise Exception(f"Failed to enter {sub}")
        return curr 
        

    def show_cmds(self):
        for cmd in self.cmds:
            print(cmd)

    def show(self, cmd_args):
        #print(cmd_args)
        if not len(cmd_args):       
            print(f"class name: {type(self).__name__}")
            print(f"NodeDiag inst {self.inst_name}")
            print(f"Subs:")
            print(self.subs)
            print("Checks")
            print(self.checks)
            return
        import pdb; pdb.set_trace()
        show_type = cmd_args[0]
        if show_type == "check":
            for check in self.checks:
               print(check)

    def show_tree(self, tree_level, indent="", show_type="node"):
        indent+="|--"
        print(f"{indent}{self.inst_name}")
        if show_type == "check":
            for check_name in self.checks:
                if check_name == "overall":
                    check_name_show = ""
                else:
                    check_name_show = check_name
                print(f"{indent}|--[check] {check_name_show}")
                check_obj = self.checks_dict[check_name]
                try:
                    conds = check_obj.ok_sufficient_conditions
                except:
                    print(f"sufficent, check_name={check_name}")
                    import pdb; pdb.set_trace()
                    pass
                for cond in conds:
                    print(f"{indent}|--|--[suf] {cond}")
                try:
                    conds = check_obj.prerequisite_conditions
                except:
                    print(f"pre, check_name={check_name}")
                    import pdb; pdb.set_trace()
                    pass
                for cond in conds:
                    print(f"{indent}|--|--[pre] {cond}")
                try:
                    conds = check_obj.ok_necessary_conditions
                except:
                    print(f"check_name={check_name}")
                    import pdb; pdb.set_trace()
                    pass
                for cond in conds:
                    print(f"{indent}|--|--[dep] {cond}")
        elif show_type == "cmd" or show_type == "command":
            for cmd_name in self.cmds:
                print(f"{indent}|--[cmd] {cmd_name}")
        if tree_level != -1:
            tree_level -= 1
            if tree_level == 0:
                return
        for sub in self.subs_dict:
            # subs list has the raw conf
            # subs_dict has the processed version, so func:.. is already
            # converted to the range string.
            sub_str = sub
            if self.subs_dict[sub]: # range_str not None
               sub_str += f"[{self.subs_dict[sub]}]"
            sub_node = self.enter_sub_node(
                sub_str, input_dict=self.args_to_sub)
            sub_node.show_tree(tree_level, indent, show_type=show_type)

    # much duplicated logic.  to be combined with check.  TBD
    def cmds_init(self):
        for cmd_name in self.cmds:
            if cmd_name in self.cmds_dict:
                print(f"cmd <{cmd_name} already initialized.")
                continue
            cmd_class_name = self.map_cmd_to_class[cmd_name]
            cmd_obj = self.constructClassObj(cmd_class_name, inst_name=None)
            if not cmd_obj:
                raise Exception(f"Command {cmd_name} obj not constructed")
            self.cmds_dict[cmd_name] = cmd_obj

    def cmd(self, cmd_args):
        print(cmd_args)
        if len(self.cmds) and (not self.cmds_dict):
            self.cmds_init()

        if not len(cmd_args):
            self.show_cmds()
            return

        cmd_name = cmd_args[0]

        if cmd_name == "remote":
            # test remote execution here
            path = cmd_args[1]
            self.remote_run(path)
 
            return

        if cmd_name not in self.cmds_dict:
            print(f"{cmd_name} not found")
            return

        if len(cmd_args) < 2:
            self.run_cmd(cmd_name)
            return

    def checks_init(self):
        for check_name in self.checks:
            if check_name in self.checks_dict:
                print(f"check <{check} already initialized.")
                continue
            check_class_name = "Check" + check_name[0].upper() + check_name[1:]
            if not globals().get(check_class_name):
                if hasattr(self, "map_check_to_class"):
                    check_map = self.map_check_to_class
                else:
                    check_map = self.get_map_check_to_class()
                if check_name in check_map:
                    check_class_name = check_map[check_name]
                else:
                    import pdb; pdb.set_trace()
                    raise Exception(f"cannot find check class for <{check_name}>")
            check_obj = self.constructClassObj(check_class_name, inst_name=check_name)
            if not check_obj:
                raise Exception(f"Check {check_name} obj not constructed")
            self.checks_dict[check_name] = check_obj

    def check(self, cmd_args):
        #print(cmd_args)
        if len(self.checks) and (not self.checks_dict):
            self.checks_init()

        if not len(cmd_args):       
            print("Run overall check")
            return
        
        if cmd_args[0] == "state_machine":
            self.decision_state_machine_graph()
            return

        check_name = cmd_args[0]
        if check_name not in self.checks_dict:
            print(f"{check_name} not found")
            return
        if len(cmd_args) < 2:
            self.run_check(check_name)
            return
        cmd = cmd_args[1]
        print(f"check_name={check_name}, cmd={cmd}\n\n")
        if cmd == "show":
            self.show_check(check_name)
            return
        elif cmd == "graph":
            #self.check_dep_graph(check_name)
            self.decision_graph(f".:{check_name}")

    def run_check(self, check_name):
        if len(self.checks) and (not self.checks_dict):
            self.checks_init()
        if not check_name:
            check_name = "overall"
        if check_name not in self.checks_dict:
            print(f"run_check at node {self.parent.inst_name}: invalid check {check_name}")
            return
        check_obj = self.checks_dict[check_name]
        check_obj.run()

    def show_check(self, check_name):
        if check_name not in  self.checks_dict:
            print("Invalid check")
            return
        check_obj = self.checks_dict[check_name]
        check_obj.show()

    def run(self, target:str):
        '''
        target string could be [cmd]<cmd_name> or [check]<check_name>
        [check]<empty> means [check]overall".
        '''
        m = re.match("\[(?P<target_type>\w+)\](?P<target_name>\w*)", target)
        if not m:
            raise Exception("node run: invalid target <{target}>")
        target_type = m.group("target_type")
        target_name = m.group("target_name")
        # TBD combine cmd and check
        if target_type == "check":
            self.run_check(target_name)
        elif target_type == "cmd":
            self.run_cmd(target_name)

    def remote_run(self, path:str):
        print(f"remote_run: path={path}")
        m = re.match(r"(?P<node_path>.*):(?P<run_target>[^: ]+)", path)
        if not m:
            raise Exception(f"remote_run, invalid path <{path}>")
        node_path = m.group("node_path")
        run_target = m.group("run_target")
        remote_node = self.enter_node(node_path, self.node_args)
        import pdb; pdb.set_trace()
        remote_node.run(run_target)

    def triage(self, check_name : str):

        print(f"Check {check.name} triage")
        check = self.checks_dict[check_name]
        ret = check.run()
        if ret == "OK":
            print("check returned OK, no issue to further triage")
            return
        if len(check.ok_necessary_conditions) == 0:
            print("check failed. no dependency to further check")
            return
        for cond in check.ok_necessary_conditions:
            m = re.match(r"(?P<cond_check>[^=]+)==(?P<cond_status>.*)", cond)
            if not m:
                print(f"Invalid condition statement {cond}")
                continue
            cond_check = m.group("cond_check") 
            cond_status_expect = m.group("cond_status")
            remote_node, check_ret = self.remote_run(cond_check)
            if check_ret == cond_status_expect:
                continue
            remote_check_obj.triage()

    def check_dep_graph(self, check_name:str, parent_name=None, lines=[], level=0):
        #print(f"Check {check_name} dep_graph")
        if not check_name:
            check_name = "overall"
        if not len(self.checks_dict):
            self.checks_init() #TBD
        if check_name not in self.checks_dict:
             print(f"<{check_name}> not found for {self.inst_name}")
             import pdb; pdb.set_trace()
             raise Exception("Invalid check")
        check = self.checks_dict[check_name]
        #print(f"Check name: {check.name}")
        if len(lines) == 0:
            lines.append("digraph {")
            lines.append("node [shape=Rectangle]")
            level = 0
            parent_name = check_name
        for cond in check.ok_necessary_conditions:
            (cond_check, cond_status) = Check.cond_parse(cond)
            lines.append(f'"{parent_name}"->"{cond_check}"')
            (node_path, cond_check_name) = Check.check_path_parse(cond_check)
            remote_node = self.enter_node(node_path, input_dict=self.node_args)
            remote_node.check_dep_graph(cond_check_name, parent_name=cond_check, lines=lines, level=level+1)
            
        if level == 0:
            lines.append("}")
            for line in lines:
                print(line)

    # get valid label for graphviz.  no : or . allowed.
    def check_path_to_label(self, check_path: str):
        if check_path.startswith(".:"):
            # it could be too short and having naming conflicts
            check_path = self.inst_name + "." + check_path
        return Check.check_path_to_label(check_path)

    def decision_graph(self, check_path:str, dep_parent_label=None, prev=None, prev_line_label=None, lines=[], level=0, visited = {}):
        # self is the node.

        #print(f"Check {check_name} dep_graph")
        (node_path, check_name) = Check.check_path_parse(check_path)
        check_label = self.check_path_to_label(check_path)
        if not check_name:
            check_name = "overall"
        if not len(self.checks_dict):
            self.checks_init() #TBD
        if check_name not in self.checks_dict:
             print(f"<{check_name}> not found for {self.inst_name}")
             import pdb; pdb.set_trace()
             raise Exception("Invalid check")
        check = self.checks_dict[check_name]

        if level == 0:
            lines.append("digraph {")
            lines.append("node [shape=Rectangle]")
            visited = {}

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
                lines.append(f"{dep_parent_label} -> {check_entry_label} [style=dashed]")
            if prev:
                lines.append(f"{prev} -> {check_entry_label} {prev_line_label}")
            return visited[check_label]
            
        (suf_exist, pre_exist, internal_lines) = check.check_graph_internal(check_path, check_label)
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
                lines.append(f'{prev}->{cond_check_label} {prev_line_label}')
                lines.append(f'{cond_check_label}->{check_ok_label} [label="Y"]')
                prev = cond_check_label
            lines.append(f'{prev}->{check_pre_label} [label="N"]')

        if pre_exist:
            prev  = check_pre_label
            for idx, cond in enumerate(check.prerequisite_conditions):
                cond_check_path, cond_status = Check.cond_parse(cond)
                (cond_node_path, cond_check_name) = Check.check_path_parse(cond_check_path)
                cond_check_label = self.check_path_to_label(cond_check_path)
                if idx == 0:
                    prev_line_label = ""
                else:
                    prev_line_label = '[label="Y"]'
                remote_node = self.enter_node(cond_node_path, input_dict=self.node_args)
                remote_node.decision_graph(
                    cond_check_path, dep_parent_label=None, prev=prev, prev_line_label=prev_line_label, lines=lines, level=level+1)
                prev = cond_check_label
            lines.append(f'{prev}->{check_label}_run [label="Y"]')
        
        # dep loop    
        prev = check_fail_label
        dep_parent_label = check_fail_label
        prev_is_composite = False
        for idx, cond in enumerate(check.ok_necessary_conditions):
             (cond_check_path, cond_status) = Check.cond_parse(cond)
             (cond_node_path, cond_check_name) = Check.check_path_parse(cond_check_path)
             cond_check_label = self.check_path_to_label(cond_check_path)
             if idx == 0:
                 if is_composite:
                     prev_line_label = ''
                 else:
                     prev_line_label = '[label="N"]'
             else:
                 if prev_is_composite:
                     prev_line_label = ''
                     prev = f"{prev}_ok"
                 else:
                     prev_line_label = '[label="Y"]'
             remote_node = self.enter_node(cond_node_path, input_dict=self.node_args)
             lines.append(f'# == level={level}, dep loop from {check.inst_name} to {cond_check_path}')
             prev_is_composite = remote_node.decision_graph(cond_check_path, dep_parent_label=dep_parent_label, prev=prev, prev_line_label=prev_line_label, lines=lines, level=level+1)
             prev = cond_check_label
        if len(check.ok_necessary_conditions):
            to_label = f"{check_fail_label}_no_failed_dep"
            to_text = f"[investigate]No failed dependency for {check_fail_label}"
            lines.append(f'{to_label} [label="{to_text}" shape=signature]')
            if prev_is_composite:
                lines.append(f'{prev}_ok->{to_label}')
            else:
                lines.append(f'{prev}->{to_label} [label="Y"]')
        if check.action_on_fail:
            to_label = f"{check_label}_on_fail"
            to_text = check.action_on_fail
            lines.append(f'{to_label} [label="{to_text}", shape=signature]')
            if (not len(check.ok_necessary_conditions)) and is_composite:
                lines.append(f'{prev}->{to_label}')
            elif prev_is_composite:
                lines.append(f'{prev}_fail->{to_label}')
            else:
                lines.append(f'{prev}->{to_label} [label="N"]')

        if level == 0:
            lines.append("}")
            for line in lines:
                print(line)

        visited[check_label] = is_composite
        return is_composite

    def decision_state_machine_graph(self):
        print("digraph {")
        print("node [shape=Rectangle]")
        print('entry [label="Entry"]')
        print('ok [label="OK"]')
        print('fail [label="FAIL"]')
        print('suf [label="sufficient conditions"]')
        print('pre [label="prerequisite conditions"]')
        print('pre_recurse [label="recurse into failed prerequisite check"]')
        print('run [label="check.run()"]')
        print('dep [label="dependencies"]')
        print('dep_recurse [label="recurse into failed dependency"]')
        print('root_cause [label="[root_cause]<cause message>"]')
        print('investigate [label="[investigate]No failed dependency.  Unknown cause"]')
        print('entry -> suf')
        print('suf -> ok [label="Y"]')
        print('suf -> pre [label="N"]')
        print('pre -> run [label="Y"]')
        print('pre -> pre_recurse [label="N"]')
        print('run -> ok [label="Y"]')
        print('run -> fail [label="N, no dep"]')
        print('run -> dep [label="N"]')
        print('dep -> dep_recurse [label="N"]')
        print('dep_recurse -> root_cause [label="N"]')
        print('dep -> investigate [label="Y"]')
        print("}")
        
if __name__ == "__main__":
    diag_node = NodeDiag(inst_name="diag")
    diag_node.show()
