from diag_node import NodeDiag


class NodeKernel(NodeDiag):

    map_check_to_class = {
        "up": "CheckKernelUp",
        "cmdline": "CheckKernelCmdLine",
        "boot_pass_ssd": "CheckKernelBootPassSSD",
        "not_crashing": "CheckKernelNotCrashing",
        "intr_counts": "CheckKernelIntrCounts",
    }

    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name=inst_name)
        self.checks = [
            "up", "cmdline", "boot_pass_ssd", "not_crashing", "intr_counts",
        ]
