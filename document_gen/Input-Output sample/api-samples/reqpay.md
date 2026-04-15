## POST /reqpay

Flexible entrypoint that accepts NPCI-like `ReqPay` XML and routes based on `Txn@type`:
- `PAY`/`DEBIT` → push
- `COLLECT`/`CREDIT` → collect (auto-approved in demo)

Returns JSON ACK with RRN.

### Request (XML, push example)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<upi:ReqPay xmlns:upi="http://npci.org/upi/schema/">
  <upi:Head ver="1.0" ts="2025-01-01T00:00:00Z" orgId="PAYERPSP" msgId="REQUI" prodType="UPI"/>
  <upi:Txn id="REQ-456" type="PAY" note="reqpay push"/>
  <upi:Payer addr="alice@payer">
    <upi:Amount value="1.00"/>
    <upi:Creds><upi:Cred><upi:Data code="1234"/></upi:Cred></upi:Creds>
  </upi:Payer>
  <upi:Payees><upi:Payee addr="merchant@benef"/></upi:Payees>
</upi:ReqPay>
```

### Curl (push)

```bash
curl -s -X POST http://127.0.0.1:5000/reqpay \
  -H "Content-Type: application/xml" \
  --data-binary @reqpay_demo.xml
```

### Request (XML, collect example)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<upi:ReqPay xmlns:upi="http://npci.org/upi/schema/">
  <upi:Head ver="1.0" ts="2025-01-01T00:00:00Z" orgId="PAYERPSP" msgId="REQUI" prodType="UPI"/>
  <upi:Txn id="REQ-789" type="COLLECT" note="reqpay collect"/>
  <upi:Payer addr="alice@payer">
    <upi:Amount value="1.00"/>
  </upi:Payer>
  <upi:Payees><upi:Payee addr="merchant@benef"><upi:Amount value="1.00"/></upi:Payee></upi:Payees>
</upi:ReqPay>
```

### Response (JSON, 202 Accepted)

```json
{
  "rrn": "RRN1731300000789012",
  "status": "ACK"
}
```


