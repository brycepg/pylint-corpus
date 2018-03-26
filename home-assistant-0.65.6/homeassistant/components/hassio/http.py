"""
Exposes regular REST commands as services.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/hassio/
"""
import asyncio
import logging
import os
import re

import async_timeout
import aiohttp
from aiohttp import web
from aiohttp.hdrs import CONTENT_TYPE
from aiohttp.web_exceptions import HTTPBadGateway

from homeassistant.const import CONTENT_TYPE_TEXT_PLAIN
from homeassistant.components.http import KEY_AUTHENTICATED, HomeAssistantView

_LOGGER = logging.getLogger(__name__)

X_HASSIO = 'X-HASSIO-KEY'

NO_TIMEOUT = {
    re.compile(r'^homeassistant/update$'),
    re.compile(r'^host/update$'),
    re.compile(r'^supervisor/update$'),
    re.compile(r'^addons/[^/]*/update$'),
    re.compile(r'^addons/[^/]*/install$'),
    re.compile(r'^addons/[^/]*/rebuild$'),
    re.compile(r'^snapshots/.*/full$'),
    re.compile(r'^snapshots/.*/partial$'),
    re.compile(r'^snapshots/[^/]*/upload$'),
    re.compile(r'^snapshots/[^/]*/download$'),
}

NO_AUTH = {
    re.compile(r'^app-(es5|latest)/(index|hassio-app).html$'),
    re.compile(r'^addons/[^/]*/logo$')
}


class HassIOView(HomeAssistantView):
    """Hass.io view to handle base part."""

    name = "api:hassio"
    url = "/api/hassio/{path:.+}"
    requires_auth = False

    def __init__(self, host, websession):
        """Initialize a Hass.io base view."""
        self._host = host
        self._websession = websession

    @asyncio.coroutine
    def _handle(self, request, path):
        """Route data to Hass.io."""
        if _need_auth(path) and not request[KEY_AUTHENTICATED]:
            return web.Response(status=401)

        client = yield from self._command_proxy(path, request)

        data = yield from client.read()
        if path.endswith('/logs'):
            return _create_response_log(client, data)
        return _create_response(client, data)

    get = _handle
    post = _handle

    @asyncio.coroutine
    def _command_proxy(self, path, request):
        """Return a client request with proxy origin for Hass.io supervisor.

        This method is a coroutine.
        """
        read_timeout = _get_timeout(path)
        hass = request.app['hass']

        try:
            data = None
            headers = {X_HASSIO: os.environ.get('HASSIO_TOKEN', "")}
            with async_timeout.timeout(10, loop=hass.loop):
                data = yield from request.read()
                if data:
                    headers[CONTENT_TYPE] = request.content_type
                else:
                    data = None

            method = getattr(self._websession, request.method.lower())
            client = yield from method(
                "http://{}/{}".format(self._host, path), data=data,
                headers=headers, timeout=read_timeout
            )

            return client

        except aiohttp.ClientError as err:
            _LOGGER.error("Client error on api %s request %s", path, err)

        except asyncio.TimeoutError:
            _LOGGER.error("Client timeout error on API request %s", path)

        raise HTTPBadGateway()


def _create_response(client, data):
    """Convert a response from client request."""
    return web.Response(
        body=data,
        status=client.status,
        content_type=client.content_type,
    )


def _create_response_log(client, data):
    """Convert a response from client request."""
    # Remove color codes
    log = re.sub(r"\x1b(\[.*?[@-~]|\].*?(\x07|\x1b\\))", "", data.decode())

    return web.Response(
        text=log,
        status=client.status,
        content_type=CONTENT_TYPE_TEXT_PLAIN,
    )


def _get_timeout(path):
    """Return timeout for a URL path."""
    for re_path in NO_TIMEOUT:
        if re_path.match(path):
            return 0
    return 300


def _need_auth(path):
    """Return if a path need authentication."""
    for re_path in NO_AUTH:
        if re_path.match(path):
            return False
    return True
