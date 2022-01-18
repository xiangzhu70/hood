from diag_check import Check


class CheckManagementInterface(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.ok_necessary_conditions = [
            ":platform.kernel:up == OK",
        ]
        self.action_on_fail = "[investigate]eth0 failed.\nOncall: fboss-platform"
