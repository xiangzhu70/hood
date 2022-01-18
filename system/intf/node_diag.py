from diag_node import NodeDiag


class NodeInterface(NodeDiag):

    map_check_to_class = {
        "overall": "CheckInterfaceOverall",
    }

    map_check_dependency = {
        "overall": "func:parent.gen_interface_dependencies",
    }
    def __init__(self, parent, inst_name):
        NodeDiag.__init__(self, inst_name)
        self.parent = parent
        self.inst_name = inst_name
        self.checks = ["overall"]
