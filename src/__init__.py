"""New Relic observability for AWS Bedrock."""

from .monitor import monitor_bedrock

__version__ = "0.1.0"
__all__ = ["monitor_bedrock"] 