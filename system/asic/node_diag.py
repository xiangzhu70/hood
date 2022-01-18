from diag_node import NodeDiag

class NodeAsic(NodeDiag):
    map_chip_type_to_class = {
        "TH3": "NodeAsicTH3",
    }

    map_var_resolve = {
        "device_id": "self", # self, [func], local_vars
    }

    map_sub_to_class = {
        "cpu_port": "NodeCpuPort",
        "front_ports": "NodeFrontPorts",
        "iphy": "NodeInternalPHY",
    }

    map_check_to_class = {
        "presence": "CheckAsicPresence",
    }

    def morph_by_chip_type(self, chip_type):
        if chip_type in NodeAsic.map_chip_type_to_class:
            self.__class__ = eval(NodeAsic.map_chip_type_to_class[chip_type])
            self.__init__()

    def __init__(self, chip_type):
        self.morph_by_chip_type(chip_type)
        NodeDiag.__init__(self, inst_name=f"asic<{chip_type}>")
        self.subs = ["cpu_port", "front_ports", "iphy"]
        self.checks = ["presence"]

    def get_map_check_to_class(self):
        return super().get_map_check_to_class().update(self.map_check_to_class)

class NodeAsicBcm(NodeAsic):
    def __init__(self):
        self.vendor_id = "14e4"

class NodeAsicTH3(NodeAsicBcm):
    def __init__(self):
        NodeAsicBcm.__init__(self)
        self.device_id = "xxxx"
