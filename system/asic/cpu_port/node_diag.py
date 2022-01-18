from diag_node import NodeDiag


class NodeCpuPort(NodeDiag):
    map_check_to_class = {
        "counts": "CheckCpuCounts",
    }
    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name=inst_name)
        self.checks = ["counts"]
