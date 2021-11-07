from node_diag import NodeDiag

class NodeSystem(NodeDiag):

    model_class_map = {
       "ModelX": "NodeSystemModelX",
       "ModelY": "NodeSystemModelY",
    }

    @staticmethod
    def get_model():
        return None
        #return "ModelX"

    def morph_by_model(self, model=None):
        if not model:
            model = NodeSystem.get_model()
        if model in NodeSystem.model_class_map:
            self.__class__ = eval(NodeSystem.model_class_map[model])
            print(f"Morphed into {type(self).__name__}")
            self.__init__(super_init_done=True)
        
    def __init__(self, model=None):
        print(f"System init, model={model}")
        self.morph_by_model(model)
 
    def show(self):
       print(f"class name: {type(self).__name__}")

class NodeSystemModelX(System):
    def __init__(self, super_init_done=False):
        if not super_init_done:
            __super__.init()
        print("SystemModelX init")

    def modelX_method(self):
        print("at modelX_method")


if __name__ == "__main__":
  model0 = NodeSystem()
  model0.show()
  modelX = NodeSystem(model="ModelX")
  modelX.show()
  modelX.modelX_method()

