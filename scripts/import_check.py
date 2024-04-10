# BEGIN import check
# This import check was added to the generated models file by generate-models.sh
import importlib

try:
    importlib.import_module("pydantic")
except ImportError:
    raise Exception(
        "Pydantic is required to use models; please install the pydantic extra."
    )
# END import check
