from diag_node import NodeDiag

class NodeManagementInterface(NodeDiag):

    map_check_to_class = {
        "overall": "CheckManagementInterface",
    }

    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)
        self.checks = ["overall"]

