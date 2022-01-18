from diag_node import NodeDiag


class NodeXphyLane(NodeDiag):
    map_check_dependency = {
        "overall": [
            "LOS",
        ]
    }

    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)
