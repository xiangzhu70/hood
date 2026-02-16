# from pdb import set_trace as stop

from hood.diag_obj import DiagObj
from utils.sh_cmd import ShellCommand
from utils.ssh_cmd import SshCommand

class CmdArg:
    def __init__(self, arg, default=None):
        self.arg = arg
        self.default = default

class Command(DiagObj):

    import_path_append = ".commands"

    def __init__(self, context_node, inst_name, node_file_path, import_path):
        self.node = context_node
        self.inst_name = inst_name
        self.obj_path = f"{self.node.node_path_inst}:[cmd]{inst_name}"
        self.args = []
        self.sh_runner = ShellCommand
        self.ssh_runner = SshCommand

        self.logger = self.node.session.logger

        # Check these to ensure the run() can work.
        # save time in the FAIL route which necessary
        # tool is not OK.
        # Applicable to both cmmands and checks
        self.prerequisite_conditions = []

        self.init()

    def init(self):
        pass

    def help(self):
        # To be overwritten by the specific commands
        print(f"Command name = {self.inst_name}")

    def log(self, log_message):
        self.logger.info(log_message)

    def show(self):
        print(f"Command: {self.inst_name}")
        if self.args:
            print("args:")
            for a in self.args:
                default = getattr(a, "default", None)
                if default is None:
                    print(f"  {a.arg}")
                else:
                    print(f"  {a.arg} (default={default})")

    def run(self, cmd_args, console_show=True):
        if console_show:
            print(f"-- Command {self.inst_name} run, args={cmd_args}")

    def sh_cmd(self, cmd, shell=False, realtime=False, timeout=1):
        ret = self.sh_runner.run_cmd(cmd, shell=shell, realtime=realtime, timeout=timeout)
        return ret

    def ssh_cmd(self, host, user, cmd, password=None, shell=False, realtime=False, timeout=1):
        ret = self.ssh_runner.run_cmd(host, user, cmd, password=password, shell=shell, realtime=realtime, timeout=timeout)
        return ret

    def cli_cmd(self, arg_cmd, cmd_args, tree=False):
        if arg_cmd == "run": 
            # call the run function provided by the user
            self.run(cmd_args)
