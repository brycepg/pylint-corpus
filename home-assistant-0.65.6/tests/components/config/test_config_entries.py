"""Test config entries API."""

import asyncio
from collections import OrderedDict
from unittest.mock import patch

import pytest
import voluptuous as vol

from homeassistant import config_entries as core_ce
from homeassistant.config_entries import ConfigFlowHandler, HANDLERS
from homeassistant.setup import async_setup_component
from homeassistant.components.config import config_entries
from homeassistant.loader import set_component

from tests.common import MockConfigEntry, MockModule, mock_coro_func


@pytest.fixture
def client(hass, test_client):
    """Fixture that can interact with the config manager API."""
    hass.loop.run_until_complete(async_setup_component(hass, 'http', {}))
    hass.loop.run_until_complete(config_entries.async_setup(hass))
    yield hass.loop.run_until_complete(test_client(hass.http.app))


@asyncio.coroutine
def test_get_entries(hass, client):
    """Test get entries."""
    MockConfigEntry(
       domain='comp',
       title='Test 1',
       source='bla'
    ).add_to_hass(hass)
    MockConfigEntry(
       domain='comp2',
       title='Test 2',
       source='bla2',
       state=core_ce.ENTRY_STATE_LOADED,
    ).add_to_hass(hass)
    resp = yield from client.get('/api/config/config_entries/entry')
    assert resp.status == 200
    data = yield from resp.json()
    for entry in data:
        entry.pop('entry_id')
    assert data == [
        {
            'domain': 'comp',
            'title': 'Test 1',
            'source': 'bla',
            'state': 'not_loaded'
        },
        {
            'domain': 'comp2',
            'title': 'Test 2',
            'source': 'bla2',
            'state': 'loaded',
        },
    ]


@asyncio.coroutine
def test_remove_entry(hass, client):
    """Test removing an entry via the API."""
    entry = MockConfigEntry(domain='demo')
    entry.add_to_hass(hass)
    resp = yield from client.delete(
        '/api/config/config_entries/entry/{}'.format(entry.entry_id))
    assert resp.status == 200
    data = yield from resp.json()
    assert data == {
        'require_restart': True
    }
    assert len(hass.config_entries.async_entries()) == 0


@asyncio.coroutine
def test_available_flows(hass, client):
    """Test querying the available flows."""
    with patch.object(core_ce, 'FLOWS', ['hello', 'world']):
        resp = yield from client.get(
            '/api/config/config_entries/flow_handlers')
        assert resp.status == 200
        data = yield from resp.json()
        assert data == ['hello', 'world']


############################
#  FLOW MANAGER API TESTS  #
############################


@asyncio.coroutine
def test_initialize_flow(hass, client):
    """Test we can initialize a flow."""
    class TestFlow(ConfigFlowHandler):
        @asyncio.coroutine
        def async_step_init(self, user_input=None):
            schema = OrderedDict()
            schema[vol.Required('username')] = str
            schema[vol.Required('password')] = str

            return self.async_show_form(
                title='test-title',
                step_id='init',
                description='test-description',
                data_schema=schema,
                errors={
                    'username': 'Should be unique.'
                }
            )

    with patch.dict(HANDLERS, {'test': TestFlow}):
        resp = yield from client.post('/api/config/config_entries/flow',
                                      json={'domain': 'test'})

    assert resp.status == 200
    data = yield from resp.json()

    data.pop('flow_id')

    assert data == {
        'type': 'form',
        'title': 'test-title',
        'description': 'test-description',
        'data_schema': [
            {
                'name': 'username',
                'required': True,
                'type': 'string'
            },
            {
                'name': 'password',
                'required': True,
                'type': 'string'
            }
        ],
        'errors': {
            'username': 'Should be unique.'
        }
    }


@asyncio.coroutine
def test_abort(hass, client):
    """Test a flow that aborts."""
    class TestFlow(ConfigFlowHandler):
        @asyncio.coroutine
        def async_step_init(self, user_input=None):
            return self.async_abort(reason='bla')

    with patch.dict(HANDLERS, {'test': TestFlow}):
        resp = yield from client.post('/api/config/config_entries/flow',
                                      json={'domain': 'test'})

    assert resp.status == 200
    data = yield from resp.json()
    data.pop('flow_id')
    assert data == {
        'reason': 'bla',
        'type': 'abort'
    }


@asyncio.coroutine
def test_create_account(hass, client):
    """Test a flow that creates an account."""
    set_component(
        'test', MockModule('test', async_setup_entry=mock_coro_func(True)))

    class TestFlow(ConfigFlowHandler):
        VERSION = 1

        @asyncio.coroutine
        def async_step_init(self, user_input=None):
            return self.async_create_entry(
                title='Test Entry',
                data={'secret': 'account_token'}
            )

    with patch.dict(HANDLERS, {'test': TestFlow}):
        resp = yield from client.post('/api/config/config_entries/flow',
                                      json={'domain': 'test'})

    assert resp.status == 200
    data = yield from resp.json()
    data.pop('flow_id')
    assert data == {
        'title': 'Test Entry',
        'type': 'create_entry'
    }


@asyncio.coroutine
def test_two_step_flow(hass, client):
    """Test we can finish a two step flow."""
    set_component(
        'test', MockModule('test', async_setup_entry=mock_coro_func(True)))

    class TestFlow(ConfigFlowHandler):
        VERSION = 1

        @asyncio.coroutine
        def async_step_init(self, user_input=None):
            return self.async_show_form(
                title='test-title',
                step_id='account',
                data_schema=vol.Schema({
                    'user_title': str
                }))

        @asyncio.coroutine
        def async_step_account(self, user_input=None):
            return self.async_create_entry(
                title=user_input['user_title'],
                data={'secret': 'account_token'}
            )

    with patch.dict(HANDLERS, {'test': TestFlow}):
        resp = yield from client.post('/api/config/config_entries/flow',
                                      json={'domain': 'test'})
        assert resp.status == 200
        data = yield from resp.json()
        flow_id = data.pop('flow_id')
        assert data == {
            'type': 'form',
            'title': 'test-title',
            'description': None,
            'data_schema': [
                {
                    'name': 'user_title',
                    'type': 'string'
                }
            ],
            'errors': None
        }

    with patch.dict(HANDLERS, {'test': TestFlow}):
        resp = yield from client.post(
            '/api/config/config_entries/flow/{}'.format(flow_id),
            json={'user_title': 'user-title'})
        assert resp.status == 200
        data = yield from resp.json()
        data.pop('flow_id')
        assert data == {
            'type': 'create_entry',
            'title': 'user-title',
        }


@asyncio.coroutine
def test_get_progress_index(hass, client):
    """Test querying for the flows that are in progress."""
    class TestFlow(ConfigFlowHandler):
        VERSION = 5

        @asyncio.coroutine
        def async_step_hassio(self, info):
            return (yield from self.async_step_account())

        @asyncio.coroutine
        def async_step_account(self, user_input=None):
            return self.async_show_form(
                step_id='account',
                title='Finish setup'
            )

    with patch.dict(HANDLERS, {'test': TestFlow}):
        form = yield from hass.config_entries.flow.async_init(
            'test', source='hassio')

    resp = yield from client.get('/api/config/config_entries/flow')
    assert resp.status == 200
    data = yield from resp.json()
    assert data == [
        {
            'flow_id': form['flow_id'],
            'domain': 'test',
            'source': 'hassio'
        }
    ]


@asyncio.coroutine
def test_get_progress_flow(hass, client):
    """Test we can query the API for same result as we get from init a flow."""
    class TestFlow(ConfigFlowHandler):
        @asyncio.coroutine
        def async_step_init(self, user_input=None):
            schema = OrderedDict()
            schema[vol.Required('username')] = str
            schema[vol.Required('password')] = str

            return self.async_show_form(
                title='test-title',
                step_id='init',
                description='test-description',
                data_schema=schema,
                errors={
                    'username': 'Should be unique.'
                }
            )

    with patch.dict(HANDLERS, {'test': TestFlow}):
        resp = yield from client.post('/api/config/config_entries/flow',
                                      json={'domain': 'test'})

    assert resp.status == 200
    data = yield from resp.json()

    resp2 = yield from client.get(
        '/api/config/config_entries/flow/{}'.format(data['flow_id']))

    assert resp2.status == 200
    data2 = yield from resp2.json()

    assert data == data2
