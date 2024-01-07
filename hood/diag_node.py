#!/usr/bin/env python3
import os
import re
import textwrap
from collections import deque
from pdb import set_trace as stop

from hood.diag_check import Check
from hood.diag_obj import DiagObj, DiagObjType
from utils.diag_utils import (
    Instances,
    group_str_parse,
    gen_graphviz,
    NameStyle,
)

verbose = False


# Thoughts on tree traversing.  it is getting over complicated.  need rethinking
# there are a few operations requiring traversing the tree.
# the original intention is to factor our the common traversing part, use
# the callback/plugin to specify run_at_node
# usages are:
# 1.  show tree
#   in this case, the node position should be printed
# 2.  search tree, find an obj of some type, can then do something on it (another callback)
#   in this case, the node position should not be printed
# a run_at_node callback looks reasonable.  but dont further complicates the logic
# with more callbacks.

class AtNodePlugin:
    def run_at_node(self, node, indent):
        pass

class AtNodeShow(AtNodePlugin):
    def __init__(self, node, show_func):
        self.node = node
        self.run_at_node = show_func

class AtNodeFindCheckDep(AtNodePlugin):
    def __init__(
        self,
        cause_dict=None,  # val cause key
        consequence_dict=None,  # val depends on key, is consequence of key
        show=False,
    ):
        self.cause_dict = cause_dict
        self.consequence_dict = consequence_dict
        self.show = show

    # key -> list[]
    # cause_dict: consequnce -> [causes]
    # consequence_dict: cause -> [consequences]
    def add_into_dep_maps(self, cause, consequence):
        if consequence not in self.cause_dict:
            self.cause_dict[consequence] = []
        self.cause_dict[consequence].append(cause)
        if cause not in self.consequence_dict:
            self.consequence_dict[cause] = []
        self.consequence_dict[cause].append(consequence)

    # Follow ok_necessary_conditions (ie, depencencies, or deps)
    # build the causes and consequences dicts.
    # if it is a range, keep the range.  only expand the range
    # when running the checks.
    def run_at_node(self, node, indent):
        session = node.session
        for item in node.checks:
            check = node.get_obj_by_attr_name(item)
            check_path = f"{node.node_path_inst}:[check]{item}"
            for cond in check.ok_necessary_conditions:
                session.goto_obj(node.node_path_inst)
                (cond_check, cond_status) = Check.cond_parse(cond)
                # this is to expand/normalize the path, and get the result
                # at session.obj_path.path.  should have a better api function.
                resolved = DiagObj.Path.resolve_obj_path(
                    cond_check, obj_type_in=DiagObjType.Check, curr_path=node.node_path_inst)
                session.obj_path = resolved.abs_path
                self.add_into_dep_maps(
                    cause=session.obj_path, consequence=check_path
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
            self.sh_cmd = self.session.sh_cmd
            self.ssh_cmd = self.session.ssh_cmd
            parent_path = node_parent.node_path_inst
            self.logger = self.session.logger
            if parent_path != ":":
                parent_path += "."
            self.node_path_inst = parent_path + inst_name
            m = re.match(r"(?P<base>[^\[]+)(?P<range>\[.*\])?", inst_name)
            if not m:
                raise Exception(f"Invalid inst_name {inst_name}")
            # base is the node_path without the range part
            self.node_path_base = parent_path + m.group("base")
            self.range = m.group("range")
        else:
            self.node_path_inst = ":"
            self.node_path_base = ":"

        self.inst_name = inst_name
        # parent node, often the source of the structure information.
        self.node_parent = node_parent

        self.node_file_path = node_file_path
        self.import_path = import_path

        # This legit obj names (cmds, checks etc) will be cached here.
        # Its type is saved in the map, used in __get_class_obj to
        # construct the object.
        self.map_name_to_type = {}

        # self.map_sub_to_class = {}
        # self.map_cmd_to_class = {}
        # self.map_check_to_class = {}

        # By default, this is True except the top empty node,
        # so the hierarchy structures
        # (subs, cmds, checks) are derived from the files.
        # In more complicated cases such as structure changes for
        # inherited classes, muliple elements, set file_cfg to False,
        # in init(), and explicitly set (subs, cmds, checks)
        # self.file_cfg = node_parent is not None
        # Not sure if it is useful any more.  Why not just explicitly control
        # it?  display order should be explitly set anyway.  with hier_build,
        # it is easy to specify.  So, let the files just provide implementation,
        # not affecting the declaration.
        self.file_cfg = False

        # ownership if each node is clearly defined
        # if it is empty, the ownership should be inherited from
        # the hierarchical parents
        self.owners = []

        # the sub nodes
        self.subs = []
        # the properties
        self.props = []
        # commands here do not implicitly inherit.
        self.commands = []
        # the diag checks
        self.checks = []

        # obj dicts are for each 
        self.sub_objs = {}

        # for now, use prop_dict in node to keep the values, for easy implementation,
        # not using the prop obj type
        self.props_dict = {}

        # Run customized init for the diag nodes if init is overridden
        self.init()

        # After sub objects init calls.
        # Do some optimization preparation here.
        self.post_init()

    # To be overridden
    def init(self):
        pass

    def post_init(self):
        if self.file_cfg:
            self.cfg_by_files()

        # Optimize sub obj accesses with an obj cache.
        # why doing this in post_init, after the user init is called?  TBD
        self.objs_dicts_init()

        for prop in self.props:
            self.props_dict[prop] = "Unknown"

    # should be overriden for names ending in digits
    def get_inst_idx(self):
        m = re.match("\S+(?P<idx>\d+)", self.inst_name)
        if not m:
            return None
        return int(m.group("idx"))

    # the lists could be populated by files.  in some cases, the lists
    # depend on specific derived types, so the files do not correspond
    # to the actual lists, then the lists should be used instead of the
    # files.
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
            (DiagObjType.Command, self.commands),
            (DiagObjType.Check, self.checks),
            (DiagObjType.Property, self.props),
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

    # Build map_name_to_type as a map of name->obj_type
    def objs_dicts_init(self):

        # self.session is not assigned until after the NodeDiag consturction.
        # so it is not availble to look up.  but there is no need to be verbose
        # when contructing the top empty node.
        verbose = self.inst_name != "top" and self.session.verbose

        if verbose:
            print(f"{self.inst_name} map_name_to_type: ")

        # constructed objects will be saved here for fast lookup
        self.objs_dict = {}

        self.sub_groups = {}

        # At init time, set up the names dict, so they are legit to access
        # when needed.  The objects will be constructed when being accessed
        # in get_obj_by_attr_name()
        for sub_name in self.subs:
            if sub_name in self.map_sub_to_class:
                sub_type_name = sub_name
                range_str = None
                inst = None
            else:
                (sub_type_name, range_str, inst) = group_str_parse(sub_name)

            if range_str:
                self.sub_groups[sub_type_name] = range_str
            self.map_name_to_type[sub_type_name] = DiagObjType.Node
            if verbose:
                print(f"    {sub_type_name}, type node")
        for prop_name in self.props:
            self.map_name_to_type[prop_name] = DiagObjType.Property
            if verbose:
                print(f"    {prop_name}, type prop")            
        for cmd_name in self.commands:
            self.map_name_to_type[cmd_name] = DiagObjType.Command
            if verbose:
                print(f"    {cmd_name}, type cmd")                    
        for check_name in self.checks:
            self.map_name_to_type[check_name] = DiagObjType.Check
            if verbose:
                print(f"    {check_name}, type check")  

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

    def show_summary(self, console_show=True):
        show_dict = {}
        if console_show:
            print(f"class name: {type(self).__name__}")
            print(f"inst_name: {self.inst_name}")
            print(f"node_path: {self.node_path_inst}")
            print(f"node file path: {self.node_file_path}")
            if hasattr(self, "info"):
                print(f"Info: {self.info}")
            self.show_props()
            self.show_cmds()
            self.show_checks()
            self.show_subs()
        show_dict["inst_name"] = self.inst_name
        show_dict["node_path"] = self.node_path_inst
        show_dict["props"] = self.props
        show_dict["cmds"] = self.commands
        show_dict["checks"] = self.checks
        return show_dict

    def show_props(self):
        print("--Props:")
        # for prop in self.props:
        #     print(prop)
        #     curr_obj = self.session.goto_obj(f"prop", )
        for prop in self.props_dict:
            val = self.props_dict[prop]
            print(f"{prop}: {val}")

    def show_subs(self):
        print("--Sub nodes:")
        for sub in self.subs:
            print(f"  {sub}")
        return self.subs

    def show_checks(self):
        print("--Checks")
        for check in self.checks:
            print(f"  {check}")
        return self.checks

    def show_cmds(self):
        print("--Commands")
        for cmd in self.commands:
            print(f"  {cmd}")
        return self.commands

    def show(self, cmd_args, console_show=True):
        # print(cmd_args)
        if not len(cmd_args):
            return self.show_summary(console_show)

        else:
            print(cmd_args)
            if (cmd_args[0]) == "check":
                return self.show_checks()
            elif (cmd_args[0]) == "cmd":
                return self.show_cmds()

    def help(self):
        print("Commands:")
        for cmd in self.commands:
            print(f"  {cmd}")

        print("Checks")
        for check in self.checks:
            print(f"  {check}")

    def traverse_tree(
        self,
        tree_level=0,
        tree_level_max=-1,
        plugin=None,
        indent="",
        show_node=False,
        expand_group=False,
    ):
        tree_dict = {}
        if show_node:
            print(f"{indent}{self.inst_name}")
        indent += "|--"
        tree_dict["name"] = self.inst_name
        tree_dict["node_path"] = self.node_path_inst
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
            self.session.goto_obj(self.node_path_inst)

        return tree_dict

    def find_attr(self, attr, show_node=False, show=False):

        class AtNodeFindAttr(AtNodePlugin):
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
                            
        plugin = AtNodeFindAttr(attr, show=show)
        self.traverse_tree(0, plugin=plugin, show_node=show_node)
        return plugin.found

    def show_map(self, show_type=None, tree_level_max=-1, console_show=True):
        if not tree_level_max:
            tree_level_max = -1

        def tree_show_cmd(node, cmd_name, indent):
            print(f"{indent}[cmd]{cmd_name}")
            cmd = node.get_obj_by_attr_name(cmd_name)
            conds = cmd.prerequisite_conditions
            for cond in conds:
                print(f"{indent}|--[pre]{cond}")
    
        def tree_show_check(node, check_name, indent):
            if check_name == "overall":
                check_name_show = ""
            else:
                check_name_show = check_name
            print(f"{indent}[chk]{check_name_show}")
            check = node.get_obj_by_attr_name(check_name)
            conds = check.ok_sufficient_conditions
            for cond in conds:
                print(f"{indent}|--[suf]{cond}")
            conds = check.prerequisite_conditions
            for cond in conds:
                print(f"{indent}|--[pre]{cond}")
            conds = check.ok_necessary_conditions
            for cond in conds:
                print(f"{indent}|--[dep]{cond}")

        def tree_show_all(node, indent):
            for cmd in node.commands:
                tree_show_cmd(node, cmd, indent)
            for check in node.checks:
                tree_show_check(node, check, indent)

        if show_type == "check":
            show_func = tree_show_check
        elif show_type == "cmd":
            show_func = tree_show_cmd
        else: # default "all"
            show_func = tree_show_all

        if show_type == "node":
            at_node_show = None
        else:
            at_node_show = AtNodeShow(show_type, show_func)

        tree_dict = self.traverse_tree(
            0, plugin=at_node_show, show_node=console_show, tree_level_max=tree_level_max
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

    def get_obj_by_attr_name(self, attr_name):
        if attr_name not in self.map_name_to_type:
            print(f"[{attr_name}] not in [{self.node_path_inst}]")
            raise AttributeError
        obj = self.__get_class_obj(self.map_name_to_type[attr_name], attr_name)
        if not obj:
            print("failed to set up <{attr_name}> obj")
            raise AttributeError
        return obj
    
    def get_import_path(
        self,
        class_type,
        obj_name="",  # for Node type only
        inst_name="",
    ):
        node_path = self.node_path_base
        import_path = self.import_path
        sub_dir = ""
        sub_node_import_path = ""

        if class_type == DiagObjType.Node:
            sub_dir = os.path.join(self.node_file_path, obj_name)
            if not os.path.isdir(sub_dir):
                # other configuation to be supported.
                err_msg = f"import path sub direcotry {sub_dir} not found"
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
        if self.inst_name != "top" and obj_name not in self.map_name_to_type:
            print(
                f"obj_name <{obj_name}> not in {self.inst_name} map_name_to_type")
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

    def run_cmd(self, cmd, cmd_args=None):
        self.logger.info(f">>== node {self.node_path_inst} run_cmd: cmd [{cmd}], args [{cmd_args}]")
        cmdObj = self.get_obj_by_attr_name(cmd)
        # for prerequisite in cmdObj.prerequisite_conditions:
        #    pass
        return cmdObj.run(cmd_args)

    def run_check(self, check, cmd_args=None):
        checkObj = self.get_obj_by_attr_name(check)
        return checkObj.run(cmd_args)

    def remote_run(self, path: str, cmd_args=None):
        curr_obj = self.session.goto_obj(path)
        ret = curr_obj.run(cmd_args=cmd_args)
        # after remote run, go back to the original node
        self.session.goto_obj(self.node_path_inst)
        return ret

    # Find all direct depending checks and build the dict
    def build_full_dep_map(self):

        cause_dict = {}
        consequence_dict = {}
        self.session.goto_obj(self.node_path_inst)
        plugin = AtNodeFindCheckDep(cause_dict, consequence_dict)
        self.traverse_tree(0, plugin=plugin)
        return (cause_dict, consequence_dict)

    def check_dependents_find(self, check_name):
        top_node = self.session.top_node
        cause_dict, consequence_dict = top_node.build_full_dep_map()

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
        check = self.get_obj_by_attr_name(check_name)
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

        print(f"Added {self.node_path_inst}:[{obj_type}]{obj_name}")

    def prop_set(self, prop, val):
        self.props_dict[prop] = val

    def prop_get(self, prop):
        if not prop in self.props_dict:
            return None
        return self.props_dict

    def cli_get_cmds(self):
        return ["show", "run", "find"]

    def cli_cmd(self, arg_cmd, cmd_args, tree_depth=-1, console_show=True):
        ret = None
        if arg_cmd == "help":
            self.help()
        elif arg_cmd == "show":
            return self.show(cmd_args, console_show=console_show)
        elif arg_cmd == "help":
            return self.help()
        elif arg_cmd == "map":
            if len(cmd_args) and cmd_args[0] in ["node", "check", "cmd"]:
                show_type = cmd_args[0]
            else:
                show_type = "all"
            return self.show_map(show_type=show_type,
                                  tree_level_max=tree_depth,
                                  console_show=console_show)
        elif arg_cmd == "set":
            if len(cmd_args) < 2:
                print(f"Error: invalid set params {cmd_args}")
                return ret
            self.prop_set(cmd_args[0], cmd_args[1])
            return ret
        elif arg_cmd == "get":
            if len(cmd_args) < 1:
                print(f"Error: invalid set params {cmd_args}")
                return ret
            return self.prop_get(cmd_args[0])

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

        else:
            print(
                f"Error: unknown command {arg_cmd} for the node {self.inst_name}")
            return ret
