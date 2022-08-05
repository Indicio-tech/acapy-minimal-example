from typing import List
from abc import ABC, abstractmethod

class BaseGenerator(ABC):

    @abstractmethod
    def generate(self):
        pass

class BaseContainer(BaseGenerator, ABC):
    pass

class BaseContainerConfig(BaseGenerator, ABC):
    pass

class ACAPYContainer(BaseContainer):
    def generate(self) -> List[tuple]:
        """

        Returns: [(file name, config class),]
        - Example: [(Dockerfile, DockerConfig),]
        - Example: [(pyproject.toml, PoetryConfig),]
        """
        pass

class DockerConfig(ContainerConfig):
    def generate(self):
        """Generates Dockerfile

        TODO: needs to contain volume declaration
        """
        pass

class PoetryConfig(BaseContainerConfig):
    def generate(self):
        """Generates pyproject.toml file"""
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