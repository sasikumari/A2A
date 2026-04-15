#!/bin/bash

BASE_URL="http://127.0.0.1:5000"

echo "Testing /push..."
PUSH_RESPONSE=$(curl -s -X POST $BASE_URL/push \
  -H "Content-Type: application/xml" \
  --data-binary @reqpay_demo.xml)
echo "Response: $PUSH_RESPONSE"

# Extract RRN if possible (simple grep/sed as fallback if jq not present)
RRN=$(echo $PUSH_RESPONSE | grep -o '"rrn": *"[^"]*"' | cut -d'"' -f4)

if [ -n "$RRN" ]; then
    echo "Got RRN: $RRN"
    echo "Testing /status for RRN: $RRN..."
    STATUS_XML="<StatusRequest><RRN>$RRN</RRN></StatusRequest>"
    curl -s -X POST $BASE_URL/status \
      -H "Content-Type: application/xml" \
      --data-binary "$STATUS_XML"
    echo ""
else
    echo "Could not extract RRN from push response."
fi

echo "Testing /collect..."
curl -s -X POST $BASE_URL/collect \
  -H "Content-Type: application/xml" \
  --data-binary '<CollectRequest><PayeeVPA>merchant@benef</PayeeVPA><PayerVPA>alice@payer</PayerVPA><Amount>1.00</Amount><Note>demo</Note></CollectRequest>'
echo ""

echo "Testing /reqpay..."
curl -s -X POST $BASE_URL/reqpay \
  -H "Content-Type: application/xml" \
  --data-binary @reqpay_demo.xml
echo ""

echo "Testing /transactions..."
curl -s -X GET $BASE_URL/transactions
echo ""
