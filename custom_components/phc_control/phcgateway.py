import asyncio
import base64
import logging
import zipfile
from attr import dataclass
import requests
import async_timeout

from aiohttp.client import ClientError, ClientResponseError, ClientSession
from aiohttp.hdrs import METH_DELETE, METH_GET, METH_PUT

import xml.etree.ElementTree as ET

from .const import DimmerState, OutputState

_LOGGER = logging.getLogger(__name__)


class PHCException(Exception):
    """Base error for python-homewizard-energy."""


class RequestError(PHCException):
    """Base error for python-homewizard-energy."""


class DisabledError(PHCException):
    """Base error for python-homewizard-energy."""


@dataclass
class OutputDeviceDescription:
    type: str
    address: int
    channels: dict[int, str]


class PHCGateway:
    _close_session: bool = False
    _request_timeout: int = 10
    _cached_output_modules: list[OutputDeviceDescription]
    _cached_dimmer_modules: list[OutputDeviceDescription]

    def __init__(
        self, host, clientsession: ClientSession = None, timeout: int = 10
    ) -> None:
        self._host = host
        self._session = clientsession
        self._request_timeout = timeout
        self._cached_output_modules = None
        self._cached_dimmer_modules = None

    @property
    def host(self) -> str:
        """Return the hostname of the device.

        Returns:
            host: The used host

        """
        return self._host

    def get_output_status(self, address) -> OutputState:
        commandText = f'<?xml version="1.0" encoding="UTF-8"?><methodCall><methodName>service.stm.sendTelegram</methodName><params><param><value><i4>0</i4></value></param><param><value><i4>{64 + address}</i4></value></param><param><value><i4>1</i4></value></param></params></methodCall>'
        response = requests.post(
            f"http://{self._host}:6680/", commandText, timeout=1500
        )
        rr = ET.fromstring(response.text)
        status = int(rr.findall("./params/param/value/array/data/value/i4")[-1].text)

        res = [True] * 8
        for addr in range(0, 8):
            res[addr] = status & pow(2, addr) > 0

        state = OutputState(states=res)
        return state

    def turn_output_on(self, address: int, channel: int) -> None:
        """Turn channel on."""
        return self.output_command(address, channel, 2)
        return None

    def turn_output_off(self, address: int, channel: int) -> None:
        """Turn channel off."""
        return self.output_command(address, channel, 3)
        return None

    def output_command(self, address: int, channel: int, command: int) -> None:
        """Send command for channel to PHC."""
        commandText = f'<?xml version="1.0" encoding="UTF-8"?><methodCall><methodName>service.stm.sendTelegram</methodName><params><param><value><i4>0</i4></value></param><param><value><i4>{(64 + address)}</i4></value></param><param><value><i4>{(channel * 32 + command)}</i4></value></param></params></methodCall>'
        response = requests.post(
            f"http://{self._host}:6680/", commandText, timeout=1500
        )
        return None

    def get_project(self) -> str:
        """download project file"""
        filename = f'/tmp/phc_{self._host.replace(".", "_")}.zip'
        dirname = f'/tmp/phc_{self._host.replace(".", "_")}'
        with open(filename, "wb") as result:
            for i in range(0, 5):
                r = requests.post(
                    f"http://{self._host}:6680/",
                    f"""<?xml version = ""1.0"" encoding=""UTF-8""?><methodCall><methodName>service.stm.readFile</methodName><params><param><value><i4>0</i4></value></param><param><value><i4>{i}</i4></value></param><param><value><i4>1</i4></value></param></params></methodCall>""",
                )
                root = ET.fromstring(r.text)
                child = root[0][0][0][0][-1][-1][0]
                decode = base64.b64decode(child.text)
                result.write(decode)
                print(len(decode))
                if len(decode) < 32768:
                    break

        zip_ref = zipfile.ZipFile(filename, "r")
        zip_ref.extractall(dirname)
        zip_ref.close()

        return dirname

    def get_output_modules(self) -> list[OutputDeviceDescription]:
        if not self._cached_output_modules is None:
            return self._cached_output_modules

        dirname = self.get_project()

        res = list[OutputDeviceDescription]()
        project = ET.parse(f"{dirname}/project.ppfx")
        for mod in project.getroot().findall("./STM/MODS[@grp='Ausgangsmodule']/MOD"):
            channels = {}
            if mod.attrib["name"].startswith("AMD230"):
                for cha in mod.findall("./CHAS[@grp='Ausgang']/CHA[@visu='true']"):
                    channels[int(cha.attrib["adr"])] = cha.text.strip().split("()")[0]
                    # print(
                    #     f"{mod.attrib['adr']}-{cha.attrib['adr']}: {cha.text.strip()}"
                    # )
            dev = OutputDeviceDescription(
                type="Output", address=int(mod.attrib["adr"]), channels=channels
            )
            res.append(dev)

        self._cached_output_modules = res
        return res

    def get_dimmer_modules(self):
        if not self._cached_dimmer_modules is None:
            return self._cached_dimmer_modules

        dirname = self.get_project()

        res = list[OutputDeviceDescription]()
        project = ET.parse(f"{dirname}/project.ppfx")
        for mod in project.getroot().findall("./STM/MODS[@grp='Dimmermodule']/MOD"):
            channels = {}
            if mod.attrib["name"].startswith("DIM_AB"):
                for cha in mod.findall("./CHAS[@grp='Ausgang']/CHA[@visu='true']"):
                    channels[int(cha.attrib["adr"])] = cha.text.strip().split("()")[0]
            dev = OutputDeviceDescription(
                type="Output", address=int(mod.attrib["adr"]), channels=channels
            )
            res.append(dev)

        self._cached_dimmer_modules = res
        return res

    def parse_dimmer_status(self, text: str) -> DimmerState:
        rr = ET.fromstring(text)
        values = rr.findall("./params/param/value/array/data/value/i4")[4:6]
        res = [int] * 2
        for addr in range(0, 2):
            res[addr] = int(values[addr].text)

        state = OutputState(states=res)
        return state

    def get_dimmer_status(self, module) -> DimmerState:
        commandText = f'<?xml version="1.0" encoding="UTF-8"?><methodCall><methodName>service.stm.sendTelegram</methodName><params><param><value><i4>0</i4></value></param><param><value><i4>{0xA0 + module}</i4></value></param><param><value><i4>1</i4></value></param></params></methodCall>'
        response = requests.post(
            f"http://{self._host}:6680/", commandText, timeout=1500
        )

        return self.parse_dimmer_status(response.text)

    def turn_dimmer_on(self, address: int, channel: int) -> None:
        """Turn channel on."""
        return self.dimmer_command(address, channel, 12)

    def turn_dimmer_set(self, address: int, channel: int, brightness: int) -> None:
        """Turn channel on."""
        time = 3
        dimlevel = brightness
        commandText = f'<?xml version="1.0" encoding="UTF-8"?><methodCall><methodName>service.stm.sendTelegram</methodName><params><param><value><i4>0</i4></value></param><param><value><i4>{160 + address}</i4></value></param><param><value><i4>{channel * 32 + 22}</i4></value></param><param><value><i4>{dimlevel}</i4></value></param><param><value><i4>{time}</i4></value></param></params></methodCall>'
        # return self.dimmer_command(address, channel, 2)
        response = requests.post(
            f"http://{self._host}:6680/", commandText, timeout=1500
        )
        return None

    def turn_dimmer_off(self, address: int, channel: int) -> None:
        """Turn channel off."""
        return self.dimmer_command(address, channel, 4)

    def dimmer_command(self, address: int, channel: int, command: int) -> None:
        """Send command for channel to PHC."""
        commandText = f'<?xml version="1.0" encoding="UTF-8"?><methodCall><methodName>service.stm.sendTelegram</methodName><params><param><value><i4>0</i4></value></param><param><value><i4>{(160 + address)}</i4></value></param><param><value><i4>{(channel * 32 + command)}</i4></value></param></params></methodCall>'
        response = requests.post(
            f"http://{self._host}:6680/", commandText, timeout=1500
        )
        return None

    async def close(self):
        """Close client session."""
        _LOGGER.debug("Closing clientsession")
        if self._session and self._close_session:
            await self._session.close()
