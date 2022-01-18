from diag_check import Check


class CheckFbwhoami(Check):
    def __init__(self, inst_name, parent):
        super().__init__(inst_name)
        self.action_on_fail = "[root_cause]Missing fbwhoami\nOncall: fboss-PE"
   

class CheckFruid(Check):
    def __init__(self, inst_name, parent):
        super().__init__(inst_name)
        self.action_on_fail = "[root_cause]Missing fruid\nOncall: fboss-PE"
