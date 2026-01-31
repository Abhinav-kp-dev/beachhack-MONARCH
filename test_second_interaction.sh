#!/bin/bash
# Test script for Second Interaction (Follow-up)

BASE_URL="http://localhost:8001"
CUSTOMER_ID="car_buyer_complex_001"

echo "=== 2. Follow-up Interaction: Rescheduling & Budget Update ==="
curl -s -X POST "$BASE_URL/conversation" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "'"$CUSTOMER_ID"'",
    "channel": "chat",
    "content": "Agent: Hello... Customer: Hi Neha, this is the same person who spoke to you last week... Agent: Yes, I remember... Customer: ... I want to stay closer to 11 or 12 lakhs. Stretching beyond that feels uncomfortable now... Agent: Understood. So we’ll treat 12 lakhs as a firm upper limit for now... Customer: Yes, exactly... Customer: Yes, but this time please make it sometime on Saturday morning."
  }' | python3 -m json.tool
echo ""

echo "=== 3. Retrieve Updated Unified Profile ==="
curl -s "$BASE_URL/customer/$CUSTOMER_ID/context" | python3 -m json.tool
echo ""
