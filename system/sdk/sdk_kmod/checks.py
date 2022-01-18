from diag_check import Check


class CheckSdkKmodLoaded(Check):
    def __init__(self, inst_name, parent):
        super().__init__(inst_name)
        self.action_on_fail = "[root_cause]Kmod not loaded\nOncall: fboss-dev"
    

class CheckSdkKmodIntrCounts(Check):
    def __init__(self, inst_name, parent):
        super().__init__(inst_name)
        self.action_on_fail = "[investigate]kmod intr counts stuck\nOncall: fboss-dev"
