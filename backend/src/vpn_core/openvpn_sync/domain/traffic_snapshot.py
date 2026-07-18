from dataclasses import dataclass, field


@dataclass(frozen=True)
class OpenVpnTrafficSnapshot:
    live: dict[str, int] = field(default_factory=dict)
    disconnect: dict[str, int] = field(default_factory=dict)
