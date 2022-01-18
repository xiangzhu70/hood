from diag_node import NodeDiag


class NodeBmcEth0(NodeDiag):
    map_check_to_class = {
        "overall": "CheckBmcEth0Overall",
    }
    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name=inst_name)
        self.checks = ["overall"]
