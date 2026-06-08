from vpn_core.openvpn_sync.services.traffic_helpers import compute_traffic_delta


def test_compute_traffic_delta_normal_growth():
    assert compute_traffic_delta(1000, 2500) == 1500


def test_compute_traffic_delta_reconnect_resets_counter():
    assert compute_traffic_delta(5000, 800) == 800


def test_compute_traffic_delta_first_reading():
    assert compute_traffic_delta(0, 1200) == 1200


def test_compute_traffic_delta_no_usage():
    assert compute_traffic_delta(1000, 0) == 0
