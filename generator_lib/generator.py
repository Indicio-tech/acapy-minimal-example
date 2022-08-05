from typing import List

class Container:
    pass

class ContainerConfig:
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

class Generator:

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