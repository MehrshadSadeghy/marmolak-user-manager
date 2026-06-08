def compute_traffic_delta(previous_bytes: int, current_bytes: int) -> int:
    if current_bytes <= 0:
        return 0
    if previous_bytes <= 0:
        return current_bytes
    if current_bytes >= previous_bytes:
        return current_bytes - previous_bytes
    return current_bytes
