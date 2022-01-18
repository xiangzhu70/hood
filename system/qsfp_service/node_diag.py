from diag_node import NodeDiag


class NodeQsfpService(NodeDiag):
    map_sub_to_class = {
       "process": "NodeQsfpServiceProcess",
    }

    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)
        self.subs = ["process"]
