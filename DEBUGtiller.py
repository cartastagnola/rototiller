class DebugGlobals:
    cc_text = "cc_text"

    def __init__(self):
        self.text = 'obj_text'

    @classmethod
    def mod_cc(cls, text):
        cls.cc_text = text

    def mod_obj(self, text):
        self.text = text


DEBUG_OBJ = DebugGlobals()

