from diag_node import NodeDiag
from diag_check import Check
from diag_cmd import Command

import re

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
 
class CheckInbandPing(Check):

    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.prerequisite_conditions = [
            "::usv_sshable == OK",
        ]
        self.ok_necessary_conditions = [
            ":agent.process:process_up == OK",
            ":platform.kernel:intr_counts == OK",
            ":sdk.sdk_kmod:intr_counts == OK",
            ":agent.inband_intf: == OK",
            ":agent.slow_path:host_txrx_counts == OK",
            ":asic.cpu_port:counts == OK",
        ]

class CheckMgmtPing(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.ok_necessary_conditions = [
            ":platform.mgmt_intf: == OK",
        ]
        
class CheckMicroServerSSHable(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.ok_necessary_conditions = [
            ":platform.mgmt_intf: == OK",
        ]
 
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

class NodeAgent(NodeDiag):

    map_sub_to_class = {
       "process": "NodeAgentProcess",
       "agent_conf": "NodeAgentConf",
       "inband_intf": "NodeAgentInbandIntf",
       "swSwitch": "NodeSwSwitch",
       "slow_path": "NodeSlowPath",
       "data_path": "NodeDataPath",
    }

    map_check_to_class = {
       "process_up": "CheckAgentProcessUp",
    }

    def __init__(self):
       NodeDiag.__init__(self, inst_name="agent")
       self.subs = ["process", "agent_conf", "inband_intf", "swSwitch", "hwSwitch", "slow_path", "data_path"]

class NodeAgentInbandIntf(NodeDiag):
    map_check_to_class = {
        "overall": "CheckAgentInbandIntf",
    }

    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)
        self.checks = ["overall"]
    
class CheckAgentInbandIntf(Check):
    pass
    
class NodeAgentConf(NodeDiag):
    map_check_to_class = {
        "overall": "CheckAgentConf",
    }

    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)
        self.checks = ["overall"]

class CheckAgentConf(Check):
    pass

class NodeQsfpService(NodeDiag):
    map_sub_to_class = {
       "process": "NodeQsfpServiceProcess",
    }

    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)
        self.subs = ["process"]

class NodeQsfpServiceProcess(NodeDiag):
    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)

class NodeAgentProcess(NodeDiag):
    map_check_to_class = {
        "run_env": "CheckAgentRunEnv",
        "process_up": "CheckAgentProcessUp",
        "not_crashing": "CheckAgentProcessNotCrashing",
        "no_asic_error": "CheckAgentProcessNoAsicError",
    }
    def __init__(self):
       NodeDiag.__init__(self, inst_name="process")
       self.checks = [
           "process_up",
           "run_env",
           "not_crashing",
           "no_asic_error",
       ]
 
class CheckAgentProcessUp(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.ok_necessary_conditions = [
            ":platform.kernel:up == OK",
            ".:run_env == OK",
            ".:not_crashing == OK",
            ".:no_asic_error == OK",
        ]

class CheckAgentRunEnv(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.ok_necessary_conditions = [
            ":asic:presence == OK",
            ":platform.kernel:cmdline == OK",
            ":sdk.sdk_kmod:loaded == OK",
            ":provision:fbwhoami == OK",
            ":provision:fruid == OK",
        ]

class CheckAgentProcessNotCrashing(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.action_on_fail = "[investigate]Look into crash log\nOncall: fboss-dev"

class CheckAgentProcessNoAsicError(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.action_on_fail = "[investigate]Look into ASIC error log\nOncall: fboss-dev"

class NodePim(NodeDiag):
    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name=inst_name)
        self.subs = ["fpga", "qsfp[1..16]", "xphy[1..4]"]
        
        if not "[" in inst_name:
            m = re.match(r"pim(?P<pim_idx>\d+)$", inst_name)
            if not m:
                raise(Exception("wrong inst_name"))
            self.args_to_sub = {"pim_idx": m.group("pim_idx")} 

class NodePorts(NodeDiag):
    def __init__(self, instances_list):
        NodeDiag.__init__(self, inst_name="ports")
        # TBD is input forced to be string?
        #self.subs = eval(instances_list)


class NodeInterface(NodeDiag):

    map_check_to_class = {
        "overall": "CheckInterfaceOverall",
    }

    map_check_dependency = {
        "overall": "func:parent.gen_interface_dependencies",
    }
    def __init__(self, parent, inst_name):
        NodeDiag.__init__(self, inst_name)
        self.parent = parent
        self.inst_name = inst_name
        self.checks = ["overall"]

class CheckInterfaceOverall(Check):
    def __init__(self, inst_name, parent):
        super().__init__(inst_name)
        self.node = parent
        self.deps = self.node.parent.gen_interface_dependencies(self.node.inst_name) 

    def run(self):
        intf = self.parent
        print(f"intf {intf.inst_name} CheckInterfaceOverall run")
        
class NodeProvision(NodeDiag):
    map_check_to_class = {}

    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)
        self.checks = [
            "fbwhoami",
            "fruid"
        ]

class CheckFbwhoami(Check):
    def __init__(self, inst_name, parent):
        super().__init__(inst_name)
        self.action_on_fail = "[root_cause]Missing fbwhoami\nOncall: fboss-PE"
   

class CheckFruid(Check):
    def __init__(self, inst_name, parent):
        super().__init__(inst_name)
        self.action_on_fail = "[root_cause]Missing fruid\nOncall: fboss-PE"

class NodeFpga(NodeDiag):
    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)

class NodeQsfp(NodeDiag):
    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)

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
        
class NodeXphyLane(NodeDiag):
    map_check_dependency = {
        "overall": [
            "LOS",
        ]
    }

    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)

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

class NodeManagementInterface(NodeDiag):

    map_check_to_class = {
        "overall": "CheckManagementInterface",
    }

    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)
        self.checks = ["overall"]

class CheckManagementInterface(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.ok_necessary_conditions = [
            ":platform.kernel:up == OK",
        ]
        self.action_on_fail = "[investigate]eth0 failed.\nOncall: fboss-platform"

class NodeKernel(NodeDiag):

    map_check_to_class = {
        "up": "CheckKernelUp",
        "cmdline": "CheckKernelCmdLine",
        "boot_pass_ssd": "CheckKernelBootPassSSD",
        "not_crashing": "CheckKernelNotCrashing",
        "intr_counts": "CheckKernelIntrCounts",
    }

    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name=inst_name)
        self.checks = [
            "up", "cmdline", "boot_pass_ssd", "not_crashing", "intr_counts",
        ]

class CheckKernelUp(Check):
    
    def __init__(self, inst_name):
        super().__init__(inst_name)
        # need session to save history state.  otherwise there can be loop because dep and suff are opposite.
        #self.ok_sufficient_conditions = [
        #    "::usv_sshable == OK",
        #]
        self.prerequisite_conditions = [
            ":platform.bmc:bmc_sshable == OK",
            ":platform.bmc:usv_console_alive == OK",
        ]
        self.ok_necessary_conditions = [
            ".:boot_pass_ssd == OK",
            ".:not_crashing == OK",
      ]

class CheckKernelCmdLine(Check):
    def __init__(self, inst_name, parent):
        super().__init__(inst_name)
        self.action_on_fail = "[root_cause]Invalid kernel boot line\nOncall: fboss-dev"

class CheckKernelBootPassSSD(Check):
    def __init__(self, inst_name, parent):
        super().__init__(inst_name)
        self.action_on_fail = "[root_cause]SSD failed\nOncall: ENS"

class CheckKernelNotCrashing(Check):
    def __init__(self, inst_name, parent):
        super().__init__(inst_name)
        self.action_on_fail = "[investigate]kernel crashing\nOncall: fboss-platform"

class CheckKernelIntrCounts(Check):
    def __init__(self, inst_name, parent):
        super().__init__(inst_name)
        self.action_on_fail = "[investigate]Kernel intr counts stuck\nOncall: fboss-dev"

class NodePlatformMinipack(NodePlatform):

    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name)
        NodePlatform.init(self)
        if verbose:
            iprint("NodePlatformMinipack init")
        self.subs.append("pim[1..8]")

class NodeSdk(NodeDiag):
    map_sub_to_class = {
        "sdk_kmod": "NodeSdkKmod",
    }

    def __init__(self):
        NodeDiag.__init__(self, inst_name="sdk")
        self.subs = [
            "sdk_kmod",
        ]


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

class CheckSdkKmodLoaded(Check):
    def __init__(self, inst_name, parent):
        super().__init__(inst_name)
        self.action_on_fail = "[root_cause]Kmod not loaded\nOncall: fboss-dev"
    

class CheckSdkKmodIntrCounts(Check):
    def __init__(self, inst_name, parent):
        super().__init__(inst_name)
        self.action_on_fail = "[investigate]kmod intr counts stuck\nOncall: fboss-dev"

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

class CheckAsicPresence(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.action_on_fail = "[root-cause]ASIC missing\nOncall: fboss-hardware"

class NodeCpuPort(NodeDiag):
    map_check_to_class = {
        "counts": "CheckCpuCounts",
    }
    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name=inst_name)
        self.checks = ["counts"]

class CheckCpuCounts(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.action_on_fail = "[investigate]Asic CPU port counts not valid\nOncall: fboss-dev"

class NodeFrontPorts(NodeDiag):
    def __init__(self, inst_name):
        super().__init__(inst_name)

class NodeInternalPHY(NodeDiag):
    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name=inst_name)
        self.cmds = ["reset"]

class CmdInternalPHYReset(Command):
    def run():
        print("run internal PHY reset")

class NodeAsicBcm(NodeAsic):
    def __init__(self):
        self.vendor_id = "14e4"

class NodeAsicTH3(NodeAsicBcm):
    def __init__(self):
        NodeAsicBcm.__init__(self)
        self.device_id = "xxxx"

class NodeSwSwitch(NodeDiag):
    def __init__(self):
        NodeDiag.__init__(self, inst_name="swSwitch")
     
class NodeHwSwitch(NodeDiag):
    def __init__(self):
        NodeDiag.__init__(self, inst_name="hwSwitch")

class NodeSlowPath(NodeDiag):
    map_check_to_class = {
        "host_txrx_counts": "CheckHostTxRxCounts",
    }

    def __init__(self):
        NodeDiag.__init__(self, inst_name="slow_path")
        self.checks = ["host_txrx_counts"]

class CheckHostTxRxCounts(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
     
class NodeDataPath(NodeDiag):
    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name=inst_name)

class NodeBmc(NodeDiag):
    map_sub_to_class = {
        "eth0": "NodeBmcEth0",
    }
    map_check_to_class = {
        "bmc_sshable": "CheckBmcSSHable",
        "usv_console_alive": "CheckMicroServerConsoleAlive",
    }
    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name=inst_name)
        self.checks = [
            "bmc_sshable",
            "usv_console_alive",
        ]
        self.subs = ["eth0"]

class NodeBmcEth0(NodeDiag):
    map_check_to_class = {
        "overall": "CheckBmcEth0Overall",
    }
    def __init__(self, inst_name):
        NodeDiag.__init__(self, inst_name=inst_name)
        self.checks = ["overall"]

class CheckBmcEth0Overall(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.action_on_fail = "[investigate]bmc eth0 failed.\nOncall: fboss-platform"

class CheckBmcSSHable(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.ok_necessary_conditions = [
            ":platform.bmc.eth0: == OK",
        ]

class CheckMicroServerConsoleAlive(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.action_on_fail = "[remediate]:platform.bmc.[cmd]reset_usv"
     
if __name__ == "__main__":
  model0 = NodeSystem()
  model0.show()
  modelX = NodeSystem(model="ModelX")
  modelX.show()
  modelX.modelX_method()

