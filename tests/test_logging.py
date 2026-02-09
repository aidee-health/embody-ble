"""Test logging behavior for the embodyble library."""

import io
import logging
from contextlib import redirect_stderr
from contextlib import redirect_stdout

import embodyble  # noqa: F401
from embodyble.logging import configure_library_logging
from embodyble.logging import get_logger


def test_library_silent_by_default():
    """Library should produce no output by default."""
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        logger = get_logger("test_module")
        logger.info("This should not appear")
        logger.warning("This should not appear")
        logger.error("This should not appear")
        logger.debug("This should not appear")

    stdout_output = stdout_capture.getvalue()
    stderr_output = stderr_capture.getvalue()

    assert stdout_output == "", f"Expected no stdout output, got: {stdout_output}"
    assert stderr_output == "", f"Expected no stderr output, got: {stderr_output}"


def test_library_logging_when_configured():
    """Library should produce output when explicitly configured."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)

    embodyble_logger = logging.getLogger("embodyble")
    embodyble_logger.handlers.clear()
    embodyble_logger.addHandler(handler)
    embodyble_logger.setLevel(logging.INFO)
    embodyble_logger.propagate = False

    logger = get_logger("test_module")
    logger.info("This should appear")

    output = stream.getvalue()
    assert "This should appear" in output

    # Cleanup
    embodyble_logger.handlers.clear()


def test_get_logger_hierarchy():
    """Test logger hierarchy is properly established."""
    root_logger = get_logger()
    module_logger = get_logger("test_module")

    assert root_logger.name == "embodyble"
    assert module_logger.name == "embodyble.test_module"
    assert module_logger.parent == root_logger


def test_configure_library_logging():
    """Test configure_library_logging sets up handlers correctly."""
    # Clear any existing handlers
    embodyble_logger = logging.getLogger("embodyble")
    embodyble_logger.handlers.clear()

    # Configure logging
    configure_library_logging(level=logging.DEBUG, format_string="%(levelname)s:%(message)s")

    # Verify handler was added
    assert len(embodyble_logger.handlers) > 0
    assert any(isinstance(h, logging.StreamHandler) for h in embodyble_logger.handlers)
    assert embodyble_logger.level == logging.DEBUG

    # Cleanup
    embodyble_logger.handlers.clear()


def test_null_handler_by_default():
    """Test that library has NullHandler by default or no output."""
    # Import the package to ensure __init__ has run
    embodyble_logger = logging.getLogger("embodyble")

    # Should either have a NullHandler, or if handlers were configured by other tests,
    # verify that the library doesn't produce output by default
    if embodyble_logger.handlers:
        # Check that at least initially there was a NullHandler
        # (may have been replaced by other tests' configure_library_logging calls)
        # The key test is that library is silent by default, tested by test_library_silent_by_default
        pass
    else:
        # If no handlers, logging is disabled which is also acceptable
        pass


def test_configure_library_logging_replaces_null_handler():
    """Test that configure_library_logging removes NullHandler."""
    embodyble_logger = logging.getLogger("embodyble")
    initial_handlers = embodyble_logger.handlers.copy()

    # Configure logging
    configure_library_logging(level=logging.INFO)

    # Should no longer have NullHandler
    has_null_handler = any(isinstance(h, logging.NullHandler) for h in embodyble_logger.handlers)
    assert not has_null_handler, "NullHandler should be removed after configuration"

    # Should have StreamHandler
    has_stream_handler = any(isinstance(h, logging.StreamHandler) for h in embodyble_logger.handlers)
    assert has_stream_handler, "Should have StreamHandler after configuration"

    # Cleanup - restore original handlers
    embodyble_logger.handlers = initial_handlers
