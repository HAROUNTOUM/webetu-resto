# API notes (reverse-engineered)

These notes document the unofficial HTTP API used by the Android **Webetu**
application on the ONOU (Office National des Œuvres Universitaires) network.
They exist so the client can be maintained when the mobile app changes.

> This project is **not affiliated** with MESRS or ONOU. The API is private and
> undocumented. Endpoints, field names and rules can change without notice.
> The APK itself is **not** distributed with this repository.

The flow below was validated against a real student account during the v0.1
development. No credentials, JWT or personal data appear in these notes.

## Two services

| Service | Base URL | Auth |
|---|---|---|
| Student data (`progres`) | `https://api-webetu.mesrs.dz` | `Authorization: <jwt>` (raw, **no** `Bearer`) |
| Restaurant (`resto`) | `https://gs-api.onou.dz` | `Authorization: Bearer <jwt>` + HMAC headers |

A single login JWT is used by both. It is valid for roughly 24 hours; the tool
logs in again on every run rather than trying to refresh it.

## 1. Login

```http
POST /api/authentication/v1/
Content-Type: application/json

{"username":"<matricule>","password":"<password>"}
```

Response (fields used by this project):

```json
{
  "token": "eyJ...",
  "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "idIndividu": 123456,
  "etablissementId": 654321,
  "expirationDate": "2026-11-13T00:00:00",
  "userName": "202212345678",
  "wilaya": "06"
}
```

The body must be compact JSON and the exact bytes are **not** signed on this
endpoint. A wrong password returns `401`/`403`.

## 2. Student context

All calls below use the progres base URL and the raw JWT in `Authorization`.
The app also sends `X-IND-ID` (individual id) and `X-DIA-ID` (DIA id).

### 2.1 Academic year

```http
GET /api/infos/AnneeAcademiqueEncours
```

```json
{"code":"2026/2027","id":25}
```

### 2.2 DIA (dossier)

```http
GET /api/infos/bac/{uuid}/anneeAcademique/{year_id}/dia
```

```json
{"id":12345678,"anneeAcademiqueId":25,"etablissementId":987654, "...":"..."}
```

Only `id` is used.

### 2.3 Wilaya of inscription

```http
GET /api/infos/wilayaInscription/{dia_id}
```

The response is a **JSON string**, not a JSON object:

```json
"06"
```

### 2.4 Housing request (residence)

```http
GET /api/infos/bac/{uuid}/demandesHebregement
```

```json
[
  {
    "idAnneeAcademique": 25,
    "idResidance": 5550001,
    "llResidanceLatin": "Résidence ...",
    "llResidanceArabe": "...",
    "llDouLatin": "..."
  }
]
```

Pick the entry whose `idAnneeAcademique` matches the current year, then keep
`idResidance`. This id is required by every resto call.

> Do not call `/api/bac` on its own; the gateway answers **421 Misdirected
> Request**. The `/api/infos/...` prefix is mandatory.

## 3. Resto session

The resto service refuses every endpoint until this call succeeds:

```http
POST /api/loginpwebetu
Authorization: Bearer <jwt>
Content-Type: application/json
X-Timestamp: <unix seconds>
X-Nonce: <random uuid>
X-Signature: <hex hmac>

{
  "uuid": "<uuid>",
  "wilaya": "06",
  "residence": 5550001,
  "token": "<jwt>"
}
```

Response:

```json
{"token":"<resto session token>"}
```

The resto token is then sent as a **query parameter** named `token` on the other
resto endpoints:

```
?uuid=...&wilaya=06&residence=5550001&token=<resto token>
```

A missing resto login or an expired JWT shows up as **401 Unauthenticated**.

## 4. Restaurants

```http
GET /api/getdepotres?uuid=...&wilaya=06&residence=...&token=...
```

```json
{
  "depots": [
    {
      "id": 68,
      "nameFR": "RU EXAMPLE 02",
      "nameAR": "...",
      "isRu": 1,
      "breakfast": 1,
      "lunch": 1,
      "dinner": 1
    }
  ]
}
```

`id` is the `idDepot` used in reservations. `isRu=1` marks a university
restaurant. Flag values are integers (`0`/`1`).

**The meal is only valid in the restaurant where it was reserved.** The client
therefore always resolves one `idDepot` explicitly.

## 5. Existing reservations

```http
GET /api/meal-reservations/student?uuid=...&wilaya=...&residence=...&token=...&page=1
```

```json
{
  "data": [
    {
      "id": 65102937,
      "date_reserve": "2026-11-14",
      "mealtype_fr": "Petit-déjeuner",
      "mealtype_ar": "فطور",
      "depot_fr": "RU EXAMPLE 02",
      "candelete": true
    }
  ],
  "meta": {"last_page": 2, "per_page": 21}
}
```

Important details:

- The response is paginated; follow `meta.last_page`.
- There is **no numeric meal type** in the list. Map the French/Arabic label:
  `Petit-déjeuner`/`فطور` → 1, `Déjeuner`/`غداء` → 2, `Dîner`/`عشاء` → 3.
- `candelete` is `false` for same-day reservations (the 24-hour rule). Use it to
  decide whether a cancellation button can be shown.

## 6. Create reservations

One request can contain several meals. The `details` field is an **array of
JSON strings**, not an array of objects:

```http
POST /api/reservemeal
Authorization: Bearer <jwt>
Content-Type: application/json
X-Timestamp: ...
X-Nonce: ...
X-Signature: ...

{
  "uuid": "...",
  "wilaya": "06",
  "residence": 5550001,
  "token": "<jwt>",
  "details": [
    "{\"date_reserve\":\"2026-11-14\",\"menu_type\":1,\"idDepot\":68}",
    "{\"date_reserve\":\"2026-11-14\",\"menu_type\":2,\"idDepot\":68}"
  ]
}
```

Each inner string is compact JSON. The exact outer body bytes are what gets
signed. Meal types: `1` breakfast, `2` lunch, `3` dinner.

Success response:

```json
{
  "success": true,
  "data": [
    {"date":"2026-11-14","meal":"فطور","status":1,"message":"..."},
    {"date":"2026-11-14","meal":"غداء","status":0,"message":"..."}
  ]
}
```

`status` is `1` for success, `0` for a refused meal. A refusal is per-meal, so
the client maps results back to the requested `(date, meal)` pairs.

## 7. Cancel a reservation

```http
DELETE /api/reservemeal/{reservation_id}
Authorization: Bearer <jwt>
Content-Type: application/json
X-Timestamp: ...
X-Nonce: ...
X-Signature: ...

{"uuid":"...","wilaya":"06","residence":5550001,"token":"<jwt>"}
```

The body is signed like any other resto request. Cancellation is only allowed
while `candelete` is `true`, i.e. more than 24 hours before the meal.

## 8. HMAC request signing

Every resto request (including `GET` and `DELETE`) carries:

```http
X-Timestamp: 1700000000
X-Nonce: 3f1c... (uuid4)
X-Signature: <hex>
```

The signed message is the exact HTTP body bytes, framed as:

```
{timestamp}|{nonce}|{raw_body}
```

`X-Signature = HMAC-SHA256(key, message)` rendered as lowercase hex. For `GET`
requests the body is empty, so the message ends with the second `|`.

The key is an **application-wide constant** extracted from the Android app. It
is not a user secret and is not linked to any account. It is included in
`src/webetu_resto/signing.py` because the client cannot talk to the API without
it; treat it as public and expect it to change if ONOU rotates it.

The JSON body is serialized **once** as compact UTF-8 JSON
(`separators=(",", ":")`, `ensure_ascii=False`), then the same bytes are signed
and sent. Re-serializing with different spacing would break the signature.

## 9. Rules enforced by the server

- Reservation window: exactly **D+1, D+2 and D+3** (no same-day booking).
- A meal must be reserved at least **24 hours** before the meal time.
- One reservation per meal per day.
- A reserved meal can only be consumed in the restaurant where it was booked.
- `candelete` indicates whether a reservation can still be cancelled.

The tool runs **every day at 00:05 Africa/Algiers** and books D+1..D+3
idempotently. Running only every three days leaves gaps when a run fails; the
daily idempotent pass is deliberate.

## 10. Error handling used by the client

| Status | Meaning | Client behaviour |
|---|---|---|
| `401` / `403` | bad credentials or expired session | `AuthError`, no retry |
| `422` | validation error (e.g. malformed `details`) | `ApiError` with server message |
| `429`, `500`, `502`, `503`, `504` | transient | retry with backoff, then `ApiError` |
| network error | timeout, DNS, TLS | `NetworkError` after attempts |
| `200` with invalid JSON | gateway/HTML page | `ApiError` |

## 11. Provenance and testing

The mobile app is a Hermes/React Native bundle. The endpoints above were
recovered with `hermes-dec` and checked against the live service using a
personal account. The repository deliberately ships:

- no APK, no decompiled bundle;
- no credentials, JWT, tokens or personal identifiers;
- an offline test suite (`respx`) with synthetic responses.

If the API moves, update the constants and parsers in
`src/webetu_resto/client.py`; the rest of the code depends only on the
`WebetuClient` methods.
