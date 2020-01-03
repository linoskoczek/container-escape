class Challenge:

    instances = {}  # key: challenge, value: status

    def __init__(self):
        self.name = ''
        self.description = ''
        self.instances.append(self)

    def __del__(self):
        self.instances.remove(self)

    def run(self, id):
        pass

    def build(self, id):
        pass

    def create_config(self, id):
        pass

    def remove(self, id):
        pass
