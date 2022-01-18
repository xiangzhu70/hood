from diag_node import NodeDiag


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
