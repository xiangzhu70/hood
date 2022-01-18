from diag_node import NodeDiag

class NodeBmc(NodeDiag):
    map_sub_to_class = {
        "eth0": "NodeBmcEth0",
    }
    map_check_to_class = {
        "bmc_sshable": "CheckBmcSSHable",
        "usv_console_alive": "CheckMicroServerConsoleAlive",
    }
    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name=inst_name)
        self.checks = [
            "bmc_sshable",
            "usv_console_alive",
        ]
        self.subs = ["eth0"]
