from diag_check import Check


class CheckInterfaceOverall(Check):
    def __init__(self, inst_name, parent):
        super().__init__(inst_name)
        self.node = parent
        self.deps = self.node.parent.gen_interface_dependencies(self.node.inst_name) 

    def run(self):
        intf = self.parent
        print(f"intf {intf.inst_name} CheckInterfaceOverall run")
