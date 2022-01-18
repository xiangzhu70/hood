from diag_node import NodeDiag

class NodeAgentInbandIntf(NodeDiag):
    map_check_to_class = {
        "overall": "CheckAgentInbandIntf",
    }

    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)
        self.checks = ["overall"]

