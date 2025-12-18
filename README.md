# Embody BLE

[![PyPI](https://img.shields.io/pypi/v/embody-ble.svg)][pypi_]
[![Status](https://img.shields.io/pypi/status/embody-ble.svg)][status]
[![Python Version](https://img.shields.io/pypi/pyversions/embody-ble)][python version]
[![License](https://img.shields.io/pypi/l/embody-ble)][license]

[![Tests](https://github.com/aidee-health/embody-ble/workflows/Tests/badge.svg)][tests]

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)][pre-commit]
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)][black]

[pypi_]: https://pypi.org/project/embody-ble/
[status]: https://pypi.org/project/embody-ble/
[python version]: https://pypi.org/project/embody-ble
[tests]: https://github.com/aidee-health/embody-ble/actions?workflow=Tests
[pre-commit]: https://github.com/pre-commit/pre-commit
[black]: https://github.com/psf/black

## Features

- Connects to an EmBody device over BLE (Bluetooth) using [Bleak](https://github.com/hbldh/bleak)
- Uses the EmBody protocol to communicate with the device
- Integrates with [the EmBody Protocol Codec](https://github.com/aidee-health/embody-protocol-codec) project
- Asynchronous send without having to wait for response
- Synchronous send where response message is returned
- Provides callback interfaces for incoming messages, response messages and connect/disconnect
- Facade method to send/receive BLE messages directly
- All methods and callbacks are threadsafe
- Separate threads for send, receive and callback processing
- Type safe code using [ty](https://docs.astral.sh/ty/) for type checking
- High level callback interface for attribute reporting

## Requirements

- Python 3.11-3.13
- Access to private Aidee Health repositories on Github

## Installation

You can install _Embody BLE_ via [pip]:

```console
$ pip install embody-ble
```

This adds `embody-ble` as a library, but also provides the CLI application with the same name.

## Usage

A very basic example where you send a message request and get a response:

```python
from embodyble.embodyble import EmbodyBle
from embodyserial.helpers import EmbodySendHelper

embody_ble = EmbodyBle()
send_helper = EmbodySendHelper(sender=embody_ble)
embody_ble.connect()
print(f"Serial no: {send_helper.get_serial_no()}")
embody_ble.shutdown()
```

If you want to see more of what happens under the hood, activate debug logging before setting up `EmbodyBle`:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

## Using the application from the command line

The application also provides a CLI application that is automatically added to the path when installing via pip.

Once installed with pip, type:

```
embody-ble --help
```

To see which options are available.

> **Note**
> The serial port is automatically detected, but can be overridden by using the `--device` option.

### Example - Attribute reporting

To see how attribute reporting can be configured, have a look at the example in [examples/ble_reporting_example.py](./examples/reporting_example.py)

You can also test attribute reporting using the cli:

```shell
embody-ble --log-level INFO --report-attribute battery_level --report-interval 1
```

```shell
embody-ble --log-level INFO --report-attribute heart_rate --report-interval 1000
```

### Example - List all available EmBody devices

```shell
embody-ble --list-devices
```

### Example - List all attribute values

```shell
embody-ble --get-all
```

### Example - Get serial no of device

```shell
embody-ble --get serialno
```

### Example - List files over serial port

```shell
embody-ble --list-files
```

### Example - Set time current time (UTC)

```shell
embody-ble --set-time
```

## Logging

This library uses Python's standard logging module and follows best practices for libraries:

### For Library Users

The library is **silent by default** - it won't produce any output unless you configure logging. To enable logging from the library:

```python
import logging

# Enable INFO level logging for embodyble
logging.getLogger('embodyble').setLevel(logging.INFO)
logging.getLogger('embodyble').addHandler(logging.StreamHandler())

# Or configure specific modules
logging.getLogger('embodyble.embodyble').setLevel(logging.DEBUG)
```

### For CLI Users

The CLI configures logging automatically. Use `--log-level` to control verbosity:

```bash
embody-ble --log-level DEBUG --list-devices
```

Available levels: CRITICAL, WARNING, INFO, DEBUG

## Troubleshooting

No known issues registered.

## Contributing

Contributions are very welcome.
To learn more, see the [Contributor Guide].

## Issues

If you encounter any problems,
please [file an issue] along with a detailed description.

[hypermodern python cookiecutter]: https://github.com/cjolowicz/cookiecutter-hypermodern-python
[file an issue]: https://github.com/aidee-health/embody-ble/issues
[pip]: https://pip.pypa.io/

<!-- github-only -->

[license]: https://github.com/aidee-health/embody-ble/blob/main/LICENSE
[contributor guide]: https://github.com/aidee-health/embody-ble/blob/main/CONTRIBUTING.md
