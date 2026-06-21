-- Phase 0: OpenVPN auth-user-pass schema (additive, backward compatible)
-- Applied automatically by user-manager PostgresManager._apply_schema_patches on startup.
-- Run manually on production if you prefer explicit migration control.

ALTER TABLE openvpn_client_credentials
  ADD COLUMN IF NOT EXISTS auth_mode VARCHAR(32) NOT NULL DEFAULT 'certificate';

ALTER TABLE openvpn_client_credentials
  ADD COLUMN IF NOT EXISTS vpn_username VARCHAR(32);

ALTER TABLE openvpn_client_credentials
  ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);

ALTER TABLE openvpn_client_credentials
  ADD COLUMN IF NOT EXISTS password_rotated_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE openvpn_client_credentials
  ADD COLUMN IF NOT EXISTS auth_synced_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX IF NOT EXISTS ix_openvpn_client_credentials_vpn_username
  ON openvpn_client_credentials (vpn_username);
