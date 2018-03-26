"""Test Customize config panel."""
import asyncio
import json
from unittest.mock import patch

from homeassistant.bootstrap import async_setup_component
from homeassistant.components import config
from homeassistant.config import DATA_CUSTOMIZE


@asyncio.coroutine
def test_get_entity(hass, test_client):
    """Test getting entity."""
    with patch.object(config, 'SECTIONS', ['customize']):
        yield from async_setup_component(hass, 'config', {})

    client = yield from test_client(hass.http.app)

    def mock_read(path):
        """Mock reading data."""
        return {
            'hello.beer': {
                'free': 'beer',
            },
            'other.entity': {
                'do': 'something',
            },
        }
    hass.data[DATA_CUSTOMIZE] = {'hello.beer': {'cold': 'beer'}}
    with patch('homeassistant.components.config._read', mock_read):
        resp = yield from client.get(
            '/api/config/customize/config/hello.beer')

    assert resp.status == 200
    result = yield from resp.json()

    assert result == {'local': {'free': 'beer'}, 'global': {'cold': 'beer'}}


@asyncio.coroutine
def test_update_entity(hass, test_client):
    """Test updating entity."""
    with patch.object(config, 'SECTIONS', ['customize']):
        yield from async_setup_component(hass, 'config', {})

    client = yield from test_client(hass.http.app)

    orig_data = {
        'hello.beer': {
            'ignored': True,
        },
        'other.entity': {
            'polling_intensity': 2,
        },
    }

    def mock_read(path):
        """Mock reading data."""
        return orig_data

    written = []

    def mock_write(path, data):
        """Mock writing data."""
        written.append(data)

    hass.states.async_set('hello.world', 'state', {'a': 'b'})
    with patch('homeassistant.components.config._read', mock_read), \
            patch('homeassistant.components.config._write', mock_write):
        resp = yield from client.post(
            '/api/config/customize/config/hello.world', data=json.dumps({
                'name': 'Beer',
                'entities': ['light.top', 'light.bottom'],
            }))

    assert resp.status == 200
    result = yield from resp.json()
    assert result == {'result': 'ok'}

    state = hass.states.get('hello.world')
    assert state.state == 'state'
    assert dict(state.attributes) == {
        'a': 'b', 'name': 'Beer', 'entities': ['light.top', 'light.bottom']}

    orig_data['hello.world']['name'] = 'Beer'
    orig_data['hello.world']['entities'] = ['light.top', 'light.bottom']

    assert written[0] == orig_data


@asyncio.coroutine
def test_update_entity_invalid_key(hass, test_client):
    """Test updating entity."""
    with patch.object(config, 'SECTIONS', ['customize']):
        yield from async_setup_component(hass, 'config', {})

    client = yield from test_client(hass.http.app)

    resp = yield from client.post(
        '/api/config/customize/config/not_entity', data=json.dumps({
            'name': 'YO',
        }))

    assert resp.status == 400


@asyncio.coroutine
def test_update_entity_invalid_json(hass, test_client):
    """Test updating entity."""
    with patch.object(config, 'SECTIONS', ['customize']):
        yield from async_setup_component(hass, 'config', {})

    client = yield from test_client(hass.http.app)

    resp = yield from client.post(
        '/api/config/customize/config/hello.beer', data='not json')

    assert resp.status == 400
