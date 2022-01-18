from diag_check import Check

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

