"""Component to configure Home Assistant via an API."""
import asyncio
import os

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.const import EVENT_COMPONENT_LOADED, CONF_ID
from homeassistant.setup import (
    async_prepare_setup_platform, ATTR_COMPONENT)
from homeassistant.components.http import HomeAssistantView
from homeassistant.util.yaml import load_yaml, dump

DOMAIN = 'config'
DEPENDENCIES = ['http']
SECTIONS = ('core', 'customize', 'group', 'hassbian', 'automation', 'script',
            'entity_registry')
ON_DEMAND = ('zwave',)
FEATURE_FLAGS = ('config_entries',)


@asyncio.coroutine
def async_setup(hass, config):
    """Set up the config component."""
    global SECTIONS

    yield from hass.components.frontend.async_register_built_in_panel(
        'config', 'config', 'mdi:settings')

    # Temporary way of allowing people to opt-in for unreleased config sections
    for key, value in config.get(DOMAIN, {}).items():
        if key in FEATURE_FLAGS and value:
            SECTIONS += (key,)

    @asyncio.coroutine
    def setup_panel(panel_name):
        """Set up a panel."""
        panel = yield from async_prepare_setup_platform(
            hass, config, DOMAIN, panel_name)

        if not panel:
            return

        success = yield from panel.async_setup(hass)

        if success:
            key = '{}.{}'.format(DOMAIN, panel_name)
            hass.bus.async_fire(EVENT_COMPONENT_LOADED, {ATTR_COMPONENT: key})
            hass.config.components.add(key)

    tasks = [setup_panel(panel_name) for panel_name in SECTIONS]

    for panel_name in ON_DEMAND:
        if panel_name in hass.config.components:
            tasks.append(setup_panel(panel_name))

    if tasks:
        yield from asyncio.wait(tasks, loop=hass.loop)

    @callback
    def component_loaded(event):
        """Respond to components being loaded."""
        panel_name = event.data.get(ATTR_COMPONENT)
        if panel_name in ON_DEMAND:
            hass.async_add_job(setup_panel(panel_name))

    hass.bus.async_listen(EVENT_COMPONENT_LOADED, component_loaded)

    return True


class BaseEditConfigView(HomeAssistantView):
    """Configure a Group endpoint."""

    def __init__(self, component, config_type, path, key_schema, data_schema,
                 *, post_write_hook=None):
        """Initialize a config view."""
        self.url = '/api/config/%s/%s/{config_key}' % (component, config_type)
        self.name = 'api:config:%s:%s' % (component, config_type)
        self.path = path
        self.key_schema = key_schema
        self.data_schema = data_schema
        self.post_write_hook = post_write_hook

    def _empty_config(self):
        """Empty config if file not found."""
        raise NotImplementedError

    def _get_value(self, hass, data, config_key):
        """Get value."""
        raise NotImplementedError

    def _write_value(self, hass, data, config_key, new_value):
        """Set value."""
        raise NotImplementedError

    @asyncio.coroutine
    def get(self, request, config_key):
        """Fetch device specific config."""
        hass = request.app['hass']
        current = yield from self.read_config(hass)
        value = self._get_value(hass, current, config_key)

        if value is None:
            return self.json_message('Resource not found', 404)

        return self.json(value)

    @asyncio.coroutine
    def post(self, request, config_key):
        """Validate config and return results."""
        try:
            data = yield from request.json()
        except ValueError:
            return self.json_message('Invalid JSON specified', 400)

        try:
            self.key_schema(config_key)
        except vol.Invalid as err:
            return self.json_message('Key malformed: {}'.format(err), 400)

        try:
            # We just validate, we don't store that data because
            # we don't want to store the defaults.
            self.data_schema(data)
        except vol.Invalid as err:
            return self.json_message('Message malformed: {}'.format(err), 400)

        hass = request.app['hass']
        path = hass.config.path(self.path)

        current = yield from self.read_config(hass)
        self._write_value(hass, current, config_key, data)

        yield from hass.async_add_job(_write, path, current)

        if self.post_write_hook is not None:
            hass.async_add_job(self.post_write_hook(hass))

        return self.json({
            'result': 'ok',
        })

    @asyncio.coroutine
    def read_config(self, hass):
        """Read the config."""
        current = yield from hass.async_add_job(
            _read, hass.config.path(self.path))
        if not current:
            current = self._empty_config()
        return current


class EditKeyBasedConfigView(BaseEditConfigView):
    """Configure a list of entries."""

    def _empty_config(self):
        """Return an empty config."""
        return {}

    def _get_value(self, hass, data, config_key):
        """Get value."""
        return data.get(config_key)

    def _write_value(self, hass, data, config_key, new_value):
        """Set value."""
        data.setdefault(config_key, {}).update(new_value)


class EditIdBasedConfigView(BaseEditConfigView):
    """Configure key based config entries."""

    def _empty_config(self):
        """Return an empty config."""
        return []

    def _get_value(self, hass, data, config_key):
        """Get value."""
        return next(
            (val for val in data if val.get(CONF_ID) == config_key), None)

    def _write_value(self, hass, data, config_key, new_value):
        """Set value."""
        value = self._get_value(hass, data, config_key)

        if value is None:
            value = {CONF_ID: config_key}
            data.append(value)

        value.update(new_value)


def _read(path):
    """Read YAML helper."""
    if not os.path.isfile(path):
        return None

    return load_yaml(path)


def _write(path, data):
    """Write YAML helper."""
    # Do it before opening file. If dump causes error it will now not
    # truncate the file.
    data = dump(data)
    with open(path, 'w', encoding='utf-8') as outfile:
        outfile.write(data)
