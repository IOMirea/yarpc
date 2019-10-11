# yarpc - yet another RPC
# Copyright (C) 2019  Eugene Ershov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import uuid
import logging

from typing import Any, Dict, Callable, Optional

from .abc import ABCServer
from .enums import StatusCode
from .typing import _CommandType
from .request import Request
from .constants import NoValue
from .connection import Connection

log = logging.getLogger(__name__)


class Server(Connection, ABCServer):
    """RPC server listens for commands from clients and sends responses."""

    # # Using __slots__ causes issues with ClintServer
    # __slots__ = ("_node", "_commands")

    def __init__(self, *args: Any, node: Optional[str] = None, **kwargs: Any):
        super().__init__(*args, **kwargs)

        self._node = uuid.uuid4().hex if node is None else node
        self._commands: Dict[int, _CommandType] = {}

    def command(self, index: int) -> Callable[[_CommandType], None]:
        def inner(func: _CommandType) -> None:
            self.register_command(index, func)

        return inner

    def register_command(self, index: int, fn: _CommandType) -> int:
        if index in self._commands:
            raise ValueError("Command with index %d already registered", index)

        self._commands[index] = fn

        return index

    def remove_command(self, index: int) -> _CommandType:
        if index not in self._commands:
            raise ValueError("Command with index %d is not registered", index)

        return self._commands.pop(index)

    async def start(self, *args: Any, **kwargs: Any) -> None:
        """Starts command processing."""

        log.info("running on node %s", self.node)

        await super().start(*args, **kwargs)

    def _make_request(self, data: Any) -> Optional[Request]:
        return Request.from_data(self, data)

    async def _handle_request(self, request: Request) -> None:
        log.info("received command %d", request.command_index)

        fn = self._commands.get(request.command_index)
        if fn is None:
            log.warning("unknown command %d", request.command_index)

            await request._reply_with_status(status=StatusCode.UNKNOWN_COMMAND)

            return

        try:
            command = fn(request, **request._data)
        except TypeError as e:
            log.error("bad arguments given to %d: %s", request.command_index, str(e))

            await request._reply_with_status(str(e), StatusCode.BAD_PARAMS)

            return

        try:
            command_result = await command
        except Exception as e:
            log.error(
                "error calling command %d %s: %s",
                request.command_index,
                e.__class__.__name__,
                str(e),
            )

            await request._reply_with_status(str(e), StatusCode.INTERNAL_ERROR)

            return

        if command_result is None:
            # Special case, should be documented.
            # returning None is allowed using request.reply
            return

        await request.reply(command_result)

    async def reply(
        self, *, address: Optional[str], status: StatusCode, data: Any
    ) -> None:
        if address is None:
            log.debug("no address, unable to respond")
            return

        payload = {"s": status.value, "n": self.node, "a": address}

        if data is not NoValue:
            payload["d"] = data

        await self._send_response(self._dumps(payload))

    @property
    def node(self) -> str:
        return self._node

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self._name} node={self.node}>"
