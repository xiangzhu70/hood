#!/usr/bin/env python3

class NodeDiag:

    def __init__(self, inst_name, node_args=[]):
        self.inst_name = inst_name
        self.node_args = node_args
       
        # the local variables for the local cmd run environment.
        self.local_vars = []
        # the sub notes
        self.subs = []
        # functions needed?  could the class member functions acheive the purpose?
        # These are not exact python functions.  It is more a cmd helper to add
        # local variables for cmd excution.
        self.functions = []
        # Python inheritance is used for inheriting the structure (subs).
        # commands here do not implicitly inherit.
        self.commands = []
        self.checks = []
        self.depends = []
        self.display_name = ""

    def show(self):
       print(f"NodeDiag inst {self.inst_name}")

if __name__ == "__main__":
    diag_node = NodeDiag(inst_name="diag")
    diag_node.show()
