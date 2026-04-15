## POST /push

Initiate a push payment using NPCI-like ReqPay XML (namespaced). Returns JSON ACK with RRN.

Note: Use an existing payer and payee from the demo setup. Default working demo users are `alice@payer` and `merchant@benef` with PIN `1234`.

### Request (XML)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<upi:ReqPay xmlns:upi="http://npci.org/upi/schema/">
  <upi:Head ver="1.0" ts="2025-01-01T00:00:00Z" orgId="PAYERPSP" msgId="REQUI" prodType="UPI"/>
  <upi:Txn id="REQ-123" type="PAY" note="demo push"/>
  <upi:Payer addr="alice@payer">
    <upi:Amount value="1.00"/>
    <upi:Creds><upi:Cred><upi:Data code="1234"/></upi:Cred></upi:Creds>
  </upi:Payer>
  <upi:Payees><upi:Payee addr="merchant@benef"/></upi:Payees>
</upi:ReqPay>
```

### Curl

```bash
curl -s -X POST http://127.0.0.1:5000/push \
  -H "Content-Type: application/xml" \
  --data-binary @reqpay_demo.xml
```

Or inline:

```bash
curl -s -X POST http://127.0.0.1:5000/push \
  -H "Content-Type: application/xml" \
  --data-binary '<?xml version="1.0" encoding="UTF-8"?><upi:ReqPay xmlns:upi="http://npci.org/upi/schema/"><upi:Head ver="1.0" ts="2025-01-01T00:00:00Z" orgId="PAYERPSP" msgId="REQUI" prodType="UPI"/><upi:Txn id="REQ-123" type="PAY" note="demo push"/><upi:Payer addr="alice@payer"><upi:Amount value="1.00"/><upi:Creds><upi:Cred><upi:Data code="1234"/></upi:Cred></upi:Creds></upi:Payer><upi:Payees><upi:Payee addr="merchant@benef"/></upi:Payees></upi:ReqPay>'
```

### Response (JSON, 202 Accepted)

```json
{
  "rrn": "RRN1731300000123456",
  "status": "ACK"
}
```


