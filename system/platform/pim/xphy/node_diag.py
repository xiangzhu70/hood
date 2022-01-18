from diag_node import NodeDiag


class NodeXphy(NodeDiag):

    map_sub_to_class = {
        "lane": "NodeXphyLane",
    }

    map_check_dependency = {
        "overall": "lane[0..3]"
    }
    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)
        self.subs = ["lane[0..3]"]
