from diag_check import Check


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
