from enum import Enum


class AdminAuditAction(str, Enum):
    user_blocked = "user_blocked"
    user_unblocked = "user_unblocked"
    config_enabled = "config_enabled"
    config_disabled = "config_disabled"
    config_regenerated = "config_regenerated"
    collaborator_added = "collaborator_added"
    collaborator_removed = "collaborator_removed"
    collaborator_discount_changed = "collaborator_discount_changed"
