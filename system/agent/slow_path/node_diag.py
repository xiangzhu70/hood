from diag_node import NodeDiag


class NodeSlowPath(NodeDiag):
    map_check_to_class = {
        "host_txrx_counts": "CheckHostTxRxCounts",
    }

    def __init__(self):
        NodeDiag.__init__(self, inst_name="slow_path")
        self.checks = ["host_txrx_counts"]
