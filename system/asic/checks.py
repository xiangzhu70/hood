from diag_check import Check


class CheckAsicPresence(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.action_on_fail = "[root-cause]ASIC missing\nOncall: fboss-hardware"
