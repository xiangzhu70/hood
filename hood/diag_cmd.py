# from pdb import set_trace as stop

from hood.diag_obj import DiagObj


class Command(DiagObj):

    import_path_append = ".commands"

    def __init__(self, context_node, inst_name, node_file_path, import_path):
        self.node = context_node
        self.inst_name = inst_name
        self.obj_path = f"{self.node.node_path}:[cmd]{inst_name}"
        self.sh_cmd = self.node.session.sh_cmd
        self.logger = self.node.session.logger
        self.init()

    def init(self):
        pass

    def log(self, log_message):
        self.logger.info(log_message)

    def show(self):
        print(f"Command name = {self.inst_name}")

    def run(self, cmd_args):
        print(f"-- Command {self.inst_name} run, args={cmd_args}")

    def run_cmd(self, cmd, shell=False, realtime=False, timeout=1):
        ret = self.sh_cmd.run_cmd(cmd, shell=shell, realtime=realtime, timeout=timeout)
        return ret

    def cli_cmd(self, arg_cmd, cmd_args, tree=False):
        if arg_cmd == "run":
            self.run(cmd_args)
