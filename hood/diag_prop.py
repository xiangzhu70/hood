# from pdb import set_trace as stop

from hood.diag_obj import DiagObj

# TBD whether to have this class is still in question
# is there any compication which needs such a class, followind cmds and checks,
# or a simple dict under node would be good enough?
# for now, let it be like cmd, so the complication can be added easily if needed
# could be cleaned up later.

class Property(DiagObj):

    import_path_append = ".properties"

    def __init__(self, context_node, inst_name, node_file_path, import_path):
        self.node = context_node
        self.inst_name = inst_name
        self.val = "Unknown"

        self.init()

    def init(self):
        pass

    def set(self, cmd_args):
        self.val = cmd_args

    def get(self, cmd_args=None):
        print(self.val)

    def show(self):
        print(f"Property name = {self.inst_name}")

    def cli_cmd(self, arg_cmd, cmd_args):
        if arg_cmd == "set":
            self.set(cmd_args)
