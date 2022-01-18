from diag_node import NodeDiag

verbose = False

class NodeSystem(NodeDiag):

    # necessary to be explicit?  TBD
    map_var_resolve = {
       "chip_type": "self.chip_type",
    }

    map_model_to_class = {
       "wedge100": "NodeWedge100",
       "minipack": "NodeMinipack",
    }

    map_sub_to_class = {
       "intf": "NodeInterface",
       "qsfp_service": "NodeQsfpService",
    }

    map_check_to_class = {
       "inband_ping": "CheckInbandPing",
       "mgmt_ping": "CheckMgmtPing",
       "usv_sshable": "CheckMicroServerSSHable",
       }

    def get_map_check_to_class(self):
        inherited = super().get_map_check_to_class()
        merged = {**inherited, **self.map_check_to_class}
        return merged

    @staticmethod
    def get_model(hostname):
        return None
        #return "ModelX"

    def morph_by_model(self, model=None):
        if not model:
            model = NodeSystem.get_model()
        if model in NodeSystem.map_model_to_class:
            self.__class__ = eval(NodeSystem.map_model_to_class[model])
            if verbose:
                print(f"Morphed into {type(self).__name__}")
            self.inst_name = f"system<{model}>"
            self.__init__()

    def init(self, model):
        super().__init__()
        self.subs = ["agent", "qsfp_service", "platform", "provision",
           "intf[func:gen_intf_range]", "sdk", "asic"]
        self.args_to_sub["model"] = model
        self.checks = ["inband_ping", "mgmt_ping", "usv_sshable"]

    def __init__(self, model=None):
        if verbose:
             print(f"System init, model={model}")
        self.init(model)
        self.morph_by_model(model)

    # To be overwritten by the specific models
    def get_interface_dependencies(self, intf):
        return ""

class NodeMinipack(NodeSystem):

    map_var_resolve = NodeSystem.map_var_resolve
    map_sub_to_class = NodeSystem.map_sub_to_class
    map_check_to_class = NodeSystem.map_check_to_class
 
    def __init__(self):
        #super().init()
        if verbose:
            print("SystemMinipack init")
        self.chip_type = "TH3"

    def gen_intf_range(self):
        return "eth[2..9]/[1..16]/1"

    def gen_interface_dependencies(self, intf):
        return [
            "..asic.port2:port_up == OK",
            "..platform.pim1.xphy2: == OK",
            "..platform.pim1.qsfp10: == OK",
        ]

