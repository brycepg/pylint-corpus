"""Helper for aiohttp webclient stuff."""
import asyncio
import ssl
import sys

import aiohttp
from aiohttp.hdrs import USER_AGENT, CONTENT_TYPE
from aiohttp import web
from aiohttp.web_exceptions import HTTPGatewayTimeout, HTTPBadGateway
import async_timeout
import certifi

from homeassistant.core import callback
from homeassistant.const import EVENT_HOMEASSISTANT_CLOSE, __version__
from homeassistant.loader import bind_hass

DATA_CONNECTOR = 'aiohttp_connector'
DATA_CONNECTOR_NOTVERIFY = 'aiohttp_connector_notverify'
DATA_CLIENTSESSION = 'aiohttp_clientsession'
DATA_CLIENTSESSION_NOTVERIFY = 'aiohttp_clientsession_notverify'
SERVER_SOFTWARE = 'HomeAssistant/{0} aiohttp/{1} Python/{2[0]}.{2[1]}'.format(
    __version__, aiohttp.__version__, sys.version_info)


@callback
@bind_hass
def async_get_clientsession(hass, verify_ssl=True):
    """Return default aiohttp ClientSession.

    This method must be run in the event loop.
    """
    if verify_ssl:
        key = DATA_CLIENTSESSION
    else:
        key = DATA_CLIENTSESSION_NOTVERIFY

    if key not in hass.data:
        hass.data[key] = async_create_clientsession(hass, verify_ssl)

    return hass.data[key]


@callback
@bind_hass
def async_create_clientsession(hass, verify_ssl=True, auto_cleanup=True,
                               **kwargs):
    """Create a new ClientSession with kwargs, i.e. for cookies.

    If auto_cleanup is False, you need to call detach() after the session
    returned is no longer used. Default is True, the session will be
    automatically detached on homeassistant_stop.

    This method must be run in the event loop.
    """
    connector = _async_get_connector(hass, verify_ssl)

    clientsession = aiohttp.ClientSession(
        loop=hass.loop,
        connector=connector,
        headers={USER_AGENT: SERVER_SOFTWARE},
        **kwargs
    )

    if auto_cleanup:
        _async_register_clientsession_shutdown(hass, clientsession)

    return clientsession


@asyncio.coroutine
@bind_hass
def async_aiohttp_proxy_web(hass, request, web_coro, buffer_size=102400,
                            timeout=10):
    """Stream websession request to aiohttp web response."""
    try:
        with async_timeout.timeout(timeout, loop=hass.loop):
            req = yield from web_coro

    except asyncio.CancelledError:
        # The user cancelled the request
        return

    except asyncio.TimeoutError as err:
        # Timeout trying to start the web request
        raise HTTPGatewayTimeout() from err

    except aiohttp.ClientError as err:
        # Something went wrong with the connection
        raise HTTPBadGateway() from err

    try:
        yield from async_aiohttp_proxy_stream(
            hass,
            request,
            req.content,
            req.headers.get(CONTENT_TYPE)
        )
    finally:
        req.close()


@bind_hass
async def async_aiohttp_proxy_stream(hass, request, stream, content_type,
                                     buffer_size=102400, timeout=10):
    """Stream a stream to aiohttp web response."""
    response = web.StreamResponse()
    response.content_type = content_type
    await response.prepare(request)

    try:
        while True:
            with async_timeout.timeout(timeout, loop=hass.loop):
                data = await stream.read(buffer_size)

            if not data:
                await response.write_eof()
                break

            await response.write(data)

    except (asyncio.TimeoutError, aiohttp.ClientError):
        # Something went wrong fetching data, close connection gracefully
        await response.write_eof()

    except asyncio.CancelledError:
        # The user closed the connection
        pass


@callback
# pylint: disable=invalid-name
def _async_register_clientsession_shutdown(hass, clientsession):
    """Register ClientSession close on Home Assistant shutdown.

    This method must be run in the event loop.
    """
    @callback
    def _async_close_websession(event):
        """Close websession."""
        clientsession.detach()

    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_CLOSE, _async_close_websession)


@callback
def _async_get_connector(hass, verify_ssl=True):
    """Return the connector pool for aiohttp.

    This method must be run in the event loop.
    """
    is_new = False

    if verify_ssl:
        if DATA_CONNECTOR not in hass.data:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            ssl_context.load_verify_locations(cafile=certifi.where(),
                                              capath=None)
            connector = aiohttp.TCPConnector(loop=hass.loop,
                                             ssl_context=ssl_context)
            hass.data[DATA_CONNECTOR] = connector
            is_new = True
        else:
            connector = hass.data[DATA_CONNECTOR]
    else:
        if DATA_CONNECTOR_NOTVERIFY not in hass.data:
            connector = aiohttp.TCPConnector(loop=hass.loop, verify_ssl=False)
            hass.data[DATA_CONNECTOR_NOTVERIFY] = connector
            is_new = True
        else:
            connector = hass.data[DATA_CONNECTOR_NOTVERIFY]

    if is_new:
        @callback
        def _async_close_connector(event):
            """Close connector pool."""
            connector.close()

        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_CLOSE, _async_close_connector)

    return connector
