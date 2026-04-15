## POST /status

Poll transaction status by RRN. Returns `StatusResponse` XML.

### Request (XML)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<StatusRequest>
  <RRN>RRN1731300000123456</RRN>
</StatusRequest>
```

### Curl

```bash
curl -s -X POST http://127.0.0.1:5000/status \
  -H "Content-Type: application/xml" \
  --data-binary '<?xml version="1.0" encoding="UTF-8"?><StatusRequest><RRN>RRN1731300000123456</RRN></StatusRequest>'
```

### Response (XML, 200 OK)

```xml
<?xml version='1.0' encoding='utf-8'?>
<StatusResponse>
  <RRN>RRN1731300000123456</RRN>
  <Status>SUCCESS</Status>
</StatusResponse>
```


