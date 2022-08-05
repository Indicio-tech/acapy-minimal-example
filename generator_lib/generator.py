from typing import List
from abc import ABC, abstractmethod

class BaseGenerator:

    @abstractmethod
    def generate(self):
        pass

class Container(BaseGenerator):
    pass

class ContainerConfig(BaseGenerator):
    pass

class ACAPYContainer(Container):
    def generate(self) -> List[tuple]:
        """
        Returns: [(file name, file contents),]
        """
        pass

class PoetryConfig(ContainerConfig):
    def generate(self):
        pass

class Generator(BaseGenerator):

    def __init__(self):
        self.containers = list()

    def create_acapy(self) -> ACAPYContainer:
        """ """
        acapy = ACAPYContainer()
        self.containers.append(acapy)
        return acapy

    def generate(self):
        """Create a docker-compose file from
        list of containers
        """
        for container in self.containers:
            pass
        return "hi"