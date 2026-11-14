from src.log_parser import extract_errors, extract_error_contexts
from src.log_parser import (
    extract_errors,
    extract_error_contexts,
    normalize_error,
    generate_fingerprint
)

def test_extract_errors():
    logs = """
    INFO Application started
    ERROR Database failed
    WARNING Slow response
    CRITICAL Server shutdown
    """

    result = extract_errors(logs)

    assert len(result) == 2
    assert "ERROR Database failed" in result[0]
    assert "CRITICAL Server shutdown" in result[1]


def test_extract_error_contexts():
    logs = """INFO Application started
INFO Loading config
ERROR Database failed
INFO Retrying connection
INFO Application stopped"""

    result = extract_error_contexts(logs, context_lines=1)

    assert len(result) == 1
    assert "INFO Loading config" in result[0]
    assert "ERROR Database failed" in result[0]
    assert "INFO Retrying connection" in result[0]

def test_no_errors():
    logs = """
    INFO Application started
    WARNING Slow response
    INFO Database connected
    """

    assert extract_errors(logs) == []
    assert extract_error_contexts(logs) == []

#-----------------------------test error fingerprintning-----------------------------

def test_dynamic_ids_are_normalized():

    error1 = "ERROR Payment failed for order 101"
    error2 = "ERROR Payment failed for order 205"

    assert normalize_error(error1) == normalize_error(error2)

def test_http_status_codes_are_preserved():

    error1 = "ERROR HTTP 404 Not Found"
    error2 = "ERROR HTTP 500 Server Error"

    assert normalize_error(error1) != normalize_error(error2)

def test_fingerprints_for_similar_errors():

    error1 = "ERROR Payment failed for order 101"
    error2 = "ERROR Payment failed for order 205"

    assert generate_fingerprint(error1) == generate_fingerprint(error2)

def test_fingerprints_for_different_errors():

    error1 = "ERROR HTTP 404 Not Found"
    error2 = "ERROR HTTP 500 Server Error"

    assert generate_fingerprint(error1) != generate_fingerprint(error2)