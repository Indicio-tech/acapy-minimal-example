"""Base model for use with pydantic models implementing Serde protocol."""

from typing import Any, Mapping, Type, TypeVar

try:
    from pydantic import BaseModel as PydanticBaseModel
except ImportError:
    raise Exception(
        "Pydantic is required to use models; please install the pydantic extra."
    )


T = TypeVar("T", bound="BaseModel")


class BaseModel(PydanticBaseModel):
    """BaseModel for use with pydantic models implementing Serde protocol."""

    def serialize(self):
        """Serialize the model to a dictionary."""
        return self.model_dump(by_alias=True, exclude_unset=True, exclude_none=True)

    @classmethod
    def deserialize(cls: Type[T], value: Mapping[str, Any]) -> T:
        """Deserialize a dictionary to a model."""
        return cls.model_validate(value)
