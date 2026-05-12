from abc import ABC, abstractmethod

class Projection(ABC):
    @abstractmethod
    def apply(self, event):
        pass
