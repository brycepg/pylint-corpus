"""
Demo platform that has two fake binary sensors.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/demo/
"""
import homeassistant.util.dt as dt_util
from homeassistant.components.calendar import CalendarEventDevice
from homeassistant.components.google import CONF_DEVICE_ID, CONF_NAME


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Demo Calendar platform."""
    calendar_data_future = DemoGoogleCalendarDataFuture()
    calendar_data_current = DemoGoogleCalendarDataCurrent()
    add_devices([
        DemoGoogleCalendar(hass, calendar_data_future, {
            CONF_NAME: 'Future Event',
            CONF_DEVICE_ID: 'future_event',
        }),

        DemoGoogleCalendar(hass, calendar_data_current, {
            CONF_NAME: 'Current Event',
            CONF_DEVICE_ID: 'current_event',
        }),
    ])


class DemoGoogleCalendarData(object):
    """Representation of a Demo Calendar element."""

    # pylint: disable=no-self-use
    def update(self):
        """Return true so entity knows we have new data."""
        return True


class DemoGoogleCalendarDataFuture(DemoGoogleCalendarData):
    """Representation of a Demo Calendar for a future event."""

    def __init__(self):
        """Set the event to a future event."""
        one_hour_from_now = dt_util.now() \
            + dt_util.dt.timedelta(minutes=30)
        self.event = {
            'start': {
                'dateTime': one_hour_from_now.isoformat()
            },
            'end': {
                'dateTime': (one_hour_from_now + dt_util.dt.
                             timedelta(minutes=60)).isoformat()
            },
            'summary': 'Future Event',
        }


class DemoGoogleCalendarDataCurrent(DemoGoogleCalendarData):
    """Representation of a Demo Calendar for a current event."""

    def __init__(self):
        """Set the event data."""
        middle_of_event = dt_util.now() \
            - dt_util.dt.timedelta(minutes=30)
        self.event = {
            'start': {
                'dateTime': middle_of_event.isoformat()
            },
            'end': {
                'dateTime': (middle_of_event + dt_util.dt.
                             timedelta(minutes=60)).isoformat()
            },
            'summary': 'Current Event',
        }


class DemoGoogleCalendar(CalendarEventDevice):
    """Representation of a Demo Calendar element."""

    def __init__(self, hass, calendar_data, data):
        """Initialize Google Calendar but without the API calls."""
        self.data = calendar_data
        super().__init__(hass, data)
