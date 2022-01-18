from diag_check import Check


class CheckCpuCounts(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.action_on_fail = "[investigate]Asic CPU port counts not valid\nOncall: fboss-dev"
