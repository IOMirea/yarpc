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

from __future__ import annotations

import abc

from typing import Any, Dict, List, Callable, Optional, Generator

from .enums import StatusCode
from .typing import CommandType
from .response import Response

__all__ = ("ResponsesIterator", "ABCClient", "ABCServer")


class ResponsesIterator(abc.ABC):
    """
    Provides access to command responses.

    Instances can be awaited to get all responses at once or used as async iterator to
    process responses as soon as they come.
    """

    @abc.abstractmethod
    def __await__(self) -> Generator[Any, None, List[Response]]:
        ...

    @abc.abstractmethod
    def __aiter__(self) -> ResponsesIterator:
        ...

    @abc.abstractmethod
    async def __anext__(self) -> Response:
        ...


class ABCClient(abc.ABC):
    @abc.abstractmethod
    def call(
        self,
        command_index: int,
        data: Dict[str, Any] = {},
        timeout: Optional[float] = None,
        expect_responses: int = 0,
    ) -> ResponsesIterator:
        """Calls command by index."""


class ABCServer(abc.ABC):
    @abc.abstractproperty
    def node(self) -> str:
        """Node address."""

    @abc.abstractmethod
    def command(self, index: int) -> Callable[[CommandType], None]:
        ...

    @abc.abstractmethod
    def register_command(self, index: int, fn: CommandType) -> int:
        ...

    @abc.abstractmethod
    def remove_command(self, index: int) -> CommandType:
        ...

    @abc.abstractmethod
    async def reply(
        self, *, address: Optional[str], status: StatusCode, data: Any
    ) -> None:
        """Sends response to address (if address is present)."""
