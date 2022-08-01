"""Command-line interface."""
import click


@click.command()
@click.version_option()
def main() -> None:
    """Embody BLE Communicator."""


if __name__ == "__main__":
    main(prog_name="embody-ble-communicator")  # pragma: no cover
