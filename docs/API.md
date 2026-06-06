# User Manager API Reference

Base URL (local Docker): `http://localhost:8080`

Interactive docs: `http://localhost:8080/docs`

---

## Authentication

| API group | Required headers |
|-----------|------------------|
| Bot APIs (`/api/v1/bot/*`) | `X-Bot-Api-Key: <BOT_API_KEY>` |
| Admin APIs (`/api/v1/admin/*`) | `X-Bot-Api-Key` + `X-Admin-Telegram-Id: <telegram_chat_id>` |
| Core domain APIs (subscription, servers, openvpn, strategy, traffic) | **No auth currently** — internal use only |

Set in `.env`:

```env
BOT_API_KEY=changeme-bot-api-key
ADMIN_CHAT_IDS=123456789
SUPER_ADMIN_CHAT_IDS=987654321
```

Admin IDs must be listed in `ADMIN_CHAT_IDS` or `SUPER_ADMIN_CHAT_IDS`.

### Example headers

```bash
# Bot call
-H "X-Bot-Api-Key: changeme-bot-api-key"

# Admin call
-H "X-Bot-Api-Key: changeme-bot-api-key" \
-H "X-Admin-Telegram-Id: 123456789"
```

---

## Common enums

### `PaymentPurpose`

| Value | Use |
|-------|-----|
| `purchase` | Buy a new VPN service |
| `renewal` | Renew an existing subscription |
| `topup` | Wallet top-up only |

### `PaymentRequestStatus`

| Value | Meaning |
|-------|---------|
| `awaiting_receipt` | Payment created; user has not uploaded receipt yet |
| `pending_approval` | Receipt submitted; waiting for admin |
| `approved` | Admin approved (transitional) |
| `rejected` | Admin rejected |
| `completed` | Fully processed |

### `SubscriptionStatus`

| Value | Meaning |
|-------|---------|
| `active` | Subscription is active |
| `expired` | Time expired |
| `traffic_exceeded` | Data quota used up |
| `disabled` | Manually disabled |

### Service type slugs (default seeded)

| Slug | Description |
|------|-------------|
| `v2ray` | V2Ray / Xray subscription link |
| `openvpn` | OpenVPN `.ovpn` config file |

---

## Shared models

### User

```json
{
  "id": 1,
  "telegram_id": "123456789",
  "chat_id": "123456789",
  "username": "john_doe",
  "is_active": true,
  "created_at": "2026-06-06T10:00:00Z"
}
```

### Plan

```json
{
  "id": 1,
  "name": "10 GB Monthly",
  "description": "",
  "service_type": "v2ray",
  "duration_days": 30,
  "traffic_limit_bytes": 10737418240,
  "price_toman": 200,
  "is_active": true
}
```

**Note:** `traffic_limit_bytes` — 10 GB = `10737418240` bytes (10 × 1024³).

### Subscription

```json
{
  "id": 1,
  "user_id": 1,
  "plan_id": 1,
  "service_type": "openvpn",
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "traffic_limit_bytes": 10737418240,
  "traffic_used_bytes": 0,
  "started_at": "2026-06-06T10:00:00Z",
  "expire_at": "2026-07-06T10:00:00Z"
}
```

### PaymentRequest

```json
{
  "id": 1,
  "user_id": 1,
  "payment_method_id": 1,
  "purpose": "purchase",
  "amount_toman": 200,
  "plan_id": 1,
  "subscription_id": null,
  "service_type": "v2ray",
  "status": "awaiting_receipt",
  "receipt_file_id": null,
  "receipt_message_id": null,
  "admin_note": "",
  "reviewed_by_telegram_id": null
}
```

---

# 1. Bot APIs

Prefix: `/api/v1/bot`  
Auth: `X-Bot-Api-Key`

Used by the Telegram bot. All user-facing commerce flows go through these endpoints.

---

## 1.1 Register / get user

### `POST /api/v1/bot/users/register`

Create user (or update chat_id/username if already exists) and ensure wallet exists.

**Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `telegram_id` | string | yes | Telegram user ID |
| `chat_id` | string | yes | Telegram chat ID |
| `username` | string | no | Telegram @username without @ |

**Response:** `{ "user": User, "wallet_balance_toman": 0 }`

```bash
curl -X POST http://localhost:8080/api/v1/bot/users/register \
  -H "Content-Type: application/json" \
  -H "X-Bot-Api-Key: changeme-bot-api-key" \
  -d '{"telegram_id":"123456789","chat_id":"123456789","username":"myuser"}'
```

### `GET /api/v1/bot/users/by-telegram/{telegram_id}`

Get user + wallet balance by Telegram ID.

---

## 1.2 Services & plans (catalog)

### `GET /api/v1/bot/services`

List **enabled** service types only (e.g. v2ray, openvpn).

**Response:** `{ "services": [ ServiceType, ... ] }`

### `GET /api/v1/bot/services/{service_type}/plans`

List active plans for a service type.

**Path:** `service_type` — e.g. `v2ray`, `openvpn`

**Response:** `{ "plans": [ Plan, ... ] }`

```bash
curl http://localhost:8080/api/v1/bot/services/v2ray/plans \
  -H "X-Bot-Api-Key: changeme-bot-api-key"
```

---

## 1.3 Wallet

### `GET /api/v1/bot/users/{telegram_id}/wallet`

**Response:** `{ "user_id": 1, "balance_toman": 500 }`

---

## 1.4 Purchase flow

### `POST /api/v1/bot/purchase/preview`

Check if user can afford a plan.

**Body:**

| Field | Type | Required |
|-------|------|----------|
| `telegram_id` | string | yes |
| `plan_id` | int | yes |

**Response:**

```json
{
  "plan": { "...": "..." },
  "wallet_balance_toman": 100,
  "price_toman": 200,
  "sufficient_balance": false,
  "shortfall_toman": 100
}
```

### `POST /api/v1/bot/purchase`

Buy with wallet balance (fails with 400 if insufficient).

**Body:** same as preview

**Response:**

```json
{
  "subscription": { "...": "..." },
  "wallet_balance_toman": 0,
  "paid_from_wallet": true,
  "payment_request_id": null,
  "delivery": {
    "service_type": "openvpn",
    "subscription_id": 1,
    "delivery_type": "file",
    "content": "<ovpn file content>",
    "filename": "tg-123456789.ovpn"
  }
}
```

`delivery_type`: `"file"` (OpenVPN) or `"link"` (V2Ray subscription URL).

---

## 1.5 Renewal

### `POST /api/v1/bot/renew`

Renew subscription using wallet balance.

**Body:**

| Field | Type | Required |
|-------|------|----------|
| `telegram_id` | string | yes |
| `subscription_id` | int | yes |
| `plan_id` | int | yes |

**Response:** same shape as purchase result.

---

## 1.6 Payment flow (manual / receipt)

Used when wallet balance is insufficient.

### Step 1 — `POST /api/v1/bot/payments/initiate`

**Body:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `telegram_id` | string | yes | |
| `purpose` | string | yes | `purchase`, `renewal`, or `topup` |
| `amount_toman` | int | for `topup` | Ignored for purchase/renewal (plan price used) |
| `payment_method_id` | int | no | Selected payment method |
| `plan_id` | int | for purchase/renewal | |
| `subscription_id` | int | for renewal | |
| `service_type` | string | no | Usually inferred from plan |

**Purchase example:**

```bash
curl -X POST http://localhost:8080/api/v1/bot/payments/initiate \
  -H "Content-Type: application/json" \
  -H "X-Bot-Api-Key: changeme-bot-api-key" \
  -d '{
    "telegram_id": "123456789",
    "purpose": "purchase",
    "plan_id": 1,
    "payment_method_id": 1
  }'
```

**Top-up example:**

```bash
curl -X POST http://localhost:8080/api/v1/bot/wallet/topup/initiate \
  -H "Content-Type: application/json" \
  -H "X-Bot-Api-Key: changeme-bot-api-key" \
  -d '{"telegram_id":"123456789","amount_toman":50000}'
```

### Step 2 — `GET /api/v1/bot/users/{telegram_id}/payments/active`

Get the open payment awaiting receipt (`status = awaiting_receipt`).

### Step 3 — `POST /api/v1/bot/payments/{payment_request_id}/receipt`

Submit receipt after user pays.

**Body:**

| Field | Type | Required |
|-------|------|----------|
| `telegram_id` | string | yes |
| `receipt_file_id` | string | yes | Telegram file_id of receipt photo |
| `receipt_message_id` | int | no |

Status becomes `pending_approval`. Admin is notified via bot.

### `GET /api/v1/bot/payment-methods`

List active payment methods for users.

---

## 1.7 My services & support

### `GET /api/v1/bot/users/{telegram_id}/services`

**Response:**

```json
{
  "services": [
    {
      "subscription_id": 1,
      "service_type": "openvpn",
      "plan_name": "10 GB Monthly",
      "status_label": "active",
      "is_active": true,
      "remaining_days": 25,
      "remaining_bytes": 8589934592,
      "remaining_data_label": "8.00 GB",
      "expire_at": "2026-07-06T10:00:00Z"
    }
  ]
}
```

### `GET /api/v1/bot/support`

**Response:** `{ "support_username": "support_bot", "payment_instructions": "..." }`

---

# 2. Admin Bot APIs

Prefix: `/api/v1/admin/bot`  
Auth: `X-Bot-Api-Key` + `X-Admin-Telegram-Id`

---

## 2.1 Payment approval

### `GET /api/v1/admin/bot/payments/pending`

List all payments with `status = pending_approval`.

### `POST /api/v1/admin/bot/payments/{payment_request_id}/approve`

**Body:** `{ "admin_note": "optional note" }`

**What happens on approve:**

1. Wallet credited with payment amount  
2. If `purpose = purchase` or `renewal`: plan cost deducted, subscription created/renewed, config generated  
3. If `purpose = topup`: wallet credited only  
4. Payment marked `completed`

**Response:**

```json
{
  "payment_request_id": 1,
  "wallet_balance_toman": 0,
  "purchase": { "...PurchaseResultDTO or null for topup..." }
}
```

### `POST /api/v1/admin/bot/payments/{payment_request_id}/reject`

**Body:** `{ "admin_note": "reason" }`

---

# 3. Admin Commerce APIs

Prefix: `/api/v1/admin/commerce`  
Auth: admin headers

---

## 3.1 Service types

| Method | Path | Description |
|--------|------|-------------|
| GET | `/service-types` | List all service types |
| POST | `/service-types` | Create new type |
| PATCH | `/service-types/{slug}` | Update display name, description, sort order |
| POST | `/service-types/{slug}/enable` | Enable for bot catalog |
| POST | `/service-types/{slug}/disable` | Hide from bot catalog |

**Create body:**

```json
{
  "slug": "wireguard",
  "display_name": "WireGuard service",
  "description": "WireGuard configs",
  "is_enabled": true,
  "sort_order": 3
}
```

**Patch body (all optional):** `display_name`, `description`, `is_enabled`, `sort_order`

---

## 3.2 Bot settings

| Method | Path | Description |
|--------|------|-------------|
| GET | `/bot-settings` | Get support username + payment instructions |
| PATCH | `/bot-settings` | Update settings |

**Patch body:**

```json
{
  "support_username": "my_support",
  "payment_instructions": "Pay to card 6037-XXXX-XXXX-XXXX then upload receipt."
}
```

---

# 4. Admin Billing APIs

Prefix: `/api/v1/admin/billing`  
Auth: admin headers

---

## 4.1 Payment methods

| Method | Path | Description |
|--------|------|-------------|
| GET | `/payment-methods` | List all methods |
| POST | `/payment-methods` | Create |
| PATCH | `/payment-methods/{method_id}` | Update |
| DELETE | `/payment-methods/{method_id}` | Delete |

**Create body:**

```json
{
  "name": "Bank card",
  "instructions": "Card: 6037-1234-5678-9012\nName: VPN Shop",
  "is_active": true,
  "sort_order": 1
}
```

---

## 4.2 Wallets

| Method | Path | Description |
|--------|------|-------------|
| GET | `/wallets/{user_id}` | Get wallet |
| POST | `/wallets/credit` | Manually credit wallet |
| GET | `/wallets/{user_id}/transactions` | Transaction history |

**Credit body:**

```json
{
  "user_id": 1,
  "amount_toman": 10000,
  "description": "Manual adjustment"
}
```

---

## 4.3 Payment requests

### `GET /api/v1/admin/billing/payment-requests`

**Query params:**

| Param | Description |
|-------|-------------|
| `status` | Filter by status, e.g. `pending_approval` |
| `user_id` | Filter by user |

---

# 5. Admin Subscription / Plans

Prefix: `/api/v1/admin/subscription`  
Auth: admin headers

| Method | Path | Description |
|--------|------|-------------|
| GET | `/plans` | List all plans |
| POST | `/plans` | Create plan |
| PATCH | `/plans/{plan_id}` | Update plan |
| DELETE | `/plans/{plan_id}` | Delete plan |

**Create plan example (10 GB for 200 Toman, V2Ray):**

```bash
curl -X POST http://localhost:8080/api/v1/admin/subscription/plans \
  -H "Content-Type: application/json" \
  -H "X-Bot-Api-Key: changeme-bot-api-key" \
  -H "X-Admin-Telegram-Id: 123456789" \
  -d '{
    "name": "10 GB / 30 days",
    "description": "V2Ray basic plan",
    "service_type": "v2ray",
    "duration_days": 30,
    "traffic_limit_bytes": 10737418240,
    "price_toman": 200,
    "is_active": true
  }'
```

**300 GB for 300 Toman (OpenVPN):**

```json
{
  "name": "300 GB / 30 days",
  "service_type": "openvpn",
  "duration_days": 30,
  "traffic_limit_bytes": 322122547200,
  "price_toman": 300,
  "is_active": true
}
```

**Patch body (all optional):** `name`, `description`, `service_type`, `duration_days`, `traffic_limit_bytes`, `price_toman`, `is_active`

---

# 6. Core Subscription APIs

Prefix: `/api/v1/subscription`  
Auth: none (internal)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/users` | Create user |
| GET | `/users` | List users |
| GET | `/users/{user_id}` | Get user |
| POST | `/plans` | Create plan |
| GET | `/plans` | List plans (`?service_type=v2ray&active_only=true`) |
| GET | `/plans/{plan_id}` | Get plan |
| POST | `/subscriptions` | Create subscription |
| GET | `/subscriptions` | List (`?user_id=1`) |
| GET | `/subscriptions/{subscription_id}` | Get subscription |
| PATCH | `/subscriptions/{subscription_id}/status` | Update status |
| POST | `/traffic` | Record traffic usage |
| GET | `/subscriptions/{subscription_id}/traffic` | List traffic records |

**Create subscription body:**

```json
{
  "user_id": 1,
  "plan_id": 1,
  "service_type": "openvpn",
  "uuid": "optional-custom-uuid"
}
```

**Update status body:**

```json
{ "status": "disabled" }
```

**Record traffic body:**

```json
{
  "subscription_id": 1,
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "upload_bytes": 1000,
  "download_bytes": 5000,
  "total_bytes": 6000
}
```

---

# 7. OpenVPN APIs

Prefix: `/api/v1/openvpn`  
Auth: none (internal)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/provision` | Create OpenVPN config on a server |
| GET | `/users/{user_id}/configs` | List user configs (`?server_id=1`) |
| GET | `/configs/{config_id}` | Get single config |
| POST | `/deactivate` | Revoke user configs |
| POST | `/traffic/report` | Report bandwidth usage |

**Provision body:**

```json
{
  "user_id": 1,
  "server_id": 1,
  "subscription_id": 1,
  "config_count": 1
}
```

**Deactivate body:**

```json
{ "user_id": 1, "reason": "manual" }
```

**Traffic report body:**

```json
{ "user_id": 1, "subscription_id": 1, "bytes_used": 1048576 }
```

---

# 8. Server Management APIs

Prefix: `/api/v1/servers`  
Auth: none (internal)

| Method | Path | Description |
|--------|------|-------------|
| POST | `` | Register VPN server |
| GET | `` | List servers (filters via query) |
| GET | `/{server_id}` | Get server |
| PUT | `/{server_id}` | Full update |
| PATCH | `/{server_id}/status` | Update status |
| PATCH | `/{server_id}/monitoring` | Update resource metrics |
| DELETE | `/{server_id}` | Delete server |

**Create server (minimal OpenVPN example):**

```json
{
  "name": "DE-OpenVPN-1",
  "country_code": "DE",
  "cpu_cores": 2,
  "ram_mb": 2048,
  "disk_gb": 40,
  "connection": { "host": "10.0.0.5", "api_port": 8090 },
  "capacity": { "max_bandwidth_mbps": 1000 },
  "openvpn": {
    "enabled": true,
    "node_api_secret": "shared-secret",
    "vpn_host": "vpn.example.com"
  }
}
```

---

# 9. End-to-end flows

## A. Buy service (wallet)

```
POST /bot/users/register
GET  /bot/services
GET  /bot/services/{type}/plans
POST /bot/purchase/preview
POST /bot/purchase          → returns delivery (config or link)
```

## B. Buy service (manual payment)

```
POST /bot/purchase/preview          → insufficient balance
GET  /bot/payment-methods
POST /bot/payments/initiate         → purpose=purchase, plan_id=...
[user pays and uploads receipt in Telegram]
POST /bot/payments/{id}/receipt
[admin approves]
POST /admin/bot/payments/{id}/approve → wallet credited, cost deducted, config sent
```

## C. Wallet top-up

```
POST /bot/wallet/topup/initiate     → amount_toman=50000
[user pays and uploads receipt]
POST /bot/payments/{id}/receipt
POST /admin/bot/payments/{id}/approve → wallet credited only
```

## D. Admin setup (first time)

```
POST /admin/commerce/service-types/{slug}/enable
POST /admin/subscription/plans
POST /admin/billing/payment-methods
PATCH /admin/commerce/bot-settings
```

---

# 10. Error codes

| Code | Meaning |
|------|---------|
| 401 | Invalid or missing `X-Bot-Api-Key` |
| 403 | Admin Telegram ID not authorized |
| 404 | Resource not found |
| 400 | Business rule violation (e.g. insufficient balance, inactive plan) |
| 500 | Server error |

---

# 11. Byte conversion cheat sheet

| Size | Bytes |
|------|-------|
| 10 GB | 10,737,418,240 |
| 100 GB | 107,374,182,400 |
| 300 GB | 322,122,547,200 |
| 1 TB | 1,099,511,627,776 |

Formula: `GB × 1024 × 1024 × 1024`
