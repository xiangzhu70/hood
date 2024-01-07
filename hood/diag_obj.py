import enum
import importlib
import re
from pdb import set_trace as stop


from utils.diag_utils import NameStyle

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DiagObjType(enum.Enum):
    Node = "node"
    Property = "prop"
    Command = "cmd"
    Check = "check"
    Proc = "proc"


class DiagObj:

    # A DiagObj is a sub node, a check, or a command.
    # The Path is the path in the hierarchy + the obj name
    # The format is <path_head><node>.<node>...<node>:[<type>]<name>
    # path_head can be
    #  : for top,
    #  . for current,
    #  .. for parent, or ../..   for grand parents
    #
    #  TBD ? change to ..3 for 3rd parent, so ..3.node1 is the same as ../../../node1

    # node name does not contain "." or ":", cannot be pure number
    # |--node1
    # |  |--node2
    # |  |  |--node3
    # |  |  |  |--node4
    # |  |--node5

    # absolute path: :node1.node2.node3.node4
    # relative path from node3 to node4: .node4
    # relative path from node3 to itself: .
    # relative path from node3 to node2: ..
    # relative path from node3 to node1: ../.. ..2
    # relative path from node3 to node5: ..3.node5
    # .<node> goes to the sub node
    # ..<node> goes up 1 level and go to the sub node,
    # ..2.<node> goes up 2 levels and go to the sub node,

    # obj path includes [<obj_type>]<obj_name>
    # it could also include a range [..], or even i as index

    # The parsing output should be a move_action
    # 

    # parsing steps:
    # 1.  head_pos
    #     interpret the starting :, ., .., ..<num> prefixes
    # 2.  downstream path
    #     <node1>.<node2>...<node_n> 
    #     words separated by . till end of possible :[<type][name]
    #

    # class PathMoveAction:
    #     def __init__(self,
    #                  #  if True, relative from top
    #                  #  else relative from current after going up to parents_count level
    #                  is_top,
    #                  #  the number of levels to go up
    #                  parents_count,
    #                  # the sub node path with the preceeding "." and ":" stripped
    #                  sub_node_path):
    #         self.is_top = is_top
    #         self.parents_count = parents_count
    #         self.sub_node_path = sub_node_path

    class ObjPathParsed:
        def __init__(self, abs_path, is_top, parents_count, sub_node_path, range, obj_type, obj_name):
            self.abs_path = abs_path
            self.is_top = is_top
            self.parents_count = parents_count
            self.sub_node_path = sub_node_path
            self.range = range
            self.obj_name = obj_name
            self.obj_type = obj_type

        def show(self):
            print(f"abs_path: {self.abs_path}")
            print(f"pos: is_top {self.is_top}, parents_count {self.parents_count}")
            print(f"sub path {self.sub_node_path}, range {self.range}")
            print(f"obj: name {self.obj_name}, type {self.obj_type}")

    class Path:  # DiagObj.Path

        @staticmethod
        def parse_head_pos(head_pos):
            is_top = False
            parents_count = 0
            if (not head_pos) or (head_pos == "."):
                pass
            elif head_pos.startswith(":"):
                is_top = True
                # # remove ":"
                # head_pos = head_pos[1:]
                # if not head_pos:  # was ":", fill top_node_name
                #     obj_path = top_node_name
                # elif not obj_path.startswith(top_node_name):
                #     # instert top_node_name
                #     # was ":<obj>", this is the 2nd ":"
                #     if obj_path.startswith(":"):
                #         obj_path = top_node_name + obj_path
                #     else:
                #         obj_path = top_node_name + "." + obj_path
            elif head_pos.startswith(".."):
                while head_pos.startswith(".."):
                    # ..<\d+>.  ex. ..3.
                    m = re.match(r"^(?P<count>\d*)\..*", head_pos[2:])
                    if m:
                        count_str = m.group("count")
                        parents_count += int(count_str)
                        head_pos = head_pos[len(count_str)+1:]
                    else:
                        parents_count += 1
                        head_pos = head_pos[2:]
                        if len(head_pos) and head_pos[0] == "/":
                            head_pos = head_pos[1:]
            return (is_top, parents_count)
        
        @staticmethod
        def parse_obj_str(obj_str):
            if not obj_str:
                return (None, None)
            m = re.match(r"(\[(?P<type>\S+)\])?(?P<name>\w*)", obj_str)
            if not m:
                print(obj_str)
                stop()
                raise Exception("invalid check_path")
            obj_type = m.group("type") # optional, could be None
            obj_name = m.group("name")
            return (obj_type, obj_name)



        @staticmethod
        def resolve_obj_path(
                obj_path: str,
                obj_type_in=None,   # from context sometimes the type is known
                curr_path=None,     # if it is relative path, the curr_path
                                    # should be provided to derive the final
                                    # absolute path
                verbose=False):
            
            # in the dependency spec context, skip "[check]".
            # "node...node:" means "node...node:[check]overall"
            # "node...node:<check>" means "node...node:[check]<check>"
            
            parents_count = 0  # current

            if verbose:
                print(f"obj_path {obj_path}, obj_type {obj_type_in}")
            # to support "cd [check]<check_name>" case, prepend ".:"
            if obj_path.startswith("["):
                obj_path = ".:" + obj_path

            # initial cut to head_pos, sub_node_path, obj
            m = re.match(r"(?P<head_pos>[^a-zA-Z_]+)?(?P<sub_node_path>\w[^:\[]+)(?P<range>\[.*\])?(:(?P<obj>.*))?", obj_path)
            if not m:
                raise Exception(f"invalid path [{obj_path}]")
            (is_top, parents_count) = DiagObj.Path.parse_head_pos(m.group("head_pos"))
            sub_node_path = m.group("sub_node_path")
            range = m.group("range")
            obj_str = m.group("obj") # [check]<check_name>
            (obj_type, obj_name) = DiagObj.Path.parse_obj_str(obj_str)

            if obj_type_in:
                if obj_type:
                    if obj_type != obj_type_in.value.lower():
                        raise Exception("known type conflicting parsed type")
                else:
                    obj_type = obj_type_in.value.lower()
            
            # find the absolute path for a relative path
            if not is_top:
                if not curr_path:
                    raise Exception("For a relative path, curr_path should be provided")
                tmp_parents_count = parents_count
                while tmp_parents_count > 0:
                    rindex = curr_path.rindex(".")
                    curr_path = curr_path[:rindex]
                    tmp_parents_count -= 1
                abs_path = curr_path + "." + sub_node_path
            else:
                abs_path = f":{sub_node_path}"

            if obj_type_in == DiagObjType.Check and obj_str is None:
                obj_name = "overall"
                obj_type = "check"

            if obj_type == "chk":
                obj_type = "check"

            if obj_str:
                abs_path += f":[{obj_type}]{obj_name}"
            if verbose:
                print(f"resolve_obj_path: top {is_top}, abs_path {abs_path} parents_count {parents_count}, obj_type {obj_type}, obj_name {obj_name}")
            return DiagObj.ObjPathParsed(abs_path, is_top, parents_count, sub_node_path, range, obj_type, obj_name)

    @staticmethod
    def construct_obj(
        context_node,
        import_module_path,
        class_name,
        inst_name,
        node_file_path=None,
        import_path=None,
    ):
        module = importlib.import_module(import_module_path)
        if class_name not in module.__dict__:
            err_msg = f"Invalid class name {class_name}"
            print(err_msg)
            stop()
            raise Exception(err_msg)
        class_def = module.__dict__[class_name]
        try:
            classObj = class_def(
                context_node,
                inst_name,
                node_file_path=node_file_path,
                import_path=import_path,
            )
        except Exception as e:
            print(f"construct_class_obj: {class_def} failed.")
            logger.exception(e)
        return classObj

    @staticmethod
    def module_get_obj_class_names(import_module_path, obj_type):
        module = importlib.import_module(import_module_path)
        obj_class_names = []

        pattern = rf"{obj_type.name}(?P<camel>\S+)"
        for key in module.__dict__:
            m = re.match(pattern, key)
            if not m:
                continue
            camel = m.group("camel")
            obj_name = NameStyle.camel_to_underscore(camel)
            obj_class_names.append((key, obj_name))
        return obj_class_names


if __name__ == "__main__":

    for obj_path_params in [
        (":ab.cd", None),
        (":ab.cd:[check]ef", None),
        (".cd:[check]ef", ":ab"),
        ("..cd.ef.:[check]ef", ":hi.jk.op.qi"),
        ("..2.cd.ef.:[check]ef", ":hi.jk.op.qi"),
        ("../..cd.ef.:[check]ef", ":hi.jk.op.qi"),
    ]:
        (obj_path, curr_path) = obj_path_params
        obj_path_parsed = DiagObj.Path.resolve_obj_path(
            obj_path, curr_path=curr_path)
        print(f"-- obj_path: {obj_path}, curr_path {curr_path}")
        obj_path_parsed.show()