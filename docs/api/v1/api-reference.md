# GreenLedger API v1 Reference

**Version:** 1.0  
**Base URL:** `https://api.greenledger.com/v1`  
**Status:** Draft

---

## Table of Contents

1. [Authentication](#authentication)
2. [Endpoints](#endpoints)
3. [Data Models](#data-models)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)
6. [Examples](#examples)

---

## Authentication

### API Keys

All API requests require authentication using API keys.

```http
Authorization: Bearer YOUR_API_KEY
```

### Getting an API Key

[To be detailed]

---

## Endpoints

### Activities

#### List Activities
```http
GET /activities
```

**Parameters:**
- `scope` (optional): Filter by emission scope (1, 2, 3)
- `page` (optional): Page number
- `per_page` (optional): Items per page

**Response:**
```json
{
  "data": [],
  "pagination": {}
}
```

#### Create Activity
```http
POST /activities
```

**Request Body:**
```json
{
  "name": "string",
  "scope": 1,
  "emission_factor_id": "uuid",
  "quantity": 0.0,
  "unit": "string"
}
```

### Emissions

#### Calculate Emissions
```http
POST /emissions/calculate
```

**Request Body:**
```json
{
  "activity_id": "uuid",
  "quantity": 0.0
}
```

**Response:**
```json
{
  "emission_value": 0.0,
  "unit": "kg CO2e",
  "activity": {}
}
```

### Reports

#### List Reports
```http
GET /reports
```

#### Generate Report
```http
POST /reports
```

**Request Body:**
```json
{
  "report_type": "cbam|footprint",
  "period_start": "YYYY-MM-DD",
  "period_end": "YYYY-MM-DD",
  "activities": ["uuid"]
}
```

---

## Data Models

### Activity
```json
{
  "id": "uuid",
  "name": "string",
  "scope": 1,
  "emission_factor": {},
  "quantity": 0.0,
  "unit": "string",
  "created_at": "ISO 8601",
  "updated_at": "ISO 8601"
}
```

### Emission Factor
```json
{
  "id": "uuid",
  "activity": "string",
  "value": 0.0,
  "unit": "string",
  "scope": 1,
  "source": "string",
  "confidence": 1-5
}
```

### Report
```json
{
  "id": "uuid",
  "type": "cbam|footprint",
  "status": "draft|final|submitted",
  "period_start": "YYYY-MM-DD",
  "period_end": "YYYY-MM-DD",
  "total_emissions": 0.0,
  "created_at": "ISO 8601"
}
```

---

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {}
  }
}
```

### Error Codes

- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

---

## Rate Limiting

[To be detailed]

---

## Examples

### Python Example
```python
import requests

headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}

response = requests.get(
    "https://api.greenledger.com/v1/activities",
    headers=headers
)

print(response.json())
```

### cURL Example
```bash
curl -X GET "https://api.greenledger.com/v1/activities" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

**Document Status:** This is a template document. Content will be populated during API development.
