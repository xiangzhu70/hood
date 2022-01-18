from diag_node import NodeDiag

class NodeProvision(NodeDiag):
    map_check_to_class = {}

    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)
        self.checks = [
            "fbwhoami",
            "fruid"
        ]
