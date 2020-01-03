from abc import ABC, abstractmethod


class Challenge(ABC):

    @abstractmethod
    def run_instance(self, user_id):
        pass

    @abstractmethod
    def remove_instance(self, user_id):
        pass
