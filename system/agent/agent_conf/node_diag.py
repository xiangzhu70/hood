from diag_node import NodeDiag

class NodeAgentConf(NodeDiag):
    map_check_to_class = {
        "overall": "CheckAgentConf",
    }

    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)
        self.checks = ["overall"]
