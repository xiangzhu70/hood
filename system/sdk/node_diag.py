from diag_node import NodeDiag

class NodeSdk(NodeDiag):
    map_sub_to_class = {
        "sdk_kmod": "NodeSdkKmod",
    }

    def __init__(self):
        NodeDiag.__init__(self, inst_name="sdk")
        self.subs = [
            "sdk_kmod",
        ]
