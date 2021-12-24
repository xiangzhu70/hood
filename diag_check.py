class Check:
    def __init__(self, name):
        self.name = name
        self.ok_necessary_conditions = [
        # tuples of (check, bool)
        ]

    def show(self):
        print(f"Check name = {self.name}")
        print("Dependencies:")
        for dep in self.deps:
            print(dep)
