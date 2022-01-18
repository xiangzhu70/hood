from diag_node import NodeDiag

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

