#!/bin/bash
# Test script for Car Buyer Scenario

BASE_URL="http://localhost:8001"
CUSTOMER_ID="car_buyer_preferences_test"

echo "=== 1. New Interaction: Car Inquiry ==="
curl -s -X POST "$BASE_URL/conversation" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "'"$CUSTOMER_ID"'",
    "channel": "chat",
    "content": "Hello, I am looking to buy a new car possibly a sedan. I like the color black. I have a budget of around 12 lakhs. I would prefer from any Japanese companies maybe Toyota or Honda. If I can get it in the color black I might extend my budget to 15 or 17 lakhs."
  }' | python3 -m json.tool
echo ""

echo "=== 2. Retrieve Unified Profile ==="
curl -s "$BASE_URL/customer/$CUSTOMER_ID/context" | python3 -m json.tool
echo ""
