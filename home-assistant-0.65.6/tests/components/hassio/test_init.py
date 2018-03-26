"""The tests for the hassio component."""
import asyncio
import os
from unittest.mock import patch, Mock

from homeassistant.setup import async_setup_component
from homeassistant.components.hassio import async_check_config

from tests.common import mock_coro


@asyncio.coroutine
def test_setup_api_ping(hass, aioclient_mock):
    """Test setup with API ping."""
    aioclient_mock.get(
        "http://127.0.0.1/supervisor/ping", json={'result': 'ok'})
    aioclient_mock.get(
        "http://127.0.0.1/homeassistant/info", json={
            'result': 'ok', 'data': {'last_version': '10.0'}})

    with patch.dict(os.environ, {'HASSIO': "127.0.0.1"}):
        result = yield from async_setup_component(hass, 'hassio', {})
        assert result

    assert aioclient_mock.call_count == 2
    assert hass.components.hassio.get_homeassistant_version() == "10.0"
    assert hass.components.hassio.is_hassio()


@asyncio.coroutine
def test_setup_api_push_api_data(hass, aioclient_mock):
    """Test setup with API push."""
    aioclient_mock.get(
        "http://127.0.0.1/supervisor/ping", json={'result': 'ok'})
    aioclient_mock.get(
        "http://127.0.0.1/homeassistant/info", json={
            'result': 'ok', 'data': {'last_version': '10.0'}})
    aioclient_mock.post(
        "http://127.0.0.1/homeassistant/options", json={'result': 'ok'})

    with patch.dict(os.environ, {'HASSIO': "127.0.0.1"}):
        result = yield from async_setup_component(hass, 'hassio', {
            'http': {
                'api_password': "123456",
                'server_port': 9999
            },
            'hassio': {}
        })
        assert result

    assert aioclient_mock.call_count == 3
    assert not aioclient_mock.mock_calls[1][2]['ssl']
    assert aioclient_mock.mock_calls[1][2]['password'] == "123456"
    assert aioclient_mock.mock_calls[1][2]['port'] == 9999
    assert aioclient_mock.mock_calls[1][2]['watchdog']


@asyncio.coroutine
def test_setup_api_push_api_data_server_host(hass, aioclient_mock):
    """Test setup with API push with active server host."""
    aioclient_mock.get(
        "http://127.0.0.1/supervisor/ping", json={'result': 'ok'})
    aioclient_mock.get(
        "http://127.0.0.1/homeassistant/info", json={
            'result': 'ok', 'data': {'last_version': '10.0'}})
    aioclient_mock.post(
        "http://127.0.0.1/homeassistant/options", json={'result': 'ok'})

    with patch.dict(os.environ, {'HASSIO': "127.0.0.1"}):
        result = yield from async_setup_component(hass, 'hassio', {
            'http': {
                'api_password': "123456",
                'server_port': 9999,
                'server_host': "127.0.0.1"
            },
            'hassio': {}
        })
        assert result

    assert aioclient_mock.call_count == 3
    assert not aioclient_mock.mock_calls[1][2]['ssl']
    assert aioclient_mock.mock_calls[1][2]['password'] == "123456"
    assert aioclient_mock.mock_calls[1][2]['port'] == 9999
    assert not aioclient_mock.mock_calls[1][2]['watchdog']


@asyncio.coroutine
def test_setup_api_push_api_data_default(hass, aioclient_mock):
    """Test setup with API push default data."""
    aioclient_mock.get(
        "http://127.0.0.1/supervisor/ping", json={'result': 'ok'})
    aioclient_mock.get(
        "http://127.0.0.1/homeassistant/info", json={
            'result': 'ok', 'data': {'last_version': '10.0'}})
    aioclient_mock.post(
        "http://127.0.0.1/homeassistant/options", json={'result': 'ok'})

    with patch.dict(os.environ, {'HASSIO': "127.0.0.1"}):
        result = yield from async_setup_component(hass, 'hassio', {
            'http': {},
            'hassio': {}
        })
        assert result

    assert aioclient_mock.call_count == 3
    assert not aioclient_mock.mock_calls[1][2]['ssl']
    assert aioclient_mock.mock_calls[1][2]['password'] is None
    assert aioclient_mock.mock_calls[1][2]['port'] == 8123


@asyncio.coroutine
def test_setup_core_push_timezone(hass, aioclient_mock):
    """Test setup with API push default data."""
    aioclient_mock.get(
        "http://127.0.0.1/supervisor/ping", json={'result': 'ok'})
    aioclient_mock.get(
        "http://127.0.0.1/homeassistant/info", json={
            'result': 'ok', 'data': {'last_version': '10.0'}})
    aioclient_mock.post(
        "http://127.0.0.1/supervisor/options", json={'result': 'ok'})

    with patch.dict(os.environ, {'HASSIO': "127.0.0.1"}):
        result = yield from async_setup_component(hass, 'hassio', {
            'hassio': {},
            'homeassistant': {
                'time_zone': 'testzone',
            },
        })
        assert result

    assert aioclient_mock.call_count == 3
    assert aioclient_mock.mock_calls[1][2]['timezone'] == "testzone"


@asyncio.coroutine
def test_setup_hassio_no_additional_data(hass, aioclient_mock):
    """Test setup with API push default data."""
    aioclient_mock.get(
        "http://127.0.0.1/supervisor/ping", json={'result': 'ok'})
    aioclient_mock.get(
        "http://127.0.0.1/homeassistant/info", json={
            'result': 'ok', 'data': {'last_version': '10.0'}})
    aioclient_mock.get(
        "http://127.0.0.1/homeassistant/info", json={'result': 'ok'})

    with patch.dict(os.environ, {'HASSIO': "127.0.0.1"}), \
            patch.dict(os.environ, {'HASSIO_TOKEN': "123456"}):
        result = yield from async_setup_component(hass, 'hassio', {
            'hassio': {},
        })
        assert result

    assert aioclient_mock.call_count == 2
    assert aioclient_mock.mock_calls[-1][3]['X-HASSIO-KEY'] == "123456"


@asyncio.coroutine
def test_fail_setup_without_environ_var(hass):
    """Fail setup if no environ variable set."""
    with patch.dict(os.environ, {}, clear=True):
        result = yield from async_setup_component(hass, 'hassio', {})
        assert not result


@asyncio.coroutine
def test_fail_setup_cannot_connect(hass):
    """Fail setup if cannot connect."""
    with patch.dict(os.environ, {'HASSIO': "127.0.0.1"}), \
            patch('homeassistant.components.hassio.HassIO.is_connected',
                  Mock(return_value=mock_coro(None))):
        result = yield from async_setup_component(hass, 'hassio', {})
        assert not result

    assert not hass.components.hassio.is_hassio()


@asyncio.coroutine
def test_service_register(hassio_env, hass):
    """Check if service will be setup."""
    assert (yield from async_setup_component(hass, 'hassio', {}))
    assert hass.services.has_service('hassio', 'addon_start')
    assert hass.services.has_service('hassio', 'addon_stop')
    assert hass.services.has_service('hassio', 'addon_restart')
    assert hass.services.has_service('hassio', 'addon_stdin')
    assert hass.services.has_service('hassio', 'host_shutdown')
    assert hass.services.has_service('hassio', 'host_reboot')
    assert hass.services.has_service('hassio', 'host_reboot')
    assert hass.services.has_service('hassio', 'snapshot_full')
    assert hass.services.has_service('hassio', 'snapshot_partial')
    assert hass.services.has_service('hassio', 'restore_full')
    assert hass.services.has_service('hassio', 'restore_partial')


@asyncio.coroutine
def test_service_calls(hassio_env, hass, aioclient_mock):
    """Call service and check the API calls behind that."""
    assert (yield from async_setup_component(hass, 'hassio', {}))

    aioclient_mock.post(
        "http://127.0.0.1/addons/test/start", json={'result': 'ok'})
    aioclient_mock.post(
        "http://127.0.0.1/addons/test/stop", json={'result': 'ok'})
    aioclient_mock.post(
        "http://127.0.0.1/addons/test/restart", json={'result': 'ok'})
    aioclient_mock.post(
        "http://127.0.0.1/addons/test/stdin", json={'result': 'ok'})
    aioclient_mock.post(
        "http://127.0.0.1/host/shutdown", json={'result': 'ok'})
    aioclient_mock.post(
        "http://127.0.0.1/host/reboot", json={'result': 'ok'})
    aioclient_mock.post(
        "http://127.0.0.1/snapshots/new/full", json={'result': 'ok'})
    aioclient_mock.post(
        "http://127.0.0.1/snapshots/new/partial", json={'result': 'ok'})
    aioclient_mock.post(
        "http://127.0.0.1/snapshots/test/restore/full", json={'result': 'ok'})
    aioclient_mock.post(
        "http://127.0.0.1/snapshots/test/restore/partial",
        json={'result': 'ok'})

    yield from hass.services.async_call(
        'hassio', 'addon_start', {'addon': 'test'})
    yield from hass.services.async_call(
        'hassio', 'addon_stop', {'addon': 'test'})
    yield from hass.services.async_call(
        'hassio', 'addon_restart', {'addon': 'test'})
    yield from hass.services.async_call(
        'hassio', 'addon_stdin', {'addon': 'test', 'input': 'test'})
    yield from hass.async_block_till_done()

    assert aioclient_mock.call_count == 4
    assert aioclient_mock.mock_calls[-1][2] == 'test'

    yield from hass.services.async_call('hassio', 'host_shutdown', {})
    yield from hass.services.async_call('hassio', 'host_reboot', {})
    yield from hass.async_block_till_done()

    assert aioclient_mock.call_count == 6

    yield from hass.services.async_call('hassio', 'snapshot_full', {})
    yield from hass.services.async_call('hassio', 'snapshot_partial', {
        'addons': ['test'],
        'folders': ['ssl'],
        'password': "123456",
    })
    yield from hass.async_block_till_done()

    assert aioclient_mock.call_count == 8
    assert aioclient_mock.mock_calls[-1][2] == {
        'addons': ['test'], 'folders': ['ssl'], 'password': "123456"}

    yield from hass.services.async_call('hassio', 'restore_full', {
        'snapshot': 'test',
    })
    yield from hass.services.async_call('hassio', 'restore_partial', {
        'snapshot': 'test',
        'homeassistant': False,
        'addons': ['test'],
        'folders': ['ssl'],
        'password': "123456",
    })
    yield from hass.async_block_till_done()

    assert aioclient_mock.call_count == 10
    assert aioclient_mock.mock_calls[-1][2] == {
        'addons': ['test'], 'folders': ['ssl'], 'homeassistant': False,
        'password': "123456"
    }


@asyncio.coroutine
def test_service_calls_core(hassio_env, hass, aioclient_mock):
    """Call core service and check the API calls behind that."""
    assert (yield from async_setup_component(hass, 'hassio', {}))

    aioclient_mock.post(
        "http://127.0.0.1/homeassistant/restart", json={'result': 'ok'})
    aioclient_mock.post(
        "http://127.0.0.1/homeassistant/stop", json={'result': 'ok'})
    aioclient_mock.post(
        "http://127.0.0.1/homeassistant/check", json={'result': 'ok'})

    yield from hass.services.async_call('homeassistant', 'stop')
    yield from hass.async_block_till_done()

    assert aioclient_mock.call_count == 1

    yield from hass.services.async_call('homeassistant', 'check_config')
    yield from hass.async_block_till_done()

    assert aioclient_mock.call_count == 2

    yield from hass.services.async_call('homeassistant', 'restart')
    yield from hass.async_block_till_done()

    assert aioclient_mock.call_count == 4


@asyncio.coroutine
def test_check_config_ok(hassio_env, hass, aioclient_mock):
    """Check Config that is okay."""
    assert (yield from async_setup_component(hass, 'hassio', {}))

    aioclient_mock.post(
        "http://127.0.0.1/homeassistant/check", json={'result': 'ok'})

    assert (yield from async_check_config(hass)) is None


@asyncio.coroutine
def test_check_config_fail(hassio_env, hass, aioclient_mock):
    """Check Config that is wrong."""
    assert (yield from async_setup_component(hass, 'hassio', {}))

    aioclient_mock.post(
        "http://127.0.0.1/homeassistant/check", json={
            'result': 'error', 'message': "Error"})

    assert (yield from async_check_config(hass)) == "Error"
