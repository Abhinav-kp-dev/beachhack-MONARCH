#!/bin/bash
# Test script for Updating Customer Preferences

BASE_URL="http://localhost:8001"
CUSTOMER_ID="car_buyer_preferences_test"

echo "=== 2. Update Interaction: Changed Mind ==="
curl -s -X POST "$BASE_URL/conversation" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "'"$CUSTOMER_ID"'",
    "channel": "chat",
    "content": "so I previously told you that I was looking for a sedan but now I changed my decision and I came to like hatchback cars and my preference color is black and the budget is decreased to 8 lakhs can you suggest some models from companies like Toyota or Honda which goes with my preferences"
  }' | python3 -m json.tool
echo ""

echo "=== 3. Retrieve Updated Unified Profile ==="
curl -s "$BASE_URL/customer/$CUSTOMER_ID/context" | python3 -m json.tool
echo ""
