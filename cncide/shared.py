import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from shared import BigArchive

__all__ = [
    "BigArchive"
]