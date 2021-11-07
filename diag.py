from node_diag import *

class Session:

    sessions_count = 0

    def __init__(self, entry_file, args):
        self.session_id = Session.sessions_count
        Sessions.sessions_count += 1

        self.local_vars = parse_args(args)

        self.visited_nodes = {}

        import_nodes_entry_file(entry_file)
        
    # TBD move to a util file?
    def parse_args(self, args):
        return {}

	def enter_initial_node():

    def enter_node(node_path):
        nodes_in_path = node_path.split(".")
        node_name = nodes_in_path[0]
        node_class_name = "Node" + node_name[0].upper() + node_name[1:]
        

def gen_obj(module_name, parent_class, sub_name):
    defn_module_name = "defn_" + module_name
    exec(f"import {defn_module_name}", globals(), locals())
    globals()[defn_module_name] = locals()[defn_module_name]
    module = eval(defn_module_name)
    import pdb; pdb.set_trace()
    print("xx") 

#gen_obj("system", "System", "Sub1")

if __name__ = "__main__":
    parser = argparse.ArgumentParser(
        description = "Unified Diag Framework.  Version {diag_version}",
        formatter_class = argparse.RawTextHelpFormatter,
    )

    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("node", help="node path")

    # TBD add tree level value, default to -1
    parser.add_argument("-t", "--tree", action="store_true", help="")

    args = parser.parse_args()

    if args.verbose:
        verbose = args.verbose

    session = Session()

    session.run()
