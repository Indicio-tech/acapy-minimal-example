"""
Generator library
"""
from typing import List
from abc import ABC, abstractmethod
import pathlib
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape

SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()


class BaseGenerator(ABC):
    """
    Base Generator class

    All generator methods must provide the following method(s)
    """

    def __init__(self):
        pass

    @abstractmethod
    def generate(self):
        """
        Interface method used to generate something.

        Typically returns something.
        """


class BaseContainer(BaseGenerator, ABC):
    """
    BaseContainer

    All container "types" (ACA-Py, Echo, Webhook Listener, and Postgress) must
    inherit all methods contained herein. Also provides common setup for all
    containers.
    """

    def __init__(self):
        super().__init__()
        self.docker_config = DockerConfig()


class BaseContainerConfig(BaseGenerator, ABC):
    """
    BaseContainerConfig

    Common type used to distinguish config objects
    """


class ACAPYContainer(BaseContainer):
    """
    Contains information to setup a container running acapy
    """

    def __init__(self):
        super().__init__()
        self.docker_config.template_name = "ACA-Py.Dockerfile.Templat"

    def generate(self) -> List[tuple]:
        """

        Returns: [(file name, config class),]
        - Example: [(Dockerfile, DockerConfig),]
        - Example: [(pyproject.toml, PoetryConfig),]
        """
        return [
            ("Dockerfile", self.docker_config),
        ]


class DockerConfig(BaseContainerConfig):
    """
    DockerConfig

    The DockerConfig class contains all necessary information to create the
    docker-compose AND Dockerfile contents for a particular container.
    """

    def __init__(self):
        """
        Initialize the variables needed to generate a docker-compose and/or
        Dockerfile configuration.
        """
        super().__init__()
        self.template_name = "Dockerfile.template"
        self.volumes = []
        self.links = []
        self.image_name = None
        self.needs_build = False
        self.base_image = "bcgovimages/aries-cloudagent:0.7.4"

    def generate(self):
        """
        Generates Dockerfile
        """
        env = Environment(
            loader=FileSystemLoader(
                [os.path.join(SCRIPT_DIR, "jinja2_package/templates")]
            ),
            autoescape=select_autoescape(),
        )
        dockerfile_template = env.get_template("templateDockerfile")
        return dockerfile_template.render(config=self)

    def set_name(self, image_name):
        """
        Set the name (and thus, image name) of the container
        """
        self.image_name = image_name


class PoetryConfig(BaseContainerConfig):
    """
    PoetryConfig

    The PoetryConfig class contains all necessary information to create the
    setup poetry for a container.
    """

    def __init__(self):
        """
        Initialize the variables needed to generate a
        pyproject.toml file.
        """
        super().__init__()
        self.dependencies = []

    def add_dependency(self, dep):
        """
        Add a dependency to the poetry requirements
        """
        self.dependencies.append(dep)

    def generate(self):
        """Generates pyproject.toml file"""


class Generator(BaseGenerator):
    """
    Generator

    The Generator class contains all necessary information to generate a
    completely reproducable environment for recreating ACA-Py problems.
    """

    def __init__(self):
        super().__init__()
        self.containers = []

    def create_acapy(self) -> ACAPYContainer:
        """
        Create an ACA-Py container object.
        """
        acapy = ACAPYContainer()
        self.containers.append(acapy)
        return acapy

    def generate(self):
        """Create a docker-compose file from
        list of containers
        """
        for container in self.containers:
            # docker = container.docker_config
            # contents = docker.generate()
            # with open("path/to/Dockerfile", "rw+") as f:
            #     f.write(contents)
            print(container)
        return "hi"
