from diag_check import Check


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
