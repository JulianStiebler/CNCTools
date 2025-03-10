import sys
import os

 # Add parent directory to path to allow importing from big module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from big.big import BigArchive

__all__ = [
    "BigArchive"
]