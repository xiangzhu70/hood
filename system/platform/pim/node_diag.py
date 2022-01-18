from diag_node import NodeDiag

class NodePim(NodeDiag):
    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name=inst_name)
        self.subs = ["fpga", "qsfp[1..16]", "xphy[1..4]"]
        
        if not "[" in inst_name:
            m = re.match(r"pim(?P<pim_idx>\d+)$", inst_name)
            if not m:
                raise(Exception("wrong inst_name"))
            self.args_to_sub = {"pim_idx": m.group("pim_idx")} 

