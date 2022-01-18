from diag_node import NodeDiag


class NodeInternalPHY(NodeDiag):
    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name=inst_name)
        self.cmds = ["reset"]
