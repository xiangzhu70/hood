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

    def __init__(self, inst_name="", node_args=[]):
        self.inst_name = inst_name
        self.node_args = node_args
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
        self.commands = []
        self.checks = []
        self.depends = []

        # save initialized obj for fast lookup
        self.checks_dict = {}

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
            print(func_args)
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
                    raise Exception(f"Failed to resolve {arg}")
            args_str += f"{arg}='{val}', "
        if args_str.endswith(", "):
            args_str = args_str[:-2]
        classObj = None
        class_init_stmt = f"{class_name}({args_str})"
        try:
            classObj = eval(class_init_stmt)
        except:
            print(f"Failed in {class_init_stmt}")
            import pdb; pdb.set_trace()
        return classObj

    def sub_str_parse(self, sub_str):
        sub_name = None
        range_str = None
        inst = None
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
        if "gen_intf" in sub_str:
            import pdb; pdb.set_trace()
        (sub_name, range_str, inst) = self.sub_str_parse(sub_str)
        if inst:
            valid = self.sub_validate_instance(sub_name, inst)
            if not valid:
                import pdb; pdb.set_trace()
                raise(Exception("Not a valid instance"))

        node_class_name = "Node" + sub_name[0].upper() + sub_name[1:]
        if not globals().get(node_class_name):
            if (sub_name in self.map_sub_to_class):
                node_class_name = self.map_sub_to_class[sub_name]
            elif ("*" in self.map_sub_to_class):
                node_class_name = self.map_sub_to_class["*"]
            else:
                import pdb; pdb.set_trace()
                raise Exception(f"Cannot resolve class for {sub_name}")
        child = self.constructClassObj(node_class_name, inst_name=sub_str, input_dict=input_dict)
        if not child:
            raise(Exception(f"failed to construct a class obj for {sub_str}"))
        child.subs_dict_init()

        return child

    def show(self, cmd_args):
        print(cmd_args)
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

    def show_tree(self, tree_level, indent=""):
        indent+="|--"
        print(f"{indent}{self.inst_name}")
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
            sub_node = self.enter_sub_node(sub_str, input_dict=self.args_to_sub)
            sub_node.show_tree(tree_level, indent)

    def checks_init(self):
        for check_name in self.checks:
            if check_name in self.checks_dict:
                print(f"check <{check} already initialized.")
                continue
            check_class_name = self.map_check_to_class[check_name]
            check_obj = self.constructClassObj(check_class_name, inst_name=None)
            if not check_obj:
                raise Exception(f"Check {check_name} obj not constructed")
            self.checks_dict[check_name] = check_obj

    def check(self, cmd_args):
        print(cmd_args)
        if len(self.checks) and (not self.checks_dict):
            self.checks_init()

        if not len(cmd_args):       
            print("Run overall check")
            return
        check_name = cmd_args[0]
        found = False
        for check in self.checks:
            if check == check_name:
                found = True
                break
        if not found:
            print(f"{check_name} not found")
            return
        if len(cmd_args) < 2:
            self.run_check(check_name)
            return
        cmd = cmd_args[1]
        if cmd == "show":
            print(f"check_name={check_name}, cmd={cmd}")
            for check_name in self.checks:
                self.show_check(check_name)
            return

    def run_check(self, check_name):
        if check_name not in  self.checks_dict:
            print("Invalid check")
            return
        check_obj.run()

    def show_check(self, check_name):
        if check_name not in  self.checks_dict:
            print("Invalid check")
            return
        check_obj = self.checks_dict[check_name]
        check_obj.show()

if __name__ == "__main__":
    diag_node = NodeDiag(inst_name="diag")
    diag_node.show()
