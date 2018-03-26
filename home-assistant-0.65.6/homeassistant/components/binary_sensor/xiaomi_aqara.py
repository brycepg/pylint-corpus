"""Support for Xiaomi aqara binary sensors."""
import logging

from homeassistant.components.binary_sensor import BinarySensorDevice
from homeassistant.components.xiaomi_aqara import (PY_XIAOMI_GATEWAY,
                                                   XiaomiDevice)

_LOGGER = logging.getLogger(__name__)

NO_CLOSE = 'no_close'
ATTR_OPEN_SINCE = 'Open since'

MOTION = 'motion'
NO_MOTION = 'no_motion'
ATTR_LAST_ACTION = 'last_action'
ATTR_NO_MOTION_SINCE = 'No motion since'

DENSITY = 'density'
ATTR_DENSITY = 'Density'


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Perform the setup for Xiaomi devices."""
    devices = []
    for (_, gateway) in hass.data[PY_XIAOMI_GATEWAY].gateways.items():
        for device in gateway.devices['binary_sensor']:
            model = device['model']
            if model in ['motion', 'sensor_motion.aq2']:
                devices.append(XiaomiMotionSensor(device, hass, gateway))
            elif model in ['magnet', 'sensor_magnet.aq2']:
                devices.append(XiaomiDoorSensor(device, gateway))
            elif model == 'sensor_wleak.aq1':
                devices.append(XiaomiWaterLeakSensor(device, gateway))
            elif model == 'smoke':
                devices.append(XiaomiSmokeSensor(device, gateway))
            elif model == 'natgas':
                devices.append(XiaomiNatgasSensor(device, gateway))
            elif model in ['switch', 'sensor_switch.aq2', 'sensor_switch.aq3']:
                devices.append(XiaomiButton(device, 'Switch', 'status',
                                            hass, gateway))
            elif model == '86sw1':
                devices.append(XiaomiButton(device, 'Wall Switch', 'channel_0',
                                            hass, gateway))
            elif model == '86sw2':
                devices.append(XiaomiButton(device, 'Wall Switch (Left)',
                                            'channel_0', hass, gateway))
                devices.append(XiaomiButton(device, 'Wall Switch (Right)',
                                            'channel_1', hass, gateway))
                devices.append(XiaomiButton(device, 'Wall Switch (Both)',
                                            'dual_channel', hass, gateway))
            elif model == 'cube':
                devices.append(XiaomiCube(device, hass, gateway))
    add_devices(devices)


class XiaomiBinarySensor(XiaomiDevice, BinarySensorDevice):
    """Representation of a base XiaomiBinarySensor."""

    def __init__(self, device, name, xiaomi_hub, data_key, device_class):
        """Initialize the XiaomiSmokeSensor."""
        self._data_key = data_key
        self._device_class = device_class
        self._should_poll = False
        self._density = 0
        XiaomiDevice.__init__(self, device, name, xiaomi_hub)

    @property
    def should_poll(self):
        """Return True if entity has to be polled for state."""
        return self._should_poll

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._state

    @property
    def device_class(self):
        """Return the class of binary sensor."""
        return self._device_class

    def update(self):
        """Update the sensor state."""
        _LOGGER.debug('Updating xiaomi sensor by polling')
        self._get_from_hub(self._sid)


class XiaomiNatgasSensor(XiaomiBinarySensor):
    """Representation of a XiaomiNatgasSensor."""

    def __init__(self, device, xiaomi_hub):
        """Initialize the XiaomiSmokeSensor."""
        self._density = None
        XiaomiBinarySensor.__init__(self, device, 'Natgas Sensor', xiaomi_hub,
                                    'alarm', 'gas')

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {ATTR_DENSITY: self._density}
        attrs.update(super().device_state_attributes)
        return attrs

    def parse_data(self, data, raw_data):
        """Parse data sent by gateway."""
        if DENSITY in data:
            self._density = int(data.get(DENSITY))

        value = data.get(self._data_key)
        if value is None:
            return False

        if value == '1':
            if self._state:
                return False
            self._state = True
            return True
        elif value == '0':
            if self._state:
                self._state = False
                return True
            return False


class XiaomiMotionSensor(XiaomiBinarySensor):
    """Representation of a XiaomiMotionSensor."""

    def __init__(self, device, hass, xiaomi_hub):
        """Initialize the XiaomiMotionSensor."""
        self._hass = hass
        self._no_motion_since = 0
        XiaomiBinarySensor.__init__(self, device, 'Motion Sensor', xiaomi_hub,
                                    'status', 'motion')

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {ATTR_NO_MOTION_SINCE: self._no_motion_since}
        attrs.update(super().device_state_attributes)
        return attrs

    def parse_data(self, data, raw_data):
        """Parse data sent by gateway."""
        if raw_data['cmd'] == 'heartbeat':
            _LOGGER.debug(
                'Skipping heartbeat of the motion sensor. '
                'It can introduce an incorrect state because of a firmware '
                'bug (https://github.com/home-assistant/home-assistant/pull/'
                '11631#issuecomment-357507744).')
            return

        self._should_poll = False
        if NO_MOTION in data:  # handle push from the hub
            self._no_motion_since = data[NO_MOTION]
            self._state = False
            return True

        value = data.get(self._data_key)
        if value is None:
            return False

        if value == MOTION:
            self._should_poll = True
            if self.entity_id is not None:
                self._hass.bus.fire('motion', {
                    'entity_id': self.entity_id
                })

            self._no_motion_since = 0
            if self._state:
                return False
            self._state = True
            return True
        elif value == NO_MOTION:
            if not self._state:
                return False
            self._state = False
            return True


class XiaomiDoorSensor(XiaomiBinarySensor):
    """Representation of a XiaomiDoorSensor."""

    def __init__(self, device, xiaomi_hub):
        """Initialize the XiaomiDoorSensor."""
        self._open_since = 0
        XiaomiBinarySensor.__init__(self, device, 'Door Window Sensor',
                                    xiaomi_hub, 'status', 'opening')

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {ATTR_OPEN_SINCE: self._open_since}
        attrs.update(super().device_state_attributes)
        return attrs

    def parse_data(self, data, raw_data):
        """Parse data sent by gateway."""
        self._should_poll = False
        if NO_CLOSE in data:  # handle push from the hub
            self._open_since = data[NO_CLOSE]
            return True

        value = data.get(self._data_key)
        if value is None:
            return False

        if value == 'open':
            self._should_poll = True
            if self._state:
                return False
            self._state = True
            return True
        elif value == 'close':
            self._open_since = 0
            if self._state:
                self._state = False
                return True
            return False


class XiaomiWaterLeakSensor(XiaomiBinarySensor):
    """Representation of a XiaomiWaterLeakSensor."""

    def __init__(self, device, xiaomi_hub):
        """Initialize the XiaomiWaterLeakSensor."""
        XiaomiBinarySensor.__init__(self, device, 'Water Leak Sensor',
                                    xiaomi_hub, 'status', 'moisture')

    def parse_data(self, data, raw_data):
        """Parse data sent by gateway."""
        self._should_poll = False

        value = data.get(self._data_key)
        if value is None:
            return False

        if value == 'leak':
            self._should_poll = True
            if self._state:
                return False
            self._state = True
            return True
        elif value == 'no_leak':
            if self._state:
                self._state = False
                return True
            return False


class XiaomiSmokeSensor(XiaomiBinarySensor):
    """Representation of a XiaomiSmokeSensor."""

    def __init__(self, device, xiaomi_hub):
        """Initialize the XiaomiSmokeSensor."""
        self._density = 0
        XiaomiBinarySensor.__init__(self, device, 'Smoke Sensor', xiaomi_hub,
                                    'alarm', 'smoke')

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {ATTR_DENSITY: self._density}
        attrs.update(super().device_state_attributes)
        return attrs

    def parse_data(self, data, raw_data):
        """Parse data sent by gateway."""
        if DENSITY in data:
            self._density = int(data.get(DENSITY))
        value = data.get(self._data_key)
        if value is None:
            return False

        if value == '1':
            if self._state:
                return False
            self._state = True
            return True
        elif value == '0':
            if self._state:
                self._state = False
                return True
            return False


class XiaomiButton(XiaomiBinarySensor):
    """Representation of a Xiaomi Button."""

    def __init__(self, device, name, data_key, hass, xiaomi_hub):
        """Initialize the XiaomiButton."""
        self._hass = hass
        self._last_action = None
        XiaomiBinarySensor.__init__(self, device, name, xiaomi_hub,
                                    data_key, None)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {ATTR_LAST_ACTION: self._last_action}
        attrs.update(super().device_state_attributes)
        return attrs

    def parse_data(self, data, raw_data):
        """Parse data sent by gateway."""
        value = data.get(self._data_key)
        if value is None:
            return False

        if value == 'long_click_press':
            self._state = True
            click_type = 'long_click_press'
        elif value == 'long_click_release':
            self._state = False
            click_type = 'hold'
        elif value == 'click':
            click_type = 'single'
        elif value == 'double_click':
            click_type = 'double'
        elif value == 'both_click':
            click_type = 'both'
        elif value == 'shake':
            click_type = 'shake'
        else:
            _LOGGER.warning("Unsupported click_type detected: %s", value)
            return False

        self._hass.bus.fire('click', {
            'entity_id': self.entity_id,
            'click_type': click_type
        })
        self._last_action = click_type

        if value in ['long_click_press', 'long_click_release']:
            return True
        return False


class XiaomiCube(XiaomiBinarySensor):
    """Representation of a Xiaomi Cube."""

    def __init__(self, device, hass, xiaomi_hub):
        """Initialize the Xiaomi Cube."""
        self._hass = hass
        self._last_action = None
        self._state = False
        XiaomiBinarySensor.__init__(self, device, 'Cube', xiaomi_hub,
                                    None, None)

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {ATTR_LAST_ACTION: self._last_action}
        attrs.update(super().device_state_attributes)
        return attrs

    def parse_data(self, data, raw_data):
        """Parse data sent by gateway."""
        if 'status' in data:
            self._hass.bus.fire('cube_action', {
                'entity_id': self.entity_id,
                'action_type': data['status']
            })
            self._last_action = data['status']

        if 'rotate' in data:
            self._hass.bus.fire('cube_action', {
                'entity_id': self.entity_id,
                'action_type': 'rotate',
                'action_value': float(data['rotate'].replace(",", "."))
            })
            self._last_action = 'rotate'

        return True
