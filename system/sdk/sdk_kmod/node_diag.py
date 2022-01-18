from diag_node import NodeDiag

class NodeSdkKmod(NodeDiag):
    map_check_to_class = {
       "loaded": "CheckSdkKmodLoaded",
       "intr_counts": "CheckSdkKmodIntrCounts",
    }
    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)
        self.checks = {
            "loaded", "intr_counts",
        }
