## POST /collect

Initiate a collect request from payee to payer. Returns JSON ACK with RRN. In the demo, the payer approval is simulated as auto-approve.

### Request (XML)

```xml
<CollectRequest>
  <PayeeVPA>merchant@benef</PayeeVPA>
  <PayerVPA>alice@payer</PayerVPA>
  <Amount>1.00</Amount>
  <Note>demo collect</Note>
</CollectRequest>
```

### Curl

```bash
curl -s -X POST http://127.0.0.1:5000/collect \
  -H "Content-Type: application/xml" \
  --data-binary '<CollectRequest><PayeeVPA>merchant@benef</PayeeVPA><PayerVPA>alice@payer</PayerVPA><Amount>1.00</Amount><Note>demo collect</Note></CollectRequest>'
```

### Response (JSON, 202 Accepted)

```json
{
  "rrn": "RRN1731300000456789",
  "status": "ACK"
}
```


