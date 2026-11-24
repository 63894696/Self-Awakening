from self_awaken.errors import EmptyResponseError
from self_awaken.fingerprint import _format_probe_error


def test_empty_response_error_prefix():
    assert _format_probe_error(EmptyResponseError("no content")) == "empty_response: no content"


def test_generic_error_unchanged():
    assert _format_probe_error(RuntimeError("boom")) == "boom"
