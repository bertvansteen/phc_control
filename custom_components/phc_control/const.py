"""Constants."""

from datetime import timedelta

from attr import dataclass
from homeassistant.const import *

DOMAIN = "phc_control"
SCAN_INTERVAL = timedelta(seconds=30)
DEFAULT_NAME = "PHC Control"
DATA_CLIENT = "client"
SERVICE_REFRESH = "refresh"

PLATFORMS = [Platform.LIGHT]


@dataclass
class OutputState:
    """State of output module."""

    states: list[bool]


@dataclass
class DimmerState:
    """State of output module."""

    states: list[int]


@dataclass
class DeviceResponseEntry:
    """Response."""

    output: dict[int, OutputState]
    dimmer: dict[int, DimmerState]
