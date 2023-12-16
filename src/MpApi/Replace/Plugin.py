from abc import ABC, abstractmethod
from mpapi.search import Search


class Plugin(ABC):
    @abstractmethod
    def Input(self) -> dict:
        pass

    @abstractmethod
    def loop() -> str:  # returns an xpath as str used to loop thru result xml
        pass

    @abstractmethod
    def onItem() -> callable:
        pass

    @abstractmethod
    def search(self, Id: int, limit: int) -> Search:
        pass
