#!/usr/bin/env python3
import os
import textwrap
from collections import deque
from pdb import set_trace as stop

from hood.diag_check import Check
from hood.diag_obj import DiagObj, DiagObjType
from hood.diag_utils import (
    Instances,
    group_str_parse,
    gen_graphviz,
    NameStyle,
)

verbose = False


class TraverseTreePlugin:
    def run_at_node(self, node, indent):
        pass


class FindAttr(TraverseTreePlugin):
    def __init__(self, key, key_container=None, show=False, attr_run=None):
        self.key = key
        if not key_container:
            key_container = key + "s"
        self.key_container = key_container
        self.show = show
        self.entry_val_default = None
        self.found = {}
        self.attr_run = attr_run

    def run_at_node(self, node, indent):
        if hasattr(node, self.key_container):
            for item in node.__dict__[self.key_container]:
                item_path = f"{node.node_path}:[{self.key}]{item}"
                self.found[item_path] = self.entry_val_default
                if self.show:
                    print(f"{indent}|--[{self.key}] {item}")
                if self.attr_run:
                    self.attr_run(node, item, indent)


class FindCheckDepPlugin(TraverseTreePlugin):
    def __init__(
        self,
        cause_dict=None,  # val cause key
        consequence_dict=None,  # val depends on key, is consequence of key
        show=False,
    ):
        self.key = "check"
        self.key_container = "checks"
        self.cause_dict = cause_dict
        self.consequence_dict = consequence_dict
        self.show = show

    def add_into_dict(self, cause, consequence):
        if True:
            if consequence not in self.cause_dict:
                self.cause_dict[consequence] = [cause]
            else:
                self.cause_dict[consequence].append(cause)
        if True:
            if cause not in self.consequence_dict:
                self.consequence_dict[cause] = [consequence]
            else:
                self.consequence_dict[cause].append(consequence)

    def run_at_node(self, node, indent):
        session = node.session
        if hasattr(node, self.key_container):
            for item in node.__dict__[self.key_container]:
                check = getattr(node, item)
                check_path = f"{node.node_path}:[check]{item}"
                for cond in check.ok_necessary_conditions:
                    session.goto_obj(node.node_path)
                    (cond_check, cond_status) = Check.cond_parse(cond)
                    session.obj_path.move(
                        cond_check, obj_type=DiagObjType.Check)
                    self.add_into_dict(
                        cause=session.obj_path.path, consequence=check_path
                    )


class NodeDiag(DiagObj):

    map_sub_to_class = {}
    map_cmd_to_class = {}
    map_check_to_class = {}

    import_path_class_type_append = "node_diag"

    def __init__(self, context_node, inst_name, node_file_path, import_path):
        node_parent = context_node
        if node_parent:
            self.session = node_parent.session
            parent_path = node_parent.node_path
            if parent_path != ":":
                parent_path += "."
            self.node_path = parent_path + inst_name

        else:
            self.node_path = ":"

        self.inst_name = inst_name
        # parent node, often the source of the structure information.
        self.node_parent = node_parent

        self.node_file_path = node_file_path
        self.import_path = import_path

        # This legit obj names (cmds, checks etc) will be cached here.
        self.obj_names_dict = {}

        # self.map_sub_to_class = {}
        # self.map_cmd_to_class = {}
        # self.map_check_to_class = {}

        # By default, this is True except the top empty node,
        # so the hierarchy structures
        # (subs, cmds, checks) are derived from the files.
        # In more complicated cases such as structure changes for
        # inherited classes, muliple elements, set auto_cfg to False,
        # in init(), and explicitly set (subs, cmds, checks)
        self.auto_cfg = node_parent is not None

        # ownership if each node is clearly defined
        # if it is empty, the ownership should be inherited from
        # the hierarchical parents
        self.owners = []

        # the sub nodes
        self.subs = []
        # commands here do not implicitly inherit.
        self.cmds = []
        # the diag checks
        self.checks = []

        # Run customized init for the diag nodes if init is overridden
        self.init()

        self.post_init()

    # To be overridden
    def init(self):
        pass

    def post_init(self):
        if self.auto_cfg:
            self.cfg_by_files()

        self.objs_dicts_init()

    def cfg_by_files(self):
        # support cmds and checks, but not subs for now
        map_class_to_obj_names = {}
        map_obj_to_class = {}
        map_obj_to_class.update(self.map_cmd_to_class)
        map_obj_to_class.update(self.map_check_to_class)
        map_obj_to_class.update(self.map_sub_to_class)
        for obj in map_obj_to_class:
            class_name = map_obj_to_class[obj]
            map_class_to_obj_names[class_name] = obj

        # for sub nodes
        if False:
            # for now.  disable it.  listdir shows directory in random order.
            # better to control the order explicitly
            print(f"listdir: {os.listdir(self.node_file_path)}")
            for f in os.listdir(self.node_file_path):
                sub_path = os.path.join(self.node_file_path, f)
                if os.path.isdir(sub_path):
                    if os.path.exists(os.path.join(sub_path, "node_diag.py")):
                        self.subs.append(f)

        # for commands and checks
        for (obj_type, objs_list) in [
            (DiagObjType.Command, self.cmds),
            (DiagObjType.Check, self.checks),
        ]:
            if not self.check_obj_file_exists(obj_type):
                continue
            import_path = f"{self.import_path}.{obj_type.name.lower()}s"
            import_path = f"{self.session.import_path_prefix}{import_path}"
            obj_class_names = DiagObj.module_get_obj_class_names(
                import_path, obj_type)
            for (class_name, obj_name) in obj_class_names:
                if class_name in map_class_to_obj_names:
                    # The auto-discovered class is already statically declared
                    continue
                objs_list.append(obj_name)

    def objs_dicts_init(self):

        # constructed objects will be saved here for fast lookup
        self.objs_dict = {}

        self.sub_groups = {}

        # At init time, set up the names dict, so they are legit to access
        # when needed.  The objects will be constructed when being accessed
        # in __getattr__
        for sub_name in self.subs:
            if sub_name in self.map_sub_to_class:
                sub_type_name = sub_name
                range_str = None
                inst = None
            else:
                (sub_type_name, range_str, inst) = group_str_parse(sub_name)

            if range_str:
                self.sub_groups[sub_type_name] = range_str
            self.obj_names_dict[sub_type_name] = DiagObjType.Node
        for cmd_name in self.cmds:
            self.obj_names_dict[cmd_name] = DiagObjType.Command
        for check_name in self.checks:
            self.obj_names_dict[check_name] = DiagObjType.Check

    def construct_class_obj(self, module_path, class_name, class_type, inst_name):
        import_path = f"{self.session.import_path_prefix}{module_path}"
        classObj = DiagObj.constrct_obj(
            self, import_path, class_name, class_type, inst_name
        )
        return classObj

    def sub_validate_instance(self, sub_name, inst):
        # range_str = self.subs_dict[sub_name]
        # TBD should be able to judge if eth2/1/1 fall into  eth[2..9]/[1..16]/1
        return True

    # sub_name examples:
    # pim[1-8]  => sub_name=pim, inst=[1-8],
    # pim2
    # sub_node_path += sub_str, node_module_name += sub_name
    def enter_sub_node(self, sub_name):

        if sub_name in self.map_sub_to_class:
            sub_type_name = sub_name
            range_str = None
            inst = None
        else:
            (sub_type_name, range_str, inst) = group_str_parse(sub_name)
        if not sub_type_name:
            stop()
            raise Exception("Empty sub type name")
        if inst:
            valid = self.sub_validate_instance(sub_type_name, inst)
            if not valid:
                import pdb

                pdb.set_trace()
                raise (Exception("Not a valid instance"))
        sub_obj = self.__get_class_obj(
            DiagObjType.Node, sub_type_name, inst_name=sub_name
        )
        os.chdir(sub_obj.node_file_path)

        self.session.curr_node = sub_obj
        return sub_obj

    def show_summary(self):
        show_dict = {}
        print(f"class name: {type(self).__name__}")
        print(f"inst_name: {self.inst_name}")
        print(f"node_path: {self.node_path}")
        print(f"node file path: {self.node_file_path}")
        if hasattr(self, "info"):
            print(f"Info: {self.info}")
        self.show_subs()
        self.show_cmds()
        self.show_checks()
        show_dict["inst_name"] = self.inst_name
        show_dict["node_path"] = self.node_path
        show_dict["cmds"] = self.cmds
        show_dict["checks"] = self.checks
        return show_dict

    def show_subs(self):
        print("--Sub nodes:")
        for sub in self.subs:
            print(sub)

    def show_checks(self):
        print("--Checks")
        for check in self.checks:
            print(f"  {check}")

    def show_cmds(self):
        print("--Commands")
        for cmd in self.cmds:
            print(f"  {cmd}")

    def show(self, cmd_args):
        # print(cmd_args)
        if not len(cmd_args):
            return self.show_summary()

        else:
            print(cmd_args)
            if (cmd_args[0]) == "check":
                return self.show_checks()
            elif (cmd_args[0]) == "cmd":
                return self.show_cmds()

    def traverse_tree(
        self,
        tree_level=0,
        tree_level_max=-1,
        plugin=None,
        indent="",
        show_node=False,
        expand_group=False,
    ):
        indent += "|--"
        tree_dict = {}
        if show_node:
            print(f"{indent}{self.inst_name}")
        tree_dict["name"] = self.inst_name
        tree_dict["node_path"] = self.node_path
        tree_dict["children"] = []
        if plugin:
            plugin.run_at_node(node=self, indent=indent)
        if tree_level_max != -1:
            if tree_level >= tree_level_max:
                return
        for sub in self.subs:
            if not expand_group or (sub not in self.sub_groups):
                sub_node = self.enter_sub_node(sub)
                child_dict = sub_node.traverse_tree(
                    tree_level=tree_level + 1,
                    tree_level_max=tree_level_max,
                    plugin=plugin,
                    indent=indent,
                    show_node=show_node,
                )
                tree_dict["children"].append(child_dict)
            else:
                sub_type, range_str = self.sub_groups[sub]
                instances = Instances(sub_type, range_str, context=self)
                for inst in instances:
                    sub_node = self.enter_sub_node(inst)
                    sub_node.traverse_tree(
                        tree_level=tree_level + 1,
                        tree_level_max=tree_level_max,
                        plugin=plugin,
                        indent=indent,
                        show_node=show_node,
                    )

        if tree_level == 0:
            self.session.goto_obj(self.node_path)

        return tree_dict

    def find_attr(self, attr, show_node=False, show=False):
        plugin = FindAttr(attr, show=show)
        self.traverse_tree(0, plugin=plugin, show_node=show_node)
        return plugin.found

    def show_tree(self, show_type=None, tree_level_max=-1):
        if not tree_level_max:
            tree_level_max = -1

        def attr_check_run(node, check_name, indent):
            if check_name == "overall":
                check_name_show = ""
            else:
                check_name_show = check_name
            print(f"{indent}|--[check] {check_name_show}")
            check = getattr(node, check_name)
            conds = check.ok_sufficient_conditions
            for cond in conds:
                print(f"{indent}|--|--[suf] {cond}")
            conds = check.prerequisite_conditions
            for cond in conds:
                print(f"{indent}|--|--[pre] {cond}")
            conds = check.ok_necessary_conditions
            for cond in conds:
                print(f"{indent}|--|--[dep] {cond}")

        if show_type == "check":
            attr_show = False
            attr_run = attr_check_run
        else:
            attr_show = True
            attr_run = None

        if show_type == "node":
            plugin = None
        else:
            plugin = FindAttr(show_type, show=attr_show, attr_run=attr_run)
        tree_dict = self.traverse_tree(
            0, plugin=plugin, show_node=True, tree_level_max=tree_level_max
        )

        return tree_dict

    def check_obj_file_exists(self, obj_type):
        map_obj_type_to_file = {
            DiagObjType.Check: "checks.py",
            DiagObjType.Command: "commands.py",
            # need to search in sub directories. a different work flow.
            # DiagObjType.Node: "node_diag.py",
        }
        if obj_type not in map_obj_type_to_file:
            raise Exception("unknown obj_type")
        file = map_obj_type_to_file[obj_type]
        file_path = f"{self.node_file_path}/{file}"
        return os.path.exists(file_path)

    def obj_name_to_class_name(self, class_type, obj_name):
        obj_class_name = None
        if class_type == DiagObjType.Node:
            name_map_obj_to_class = "map_sub_to_class"
        else:
            name_map_obj_to_class = f"map_{class_type.value.lower()}_to_class"
        map_obj_name_to_class = getattr(self, name_map_obj_to_class)
        if obj_name in map_obj_name_to_class:
            obj_class_name = map_obj_name_to_class[obj_name]
        if not obj_class_name:
            obj_class_name = class_type.name + \
                NameStyle.underscore_to_camel(obj_name)
        return obj_class_name

    def __getattr__(self, attr_name):
        if attr_name in ["info"]:
            return None
        if attr_name not in self.obj_names_dict:
            # if not attr_name.startswith("map_"):
            print(
                f"attr_name <{attr_name}> not in {self.inst_name} obj_names_dict")
            # stop()
            raise AttributeError
        obj = self.__get_class_obj(self.obj_names_dict[attr_name], attr_name)
        if not obj:
            print("failed to set up <{attr_name}> obj")
            raise AttributeError
        # TBD looks hacky, should be removed?
        print(f"xxx set up <{attr_name}> for <{self.inst_name}>")
        setattr(self, attr_name, obj)
        return obj

    def get_import_path(
        self,
        class_type,
        obj_name="",  # for Node type only
        inst_name="",
    ):
        node_path = self.node_path
        import_path = self.import_path
        sub_dir = ""
        sub_node_import_path = ""

        if class_type == DiagObjType.Node:
            sub_dir = os.path.join(self.node_file_path, obj_name)
            if not os.path.isdir(sub_dir):
                # other configuation to be supported.
                err_msg = f"sub direcotry {sub_dir} not found"
                print(err_msg)
                stop()
                raise Exception(err_msg)
            if node_path == ":":
                sub_node_import_path = import_path + obj_name
            else:
                # example case: obj_name = pim, inst_name = pim1
                sub_node_import_path = import_path + "." + obj_name
            import_path = sub_node_import_path + ".node_diag"
        elif class_type == DiagObjType.Command:
            import_path += ".commands"
        elif class_type == DiagObjType.Check:
            import_path += ".checks"
        import_path = f"{self.session.import_path_prefix}{import_path}"
        return import_path, sub_dir, sub_node_import_path

    # For node, it is possible to have multiple instances.  In that case,
    # obj_name is the object type name, and inst_name is the full name.
    # For example, for PIMs in range [1..8], the object_name is "pim",
    # the inst name could be pim2, or the full group pim[1..8].
    def __get_class_obj(self, class_type, obj_name, inst_name=None):

        if not inst_name:
            inst_name = obj_name
        if self.inst_name != "top" and obj_name not in self.obj_names_dict:
            stop()
            raise AttributeError

        objs_dict = self.objs_dict
        if inst_name in objs_dict:
            return objs_dict[inst_name]

        import_path, sub_dir, sub_node_import_path = self.get_import_path(
            class_type, obj_name=obj_name
        )
        obj_class_name = self.obj_name_to_class_name(class_type, obj_name)

        class_obj = DiagObj.construct_obj(
            self,
            import_path,
            obj_class_name,
            inst_name=inst_name,
            node_file_path=sub_dir,
            import_path=sub_node_import_path,
        )
        if not class_obj:
            raise Exception(
                f"{class_type.name} {obj_name} obj not constructed")
        objs_dict[inst_name] = class_obj
        return class_obj

    def run_cmd(self, cmd):
        cmdObj = getattr(self, cmd)
        # for prerequisite in cmdObj.prerequisite_conditions:
        #    pass
        return cmdObj.run()

    def run_check(self, check):
        checkObj = getattr(self, check)
        return checkObj.run()

    def remote_run(self, path: str):
        curr_obj = self.session.goto_obj(path)
        ret = curr_obj.run()
        # after remote run, go back to the original node
        self.session.goto_obj(self.node_path)
        return ret

    # Find all direct depending checks and build the dict
    def check_direct_deps_find(self):

        cause_dict = {}
        consequence_dict = {}
        self.session.goto_obj(self.node_path)
        plugin = FindCheckDepPlugin(cause_dict, consequence_dict)
        self.traverse_tree(0, plugin=plugin)
        return (cause_dict, consequence_dict)

    def check_dependents_find(self, check_name):
        top_node = self.session.top_node
        cause_dict, consequence_dict = top_node.check_direct_deps_find()

        check_path = f"{self.node_path}:[check]{check_name}"
        check_all_dependents = []
        que = deque()
        que.append(check_path)
        while que:
            check = que.popleft()
            check_all_dependents.append(check)
            if check in consequence_dict:
                for dep_check in consequence_dict[check]:
                    que.append(dep_check)
        return check_all_dependents

    def dep_graph(self, check_name: str, lines, parent_name=None, level=0):
        session = self.session
        # print(f"Check {check_name} dep_graph")
        if not check_name:
            check_name = "overall"
        check = getattr(self, check_name)
        # print(f"Check name: {check.name}")
        if level == 0:
            lines.append("digraph {")
            lines.append("node [shape=Rectangle]")
            parent_name = check_name
        for cond in check.ok_necessary_conditions:
            (cond_check_path, cond_status) = Check.cond_parse(cond)
            lines.append(f'"{parent_name}"->"{cond_check_path}"')
            session.goto_obj(cond_check_path)
            session.curr_node.dep_graph(
                session.obj_path.obj_name,
                lines=lines,
                parent_name=cond_check_path,
                level=level + 1,
            )

        if level == 0:
            lines.append("}")
            gen_graphviz(lines)

    def add_obj(self, obj_type, obj_name):
        src_prefix = os.path.expanduser(f"{self.session.src_file_path_prefix}")
        node_file_path = self.node_file_path.replace(
            self.session.top_node.node_file_path, ""
        )
        if obj_type not in [key.value for key in DiagObjType]:
            raise Exception("invalid type to add")
        type_name = DiagObjType(obj_type).name
        file_name = f"{type_name.lower()}s.py"
        if obj_type == "node":
            sub_dir_name = f"{src_prefix}{node_file_path}/{obj_name}"
            if os.path.exists(sub_dir_name):
                raise Exception("the sub node directory already exists")
            os.mkdir(sub_dir_name)
            src_file_path = f"{sub_dir_name}/node_diag.py"
        else:
            src_file_path = f"{src_prefix}{node_file_path}/{file_name}"
        class_name = type_name + NameStyle.underscore_to_camel(obj_name)
        print(f"add {obj_type} {obj_name} at {src_file_path}, class {class_name}")
        import_prefix = self.session.import_path_prefix
        if obj_type == "node":
            head_str = (
                f"from {import_prefix}diag.diag_{obj_type} import {type_name}Diag"
            )
            is_new_file = True
            class_def_str = textwrap.dedent(
                f"""
                class {class_name}({type_name}Diag):
                    pass
                """
            )
        else:
            head_str = f"from {import_prefix}diag.diag_{obj_type} import {type_name}"
            return_stmt = {"cmd": "", "check": 'return "FAIL"'}
            class_def_str = textwrap.dedent(
                f"""\n
                class {class_name}({type_name}):
                    def run(self, cmd_args):
                        print(f"--> Entering {{self.check_path}} run()")
                        print(
                            "    ** file path: {self.session.src_file_path_prefix}{node_file_path}/{file_name}")
                        print(
                            "    ** This is a stub.  Add the real implementation here")
                        {return_stmt[obj_type]}
            """
            )
            is_new_file = not os.path.exists(src_file_path)
        with open(src_file_path, "a") as f:
            if is_new_file:
                f.write(head_str + "\n\n")
            f.write(class_def_str)

        print(f"Added {self.node_path}:[{obj_type}]{obj_name}")

    def cli_get_cmds(self):
        return ["show", "run", "find"]

    def cli_cmd(self, arg_cmd, cmd_args, tree_depth=-1):
        ret = None
        if arg_cmd == "show":
            return self.show(cmd_args)
        elif arg_cmd == "tree":
            if len(cmd_args) and cmd_args[0] in ["node", "check", "cmd"]:
                show_type = cmd_args[0]
            else:
                show_type = "node"
            return self.show_tree(show_type=show_type,
                                  tree_level_max=tree_depth)
        elif arg_cmd == "run":
            obj_type = cmd_args[1]
            obj_name = cmd_args[2]
            if obj_type == "check":
                ret = self.run_check(obj_name)
                print("ret = {ret}")
            elif obj_type == "cmd":
                ret = self.run_cmd(obj_name)
        elif arg_cmd == "find":
            if not len(cmd_args):
                raise Exception("Nothing to be found")
            obj_type = cmd_args[0]
            found = self.find_attr(obj_type)
            for key in found:
                print(f"{key}: {found[key]}")

        elif arg_cmd == "add":
            if len(cmd_args) < 2:
                raise Exception(
                    "Expecting input add [cmd|check|sub] <obj_name>")
            obj_type = cmd_args[0]
            if obj_type == "sub":
                obj_type = "node"
            obj_name = cmd_args[1]
            ret = self.add_obj(obj_type, obj_name)
            return ret
