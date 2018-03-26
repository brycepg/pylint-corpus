"""The tests for the panel_iframe component."""
import unittest
from unittest.mock import patch

from homeassistant import setup
from homeassistant.components import frontend

from tests.common import get_test_home_assistant


class TestPanelIframe(unittest.TestCase):
    """Test the panel_iframe component."""

    def setUp(self):
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()

    def tearDown(self):
        """Stop everything that was started."""
        self.hass.stop()

    def test_wrong_config(self):
        """Test setup with wrong configuration."""
        to_try = [
            {'invalid space': {
                'url': 'https://home-assistant.io'}},
            {'router': {
                'url': 'not-a-url'}}]

        for conf in to_try:
            assert not setup.setup_component(
                self.hass, 'panel_iframe', {
                    'panel_iframe': conf
                })

    @patch.dict('hass_frontend_es5.FINGERPRINTS',
                {'iframe': 'md5md5'})
    def test_correct_config(self):
        """Test correct config."""
        assert setup.setup_component(
            self.hass, 'panel_iframe', {
                'panel_iframe': {
                    'router': {
                        'icon': 'mdi:network-wireless',
                        'title': 'Router',
                        'url': 'http://192.168.1.1',
                    },
                    'weather': {
                        'icon': 'mdi:weather',
                        'title': 'Weather',
                        'url': 'https://www.wunderground.com/us/ca/san-diego',
                    },
                    'api': {
                        'icon': 'mdi:weather',
                        'title': 'Api',
                        'url': '/api',
                    },
                    'ftp': {
                        'icon': 'mdi:weather',
                        'title': 'FTP',
                        'url': 'ftp://some/ftp',
                    },
                },
            })

        panels = self.hass.data[frontend.DATA_PANELS]

        assert panels.get('router').to_response(self.hass, None) == {
            'component_name': 'iframe',
            'config': {'url': 'http://192.168.1.1'},
            'icon': 'mdi:network-wireless',
            'title': 'Router',
            'url': '/frontend_es5/panels/ha-panel-iframe-md5md5.html',
            'url_path': 'router'
        }

        assert panels.get('weather').to_response(self.hass, None) == {
            'component_name': 'iframe',
            'config': {'url': 'https://www.wunderground.com/us/ca/san-diego'},
            'icon': 'mdi:weather',
            'title': 'Weather',
            'url': '/frontend_es5/panels/ha-panel-iframe-md5md5.html',
            'url_path': 'weather',
        }

        assert panels.get('api').to_response(self.hass, None) == {
            'component_name': 'iframe',
            'config': {'url': '/api'},
            'icon': 'mdi:weather',
            'title': 'Api',
            'url': '/frontend_es5/panels/ha-panel-iframe-md5md5.html',
            'url_path': 'api',
        }

        assert panels.get('ftp').to_response(self.hass, None) == {
            'component_name': 'iframe',
            'config': {'url': 'ftp://some/ftp'},
            'icon': 'mdi:weather',
            'title': 'FTP',
            'url': '/frontend_es5/panels/ha-panel-iframe-md5md5.html',
            'url_path': 'ftp',
        }
