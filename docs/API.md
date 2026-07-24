# CredLens API Reference

## Base URL

```
http://localhost:8000
```

## Health Check

### `GET /`

Returns system status including database, MLflow, and auth availability.

**Response:**
```json
{
  "message": "CredLens API v2.0 is running.",
  "supported_markets": ["US", "IN"],
  "database_connected": true,
  "mlflow_enabled": true,
  "auth_enabled": true,
  "version": "2.0.0"
}
```

---

## Score Endpoints

### `GET /api/v1/score/{ticker}`

Analyze a stock ticker's creditworthiness.

**Parameters:**
| Parameter | Type   | Description |
|-----------|--------|-------------|
| `ticker`  | string | Stock ticker symbol (e.g., `AAPL`, `RELIANCE.NS`, `TCS.BO`) |

**Indian Ticker Format:**
- `.NS` suffix → NSE (National Stock Exchange)
- `.BO` suffix → BSE (Bombay Stock Exchange)

**Response:**
```json
{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "market": "US",
  "currency": "USD",
  "exchange": "NASDAQ",
  "country": "United States",
  "flag": "🇺🇸",
  "agency_rating": "AA+",
  "company_info": { ... },
  "score_result": {
    "stability_score": 78,
    "technical_score": 72,
    "fundamental_score": 85,
    "explanation": [...],
    "assessment_type": "ML_Model",
    "model_source": "registry",
    "latest_sentiment": 0.15
  },
  "stock_history": { ... },
  "recent_news_for_context": [...]
}
```

### `GET /api/v1/ratings/{ticker}`

Get the credit agency rating for a ticker.

**Response:**
```json
{
  "ticker": "RELIANCE.NS",
  "market": "IN",
  "rating": "CRISIL AAA",
  "agency": "CRISIL/ICRA"
}
```

---

## Company Endpoints

### `GET /api/v1/companies`

List tracked companies.

**Query Parameters:**
| Parameter | Type   | Default | Description |
|-----------|--------|---------|-------------|
| `market`  | string | null    | Filter: `US` or `IN` |
| `limit`   | int    | 50      | Max results (1-200) |
| `offset`  | int    | 0       | Pagination offset |

### `GET /api/v1/companies/search?q={query}`

Search companies by name or ticker.

### `GET /api/v1/companies/{ticker}/history`

Get score history for a ticker.

---

## Auth Endpoints

### `POST /api/v1/auth/register`

Register a new account.

**Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "full_name": "John Doe"
}
```

### `POST /api/v1/auth/login`

Login (OAuth2 password flow).

**Body (form-data):**
- `username`: email address
- `password`: password

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "email": "user@example.com",
  "full_name": "John Doe"
}
```

### `GET /api/v1/auth/me` 🔒

Get current user profile. Requires `Authorization: Bearer <token>`.

### `POST /api/v1/auth/refresh` 🔒

Refresh access token.

### `POST /api/v1/auth/watchlist` 🔒

Add ticker to watchlist. Body: `{"ticker": "AAPL"}`

### `DELETE /api/v1/auth/watchlist/{ticker}` 🔒

Remove ticker from watchlist.

---

## Alert Endpoints (all 🔒 auth required)

### `GET /api/v1/alerts/types`

Get available alert types.

### `GET /api/v1/alerts`

List user's alert rules.

### `POST /api/v1/alerts`

Create a new alert rule.

**Body:**
```json
{
  "ticker": "AAPL",
  "alert_type": "score_drop",
  "threshold": 15,
  "channel": "in_app"
}
```

**Alert Types:**
| Type         | Description | Default Threshold |
|--------------|-------------|-------------------|
| `score_drop` | Score drops by N+ points | 15 |
| `volatile`   | Score below threshold | 50 |
| `news_spike` | N+ negative news in 24h | 3 |
| `recovery`   | Score recovers above threshold | 75 |

### `DELETE /api/v1/alerts/{id}`

Delete an alert rule.

### `PATCH /api/v1/alerts/{id}/toggle`

Toggle alert active/inactive.

### `GET /api/v1/alerts/history`

Get past notifications.
