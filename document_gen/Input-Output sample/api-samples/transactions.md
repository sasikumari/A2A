## GET /transactions

Returns a JSON array of terminal transactions recorded by the in-memory ledger (latest first). Each entry is a dataclass serialized to JSON.

### Curl

```bash
curl -s http://127.0.0.1:5000/transactions | jq .
```

### Response (JSON, 200 OK)

```json
[
  {
    "rrn": "RRN1731300000123456",
    "payer_vpa": "alice@payer",
    "payee_vpa": "merchant@benef",
    "amount": 1.0,
    "note": "demo push",
    "utr_debit": "PAYERBANK25011123456789",
    "utr_credit": "BENEBANK25011123456789",
    "status": "SUCCESS",
    "created_at": "2025-01-01T00:00:10Z"
  }
]
```


