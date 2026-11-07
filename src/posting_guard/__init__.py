"""Flag hidden text, invisible Unicode and prompt-injection lines in job postings before an LLM reads them."""
__version__ = "0.2.0"

from ._patterns import Finding
from .core import CLEAN, REVIEW, Report, scan

__all__ = ["scan", "Report", "Finding", "CLEAN", "REVIEW", "__version__"]
