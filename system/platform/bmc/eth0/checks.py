from diag_check import Check

class CheckBmcEth0Overall(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.action_on_fail = "[investigate]bmc eth0 failed.\nOncall: fboss-platform"
