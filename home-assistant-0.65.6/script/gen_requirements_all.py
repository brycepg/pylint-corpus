#!/usr/bin/env python3
"""Generate an updated requirements_all.txt."""
import importlib
import os
import pkgutil
import re
import sys
import fnmatch

COMMENT_REQUIREMENTS = (
    'RPi.GPIO',
    'raspihats',
    'rpi-rf',
    'Adafruit_Python_DHT',
    'Adafruit_BBIO',
    'fritzconnection',
    'pybluez',
    'beacontools',
    'bluepy',
    'opencv-python',
    'python-lirc',
    'gattlib',
    'pyuserinput',
    'evdev',
    'pycups',
    'python-eq3bt',
    'avion',
    'decora',
    'face_recognition',
    'blinkt',
    'smbus-cffi',
    'envirophat',
    'i2csense',
    'credstash',
    'bme680',
)

TEST_REQUIREMENTS = (
    'aioautomatic',
    'aiohttp_cors',
    'aiohue',
    'apns2',
    'caldav',
    'coinmarketcap',
    'defusedxml',
    'dsmr_parser',
    'ephem',
    'evohomeclient',
    'feedparser',
    'gTTS-token',
    'HAP-python',
    'ha-ffmpeg',
    'haversine',
    'hbmqtt',
    'holidays',
    'home-assistant-frontend',
    'influxdb',
    'libpurecoollink',
    'libsoundtouch',
    'mficlient',
    'numpy',
    'paho-mqtt',
    'pexpect',
    'pilight',
    'pmsensor',
    'prometheus_client',
    'pushbullet.py',
    'py-canary',
    'pydispatcher',
    'PyJWT',
    'pylitejet',
    'pymonoprice',
    'pynx584',
    'python-forecastio',
    'pyunifi',
    'pywebpush',
    'restrictedpython',
    'rflink',
    'ring_doorbell',
    'rxv',
    'sleepyq',
    'SoCo',
    'somecomfort',
    'sqlalchemy',
    'statsd',
    'uvcclient',
    'voluptuous-serialize',
    'warrant',
    'yahoo-finance',
    'pythonwhois',
    'wakeonlan',
    'vultr'
)

IGNORE_PACKAGES = (
    'homeassistant.components.recorder.models',
    'homeassistant.components.homekit.*'
)

IGNORE_PIN = ('colorlog>2.1,<3', 'keyring>=9.3,<10.0', 'urllib3')

IGNORE_REQ = (
    'colorama<=1',  # Windows only requirement in check_config
)

URL_PIN = ('https://home-assistant.io/developers/code_review_platform/'
           '#1-requirements')


CONSTRAINT_PATH = os.path.join(os.path.dirname(__file__),
                               '../homeassistant/package_constraints.txt')
CONSTRAINT_BASE = """
# Breaks Python 3.6 and is not needed for our supported Python versions
enum34==1000000000.0.0

# This is a old unmaintained library and is replaced with pycryptodome
pycrypto==1000000000.0.0
"""


def explore_module(package, explore_children):
    """Explore the modules."""
    module = importlib.import_module(package)

    found = []

    if not hasattr(module, '__path__'):
        return found

    for _, name, _ in pkgutil.iter_modules(module.__path__, package + '.'):
        found.append(name)

        if explore_children:
            found.extend(explore_module(name, False))

    return found


def core_requirements():
    """Gather core requirements out of setup.py."""
    with open('setup.py') as inp:
        reqs_raw = re.search(
            r'REQUIRES = \[(.*?)\]', inp.read(), re.S).group(1)
    return re.findall(r"'(.*?)'", reqs_raw)


def comment_requirement(req):
    """Some requirements don't install on all systems."""
    return any(ign in req for ign in COMMENT_REQUIREMENTS)


def gather_modules():
    """Collect the information."""
    reqs = {}

    errors = []

    for package in sorted(explore_module('homeassistant.components', True) +
                          explore_module('homeassistant.scripts', True)):
        try:
            module = importlib.import_module(package)
        except ImportError:
            for pattern in IGNORE_PACKAGES:
                if fnmatch.fnmatch(package, pattern):
                    break
            else:
                errors.append(package)
            continue

        if not getattr(module, 'REQUIREMENTS', None):
            continue

        for req in module.REQUIREMENTS:
            if req in IGNORE_REQ:
                continue
            if req.partition('==')[1] == '' and req not in IGNORE_PIN:
                errors.append(
                    "{}[Please pin requirement {}, see {}]".format(
                        package, req, URL_PIN))
            reqs.setdefault(req, []).append(package)

    for key in reqs:
        reqs[key] = sorted(reqs[key],
                           key=lambda name: (len(name.split('.')), name))

    if errors:
        print("******* ERROR")
        print("Errors while importing: ", ', '.join(errors))
        print("Make sure you import 3rd party libraries inside methods.")
        return None

    return reqs


def generate_requirements_list(reqs):
    """Generate a pip file based on requirements."""
    output = []
    for pkg, requirements in sorted(reqs.items(), key=lambda item: item[0]):
        for req in sorted(requirements,
                          key=lambda name: (len(name.split('.')), name)):
            output.append('\n# {}'.format(req))

        if comment_requirement(pkg):
            output.append('\n# {}\n'.format(pkg))
        else:
            output.append('\n{}\n'.format(pkg))
    return ''.join(output)


def requirements_all_output(reqs):
    """Generate output for requirements_all."""
    output = []
    output.append('# Home Assistant core')
    output.append('\n')
    output.append('\n'.join(core_requirements()))
    output.append('\n')
    output.append(generate_requirements_list(reqs))

    return ''.join(output)


def requirements_test_output(reqs):
    """Generate output for test_requirements."""
    output = []
    output.append('# Home Assistant test')
    output.append('\n')
    with open('requirements_test.txt') as test_file:
        output.append(test_file.read())
    output.append('\n')
    filtered = {key: value for key, value in reqs.items()
                if any(
                    re.search(r'(^|#){}($|[=><])'.format(ign),
                              key) is not None for ign in TEST_REQUIREMENTS)}
    output.append(generate_requirements_list(filtered))

    return ''.join(output)


def gather_constraints():
    """Construct output for constraint file."""
    return '\n'.join(core_requirements() + [''])


def write_requirements_file(data):
    """Write the modules to the requirements_all.txt."""
    with open('requirements_all.txt', 'w+', newline="\n") as req_file:
        req_file.write(data)


def write_test_requirements_file(data):
    """Write the modules to the requirements_all.txt."""
    with open('requirements_test_all.txt', 'w+', newline="\n") as req_file:
        req_file.write(data)


def write_constraints_file(data):
    """Write constraints to a file."""
    with open(CONSTRAINT_PATH, 'w+', newline="\n") as req_file:
        req_file.write(data + CONSTRAINT_BASE)


def validate_requirements_file(data):
    """Validate if requirements_all.txt is up to date."""
    with open('requirements_all.txt', 'r') as req_file:
        return data == req_file.read()


def validate_requirements_test_file(data):
    """Validate if requirements_all.txt is up to date."""
    with open('requirements_test_all.txt', 'r') as req_file:
        return data == req_file.read()


def validate_constraints_file(data):
    """Validate if constraints is up to date."""
    with open(CONSTRAINT_PATH, 'r') as req_file:
        return data + CONSTRAINT_BASE == req_file.read()


def main():
    """Main section of the script."""
    if not os.path.isfile('requirements_all.txt'):
        print('Run this from HA root dir')
        return

    data = gather_modules()

    if data is None:
        sys.exit(1)

    constraints = gather_constraints()

    reqs_file = requirements_all_output(data)
    reqs_test_file = requirements_test_output(data)

    if sys.argv[-1] == 'validate':
        errors = []
        if not validate_requirements_file(reqs_file):
            errors.append("requirements_all.txt is not up to date")

        if not validate_requirements_test_file(reqs_test_file):
            errors.append("requirements_test_all.txt is not up to date")

        if not validate_constraints_file(constraints):
            errors.append(
                "home-assistant/package_constraints.txt is not up to date")

        if errors:
            print("******* ERROR")
            print('\n'.join(errors))
            print("Please run script/gen_requirements_all.py")
            sys.exit(1)

        sys.exit(0)

    write_requirements_file(reqs_file)
    write_test_requirements_file(reqs_test_file)
    write_constraints_file(constraints)


if __name__ == '__main__':
    main()
