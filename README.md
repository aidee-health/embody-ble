# Embody BLE Communicator

[![Tests](https://github.com/aidee-health/embody-ble-communicator/workflows/Tests/badge.svg)][tests]

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)][pre-commit]
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)][black]

[tests]: https://github.com/aidee-health/embody-ble-communicator/actions?workflow=Tests
[pre-commit]: https://github.com/pre-commit/pre-commit
[black]: https://github.com/psf/black

## Features

- Connects to an EmBody device over BLE (Bluetooth)
- Uses the EmBody protocol to communicate with the device
- Integrates with [the EmBody Protocol Codec](https://github.com/aidee-health/embody-protocol-codec) project
- Asynchronous send without having to wait for response
- Synchronous send where response message is returned
- Provides callback interfaces for incoming messages, response messages and connect/disconnect
- Facade method to send/receive BLE messages directly
- All methods and callbacks are threadsafe
- Separate threads for send, receive and callback processing
- Type safe code using [mypy](https://mypy.readthedocs.io/) for type checking

## Requirements

- Python 3.9 (NOTE! Nordic's pc-ble-driver-py (and nrfutil) does not support 3.10 yet)
- Access to private Aidee Health repositories on Github

## Installation

You can install _Embody BLE Communicator_ via [pip] from private Github repo:

```console
$ pip install "git+https://github.com/aidee-health/embody-ble-communicator@main#egg=embodyble"
```

## Usage

A very basic example where you send a message request and get a response (resolving device serial no through serial port):

```python
from embodyble import communicator
from embodycodec import codec

comm = communicator.EmbodyBleCommunicator()
response = comm.send_message_and_wait_for_response(codec.ListFiles())
print(f"Received response: {response}")
comm.shutdown()
```

If you want to see more of what happens under the hood, activate debug logging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

Please see the [Command-line Reference] for more details.

## Troubleshooting

### I get a segmentation fault on Mac

As of writing, you need to use the official Python release for Mac. Using brew's version does not work.
For more, look at the [README](https://github.com/NordicSemiconductor/pc-ble-driver-py#macos-limitations)
for Nordic's `pc-ble-driver-py`

## Contributing

Contributions are very welcome.
To learn more, see the [Contributor Guide].

## Issues

If you encounter any problems,
please [file an issue] along with a detailed description.

## Credits

This project was generated from [@cjolowicz]'s [Hypermodern Python Cookiecutter] template.

[@cjolowicz]: https://github.com/cjolowicz
[hypermodern python cookiecutter]: https://github.com/cjolowicz/cookiecutter-hypermodern-python
[file an issue]: https://github.com/aidee-health/embody-ble-communicator/issues
[pip]: https://pip.pypa.io/

<!-- github-only -->

[license]: https://github.com/aidee-health/embody-ble-communicator/blob/main/LICENSE
[contributor guide]: https://github.com/aidee-health/embody-ble-communicator/blob/main/CONTRIBUTING.md
[command-line reference]: https://embody-ble-communicator.readthedocs.io/en/latest/usage.html
