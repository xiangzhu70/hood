import enum
import importlib
import re
from pdb import set_trace as stop


from diag_utils import NameStyle

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DiagObjType(enum.Enum):
    Node = "node"
    Command = "cmd"
    Check = "check"


class DiagObj:

    # A target is a sub node, a check, or a command.
    # The TargetPath is the path in the hierarchy + the target name
    # The format is <path_head><node>.<node>...<node>:[<type>]<name>
    # path_head can be
    #  : for top,
    #  . for current,
    #  .. for parent, or ../..   for grand parents

    # parsing output:
    #  relative path <node>.<node>...
    #  if top=True, relative from top
    #  else relative from current after going up to parent_count level

    class Path:
        def __init__(self, init_path, top_node_name):
            self.top_node_name = top_node_name
            self.path = init_path

        # update absolute path, and return actions in the following set
        # (top, parent_count, sub_node_path)
        # The caller should go to top if top==True
        # Otherwise, it goes up parents by parents_count, and go to
        # sub_node_path.
        def move(self, obj_path: str, obj_type=None):
            parents_count = 0  # current
            top = False
            sub_node_path = ""
            top_node_name = self.top_node_name
            curr_path = self.path

            # to support "cd [check]<check_name>" case, prepend ".:"
            if obj_path.startswith("["):
                obj_path = ".:" + obj_path

            if obj_path.startswith(":"):
                top = True
                # remove ":"
                obj_path = obj_path[1:]
                if not obj_path:
                    obj_path = top_node_name
                elif not obj_path.startswith(top_node_name):
                    # instert top_node_name
                    if obj_path.startswith(":"):
                        obj_path = top_node_name + obj_path
                    else:
                        obj_path = top_node_name + "." + obj_path
            elif obj_path.startswith(".."):
                while obj_path.startswith(".."):
                    parents_count += 1
                    obj_path = obj_path[2:]
                    if len(obj_path) and obj_path[0] == "/":
                        obj_path = obj_path[1:]
            elif obj_path.startswith("."):
                obj_path = obj_path[1:]
            tmp_parents_count = parents_count
            if top:
                self.path = ":" + obj_path
            else:
                while tmp_parents_count > 0:
                    rindex = curr_path.rindex(".")
                    curr_path = curr_path[:rindex]
                    tmp_parents_count -= 1
                if obj_path:
                    if not obj_path.startswith(":"):
                        self.path = curr_path + "." + obj_path
                    else:
                        self.path = curr_path + obj_path
                else:
                    self.path = curr_path
            if obj_path.endswith(":") and obj_type == DiagObjType.Check:
                obj_path += "[check]overall"
                self.path += "[check]overall"

            if not obj_path:
                return (top, parents_count, sub_node_path)

            m = re.match(
                r"^(?P<node_path>[^: ]*)(:(\[(?P<type>\S+)\])?(?P<name>\w*))?", obj_path
            )
            if not m:
                print(obj_path)
                stop()
                raise Exception("invalid check_path")
            sub_node_path = m.group("node_path")
            self.obj_type = m.group("type")
            self.obj_name = m.group("name")
            if self.obj_name:
                if obj_type:  # explicitly provided by the caller
                    expected_type = obj_type.value.lower()
                    if self.obj_type:
                        if expected_type != self.obj_type:
                            stop()
                            raise Exception("target type unexpected")
                    else:
                        # target type not set.  explicitedly instert it.
                        self.obj_type = expected_type
                        column_index = self.path.rindex(":")
                        pre = self.path[: column_index + 1]
                        post = self.path[column_index + 1 :]
                        self.path = f"{pre}[{expected_type}]{post}"
            if not self.obj_type:
                self.obj_type = "node"

            return (top, parents_count, sub_node_path)

    @staticmethod
    def construct_obj(
        context_node,
        import_module_path,
        class_name,
        inst_name,
        node_file_path=None,
        import_path=None,
    ):
        if "link-tree" in import_module_path:
            stop()
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
            stop()
            print("xxx")
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
