"""
AgentWork SDK
Python client for AgentWork Infrastructure API
"""

__version__ = "0.1.0"
__author__ = "OpenClaw Bot"

from .client import (
    AgentWorkClient,
    AgentWorkClientSync,
    Message,
    Inbox
)

__all__ = [
    'AgentWorkClient',
    'AgentWorkClientSync',
    'Message',
    'Inbox'
]
