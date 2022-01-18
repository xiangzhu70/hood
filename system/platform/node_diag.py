from diag_node import NodeDiag

verbose = False

class NodePlatform(NodeDiag):

    model_class_map = {
       "minipack": "NodePlatformMinipack",
    }

    map_sub_to_class = {
        "mgmt_intf": "NodeManagementInterface",
    }
    def morph_by_model(self, model):
        if model in NodePlatform.model_class_map:
            self.__class__ = eval(NodePlatform.model_class_map[model])
            if verbose:
                print(f"Morphed into {type(self).__name__}")
            self.__init__(inst_name=f"platform<{model}>")

    def init(self):
        self.subs = ["mgmt_intf", "kernel", "bmc"]


    def __init__(self, model=None):
        if verbose:
            print(f"Platform init, model={model}")
        self.init()
        self.morph_by_model(model)

class NodePlatformMinipack(NodePlatform):

    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)
        NodePlatform.init(self)
        if verbose:
            iprint("NodePlatformMinipack init")
        self.subs.append("pim[1..8]")
        # NodePlatform.map_sub_to_class["pim"] = "NodePim"
