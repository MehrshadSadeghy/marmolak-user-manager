import re

OPENVPN_PLAN = re.compile(r"^buy:sv:\d+:plan:\d+$")
OPENVPN_PAY = re.compile(r"^buy:sv:\d+:plan:\d+:pay:\d+$")
GENERIC_PAY = re.compile(r"^buy:\d+:pay:\d+$")


def test_openvpn_plan_callback_does_not_match_payment_handler():
    callback = "buy:sv:3:plan:12"
    assert OPENVPN_PLAN.match(callback)
    assert not OPENVPN_PAY.match(callback)


def test_openvpn_payment_callback_does_not_match_plan_handler():
    callback = "buy:sv:3:plan:12:pay:1"
    assert OPENVPN_PAY.match(callback)
    assert not OPENVPN_PLAN.match(callback)


def test_generic_payment_callback():
    callback = "buy:12:pay:1"
    assert GENERIC_PAY.match(callback)
    assert not OPENVPN_PLAN.match(callback)
