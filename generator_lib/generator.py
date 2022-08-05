from typing import List
from abc import ABC, abstractmethod
from jinja2 import Environment, PackageLoader, select_autoescape

from . import jinja2_package


class BaseGenerator(ABC):
    @abstractmethod
    def generate(self):
        pass


class BaseContainer(BaseGenerator, ABC):
    pass


class BaseContainerConfig(BaseGenerator, ABC):
    pass


class ACAPYContainer(BaseContainer):
    """
    Contains information to setup a container running acapy
    """

    def generate(self) -> List[tuple]:
        """

        Returns: [(file name, config class),]
        - Example: [(Dockerfile, DockerConfig),]
        - Example: [(pyproject.toml, PoetryConfig),]
        """
        pass


class DockerConfig(BaseContainerConfig):
    def __init__(self):
        """
        Initialize the variables needed to generate a docker-compose and/or
        Dockerfile configuration.
        """
        self.templateName = "Dockerfile.template"
        self.volumes = []
        self.links = []
        self.imageName = None
        self.needsBuild = False
        self.baseImage = "bcgovimages/aries-cloudagent:0.7.4"

    def generate(self):
        """
        Generates Dockerfile
        """
        env = Environment(
            loader=PackageLoader("jinja2_package"),
            autoescape=select_autoescape(),
        )
        dockerfile_template = env.get_template("templateDockerfile")
        dockerfile_template.render(config=self)

    def set_name(self, imageName):
        self.imageName = imageName


class PoetryConfig(BaseContainerConfig):
    def __init__(self):
        """
        Initialize the variables needed to generate a
        pyproject.toml file.
        """
        self.dependencies = []

    def add_dependency(self, dep):
        """
        Add a dependency to the poetry requirements
        """
        self.dependencies.append(dep)

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
