## POST /validate-address

Triggers a ValAdd (Validate & Add) flow via the Payee PSP. Returns `RespValAdd` XML.

### Request (XML)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<upi:ReqValAdd xmlns:upi="http://npci.org/upi/schema/">
  <upi:Head ver="1.0" ts="2025-01-01T00:00:00Z" orgId="PAYERPSP" msgId="VALADD001" prodType="UPI"/>
  <upi:Txn id="VAL-001" type="ValAdd" ts="2025-01-01T00:00:00Z"/>
  <upi:Payer addr="alice@payer" name="PayerUser"/>
  <upi:Payee addr="merchant@benef"/>
</upi:ReqValAdd>
```

### Curl

```bash
curl -s -X POST http://127.0.0.1:5000/validate-address \
  -H "Content-Type: application/xml" \
  --data-binary '<?xml version="1.0" encoding="UTF-8"?><upi:ReqValAdd xmlns:upi="http://npci.org/upi/schema/"><upi:Head ver="1.0" ts="2025-01-01T00:00:00Z" orgId="PAYERPSP" msgId="VALADD001" prodType="UPI"/><upi:Txn id="VAL-001" type="ValAdd" ts="2025-01-01T00:00:00Z"/><upi:Payer addr="alice@payer" name="PayerUser"/><upi:Payee addr="merchant@benef"/></upi:ReqValAdd>'
```

### Response (XML, 200 OK)

```xml
<?xml version='1.0' encoding='utf-8'?>
<upi:RespValAdd xmlns:upi="http://npci.org/upi/schema/">
  <upi:Head ver="1.0" ts="2025-01-01T00:00:00Z" orgId="PAYEEPSP" msgId="VALADD_123456" prodType="UPI"/>
  <upi:Txn id="d0b1..." type="ValAdd" note="Address validation response" custRef="alice@payer"/>
  <upi:Resp reqMsgId="VALADD_REQ" result="SUCCESS" errCode="" maskName="mer****" code="00" type="VPA" IFSC="BENEBANK001" accType="SAVINGS" IIN="999999" pType="">
    <upi:Merchant>
      <upi:Identifier subCode="" mid="" sid="" tid="" merchantType="" merchantGenre="" pinCode="" regIdNo="" tier="" onBoardingType=""/>
      <upi:Name brand="" legal="" franchise=""/>
      <upi:Ownership type=""/>
    </upi:Merchant>
  </upi:Resp>
</upi:RespValAdd>
```


