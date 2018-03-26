"""The tests for the discovery component."""
import asyncio
import os
from unittest.mock import patch, MagicMock

import pytest

from homeassistant.bootstrap import async_setup_component
from homeassistant.components import discovery
from homeassistant.util.dt import utcnow

from tests.common import mock_coro, async_fire_time_changed

# One might consider to "mock" services, but it's easy enough to just use
# what is already available.
SERVICE = 'yamaha'
SERVICE_COMPONENT = 'media_player'

SERVICE_NO_PLATFORM = 'hass_ios'
SERVICE_NO_PLATFORM_COMPONENT = 'ios'
SERVICE_INFO = {'key': 'value'}  # Can be anything

UNKNOWN_SERVICE = 'this_service_will_never_be_supported'

BASE_CONFIG = {
    discovery.DOMAIN: {
        'ignore': []
    }
}

IGNORE_CONFIG = {
    discovery.DOMAIN: {
        'ignore': [SERVICE_NO_PLATFORM]
    }
}


@pytest.fixture(autouse=True)
def netdisco_mock():
    """Mock netdisco."""
    with patch.dict('sys.modules', {
        'netdisco.discovery': MagicMock(),
    }):
        yield


@asyncio.coroutine
def mock_discovery(hass, discoveries, config=BASE_CONFIG):
    """Helper to mock discoveries."""
    result = yield from async_setup_component(hass, 'discovery', config)
    assert result

    yield from hass.async_start()

    with patch.object(discovery, '_discover', discoveries), \
            patch('homeassistant.components.discovery.async_discover',
                  return_value=mock_coro()) as mock_discover, \
            patch('homeassistant.components.discovery.async_load_platform',
                  return_value=mock_coro()) as mock_platform:
        async_fire_time_changed(hass, utcnow())
        # Work around an issue where our loop.call_soon not get caught
        yield from hass.async_block_till_done()
        yield from hass.async_block_till_done()

    return mock_discover, mock_platform


@asyncio.coroutine
def test_unknown_service(hass):
    """Test that unknown service is ignored."""
    def discover(netdisco):
        """Fake discovery."""
        return [('this_service_will_never_be_supported', {'info': 'some'})]

    mock_discover, mock_platform = yield from mock_discovery(hass, discover)

    assert not mock_discover.called
    assert not mock_platform.called


@asyncio.coroutine
def test_load_platform(hass):
    """Test load a platform."""
    def discover(netdisco):
        """Fake discovery."""
        return [(SERVICE, SERVICE_INFO)]

    mock_discover, mock_platform = yield from mock_discovery(hass, discover)

    assert not mock_discover.called
    assert mock_platform.called
    mock_platform.assert_called_with(
        hass, SERVICE_COMPONENT, SERVICE, SERVICE_INFO, BASE_CONFIG)


@asyncio.coroutine
def test_load_component(hass):
    """Test load a component."""
    def discover(netdisco):
        """Fake discovery."""
        return [(SERVICE_NO_PLATFORM, SERVICE_INFO)]

    mock_discover, mock_platform = yield from mock_discovery(hass, discover)

    assert mock_discover.called
    assert not mock_platform.called
    mock_discover.assert_called_with(
        hass, SERVICE_NO_PLATFORM, SERVICE_INFO,
        SERVICE_NO_PLATFORM_COMPONENT, BASE_CONFIG)


@asyncio.coroutine
def test_ignore_service(hass):
    """Test ignore service."""
    def discover(netdisco):
        """Fake discovery."""
        return [(SERVICE_NO_PLATFORM, SERVICE_INFO)]

    mock_discover, mock_platform = yield from mock_discovery(hass, discover,
                                                             IGNORE_CONFIG)

    assert not mock_discover.called
    assert not mock_platform.called


@asyncio.coroutine
def test_discover_duplicates(hass):
    """Test load a component."""
    def discover(netdisco):
        """Fake discovery."""
        return [(SERVICE_NO_PLATFORM, SERVICE_INFO),
                (SERVICE_NO_PLATFORM, SERVICE_INFO)]

    mock_discover, mock_platform = yield from mock_discovery(hass, discover)

    assert mock_discover.called
    assert mock_discover.call_count == 1
    assert not mock_platform.called
    mock_discover.assert_called_with(
        hass, SERVICE_NO_PLATFORM, SERVICE_INFO,
        SERVICE_NO_PLATFORM_COMPONENT, BASE_CONFIG)


@asyncio.coroutine
def test_load_component_hassio(hass):
    """Test load hassio component."""
    def discover(netdisco):
        """Fake discovery."""
        return []

    with patch.dict(os.environ, {'HASSIO': "FAKE_HASSIO"}), \
            patch('homeassistant.components.hassio.async_setup',
                  return_value=mock_coro(return_value=True)) as mock_hassio:
        yield from mock_discovery(hass, discover)

    assert mock_hassio.called
