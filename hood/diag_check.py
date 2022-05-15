import re
import typing

class Check:


    def __init__(self, inst_name):
        self.inst_name = inst_name
        
        # Check this first.  Save time in OK route.
        self.ok_sufficient_conditions = []
        
        # Check these to ensure the run() can work.
        # save time in the FAIL route which necessary
        # tool is not OK.
        self.prerequisite_conditions = []
        # dependency / causality conditions.
        self.ok_necessary_conditions = [
        # <check> == OK
        ]

        # str in these formats
        # [root_cause]<message>
        # [check]<next check path>
        # [investigate]<reason for further investigation>
        self.action_on_fail = None

    def show(self):
        print(f"Check name = {self.inst_name}")
        print("Dependencies:")
        for dep in self.deps:
            print(dep)

    def run(self):
        print(f"Check {self.inst_name} run")
        return "OK"


    def cond_extract_check_name(cond: str):
        (cond_check, cond_status) = Check.cond_parse(cond)
        (node_path, check_name) = Check.check_path_parse(cond_check)
        return check_name

    # get valid label for graphviz.  no : or . allowed.
    def check_path_to_label(check_path: str):
        label = check_path.replace(":", "_")
        label = label.replace(".", "_")
        label = label.replace("<", "_")
        label = label.replace(">", "_")
        return label

    def check_path_parse(check_path: str):
        m = re.match(r"^(?P<node_path>^(:)?\S+):(?P<check_name>\w*)", check_path)
        if not m:
            print(check_path)
            import pdb; pdb.set_trace()
            raise Exception("invalid check_path")
        node_path = m.group("node_path")
        check_name = m.group("check_name")
        return (node_path, check_name)

    def cond_parse(cond: str):
        m = re.match(r"(?P<cond_check>[^= ]+)\s*==\s*(?P<cond_status>.*)", cond)
        if not m:
            print(f"Invalid condition statement {cond}")
            raise Exception
        cond_check = m.group("cond_check") 
        cond_status = m.group("cond_status")
        return (cond_check, cond_status)

    def check_graph_internal(self, check_path, check_label):
        suf_exist = len(self.ok_sufficient_conditions) > 0
        pre_exist = len(self.prerequisite_conditions) > 0
        lines = []
        #lines.append(f'#\n-- inst_name={self.inst_name}, check_path={check_path}, check_label={check_label}')
        if suf_exist or pre_exist:
            #import pdb; pdb.set_trace()
            lines.append(f"subgraph cluster_{check_label} {{")
            lines.append(f'label="{check_path}"')
            lines.append(f'{check_label}_entry [label="entry"]')
            lines.append(f'{check_label}_ok [label="OK"]')
            lines.append(f'{check_label}_run [label = "check.run()"]')
            lines.append(f'{check_label}_fail [label = "Fail"]')
            lines.append(f'{check_label}_run->{check_label}_ok [label="Y"]')
            lines.append(f'{check_label}_run->{check_label}_fail [label="N"]')
            if suf_exist:
                lines.append(f'{check_label}_suf [label="suff"]')
                lines.append(f'{check_label}_entry -> {check_label}_suf')
            if pre_exist:
                lines.append(f'{check_label}_pre [label="pre"]')
            if not suf_exist:
                lines.append(f'{check_label}_entry -> {check_label}_pre')

            lines.append("}")
        else:
            lines.append(f'{check_label} [label="{check_path}"]')
        #lines.append(f'# --> inst_name={self.inst_name}\n')
        return (suf_exist, pre_exist, lines)
