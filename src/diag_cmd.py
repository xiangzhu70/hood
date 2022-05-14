class Command:
    def __init__(self, cmd_name):
        self.name = cmd_name

    def show(self):
        print(f"Command name = {self.name}")

    def run(self):
        print(f"-- Command {self.name} run")


