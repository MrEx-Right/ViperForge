import pytest

from viperforge.session import Session
from viperforge.validator import ERROR, INFO, WARNING, validate_chain

from conftest import make_session


def run(*sessions):
    return validate_chain([None] * len(sessions), list(sessions))


def severities(issues, block=None):
    return [i.severity for i in issues if block is None or i.block_name == block]


def test_empty_chain_has_no_issues():
    assert run() == []


def test_valid_socket_flow_has_no_errors():
    issues = run(make_session("builder_socket"), make_session("builder_send"),
                 make_session("builder_recv"))
    assert ERROR not in severities(issues)


@pytest.mark.parametrize("consumer", ["builder_send", "builder_recv", "builder_recv_until"])
def test_socket_consumer_without_socket_is_error(consumer):
    assert ERROR in severities(run(make_session(consumer)), consumer)


def test_socket_name_must_match():
    issues = run(make_session("builder_socket", SOCK_NAME="a"),
                 make_session("builder_send", SOCK_NAME="b"))
    assert ERROR in severities(issues, "builder_send")


def test_unproduced_ctx_variable_is_warning():
    issues = run(make_session("builder_b64encode", INPUT_VAR="nowhere"))
    assert severities(issues, "builder_b64encode") == [WARNING]


def test_produced_ctx_variable_is_ok():
    issues = run(make_session("builder_read_file", FILE_PATH="x", OUTPUT_VAR="data"),
                 make_session("builder_b64encode", INPUT_VAR="data"))
    assert severities(issues, "builder_b64encode") == []


def test_empty_custom_code_is_error():
    assert ERROR in severities(run(make_session("builder_custom", CODE="   ")), "builder_custom")


@pytest.mark.parametrize("value", ["0xdeadbeef", "100", "0x41414141 + 8", "1 << 16", "-5"])
@pytest.mark.parametrize("block", ["builder_pack", "builder_p32_p64"])
def test_pack_value_accepts_literals(block, value):
    assert ERROR not in severities(run(make_session(block, VALUE=value)), block)


@pytest.mark.parametrize("value", ["not_a_number", "0xZZ", "__import__('os').getcwd()"])
@pytest.mark.parametrize("block", ["builder_pack", "builder_p32_p64"])
def test_pack_value_rejects_non_literals(block, value):
    assert ERROR in severities(run(make_session(block, VALUE=value)), block)


def test_pack_value_is_never_executed(tmp_path):
    # A crafted workspace/macro file must not be able to run code during validation.
    marker = tmp_path / "pwned"
    run(make_session("builder_pack", VALUE=f"open(r'{marker}', 'w')"))
    assert not marker.exists()


def test_sleep_seconds_must_be_number():
    assert ERROR in severities(run(make_session("builder_sleep", SECONDS="soon")), "builder_sleep")
    assert severities(run(make_session("builder_sleep", SECONDS="0.5")), "builder_sleep") == []


def test_http_url_scheme_warning():
    assert severities(run(make_session("builder_http_req", URL="example.com")),
                      "builder_http_req") == [WARNING]


@pytest.mark.parametrize("block", ["builder_read_file", "builder_write_file"])
def test_file_path_required(block):
    assert ERROR in severities(run(make_session(block, FILE_PATH="")), block)


def test_if_else_rules():
    issues = run(make_session("builder_if_else", VAR_NAME="", OPERATOR="=~"))
    assert sorted(severities(issues, "builder_if_else")) == [ERROR, WARNING]


def test_loop_rules():
    assert ERROR in severities(
        run(make_session("builder_loop", MODE="FILE", FILE_PATH="")), "builder_loop")
    assert ERROR in severities(
        run(make_session("builder_loop", MODE="RANGE", RANGE_START="a")), "builder_loop")


@pytest.mark.parametrize("count", ["0", "-1", "x"])
def test_try_catch_retry_count(count):
    s = make_session("builder_try_catch", FALLBACK_ACTION="RETRY", RETRY_COUNT=count)
    assert ERROR in severities(run(s), "builder_try_catch")


def test_variable_set_rules():
    assert ERROR in severities(
        run(make_session("builder_variable_set", VAR_NAME="")), "builder_variable_set")
    assert ERROR in severities(
        run(make_session("builder_variable_set", VAR_NAME="v", MODE="REGEX", REGEX_PATTERN="")),
        "builder_variable_set")


def test_mixing_builder_and_classic_warns():
    issues = run(make_session("builder_socket"), make_session("web_lfi"))
    assert WARNING in severities(issues, "Chain")


def test_single_builder_block_is_info():
    assert INFO in severities(run(make_session("builder_socket")), "Chain")


def test_block_without_exploit_is_error():
    assert severities(run(Session())) == [ERROR]
