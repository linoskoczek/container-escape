class Challenge:

    instances = {}  # key: challenge, value: status

    def __init__(self):
        self.title = ''
        self.subtitle = ''
        self.description = ''
        self.instances.append(self)

    def __del__(self):
        self.instances.remove(self)

    def run_instance(self, id):
        pass

    def build_instance(self, id):
        pass

    def create_instance_config(self, id):
        pass

    def remove_instance(self, id):
        pass
