#!/bin/bash
# API Test Script for Context-Aware Customer Intelligence System
# Server: http://192.168.220.76:8000

BASE_URL="http://localhost:8001"

echo "=============================================="
echo "Customer Intelligence System - API Tests"
echo "Server: $BASE_URL"
echo "=============================================="
echo ""

# Test 1: Health Check
echo "=== 1. GET /health ==="
curl -s "$BASE_URL/health" | python3 -m json.tool
echo ""

CONV_RESPONSE=$(curl -s -X POST "$BASE_URL/conversation" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "test_customer_123",
    "channel": "chat",
    "content": "Hello, I need help with my subscription. I want to upgrade to the premium plan but the website is showing an error when I try to checkout."
  }')
echo "$CONV_RESPONSE" | python3 -m json.tool
echo ""

# Test 3: Get Customer Context
echo "=== 3. GET /customer/{id}/context ==="
echo "Retrieving customer context..."
curl -s "$BASE_URL/customer/test_customer_123/context" | python3 -m json.tool
echo ""

curl -s -X POST "$BASE_URL/conversation" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "test_customer_123",
    "channel": "email",
    "content": "Subject: Re: Subscription Upgrade\n\nThank you for the quick response. I was able to upgrade successfully. I love the new features!"
  }' | python3 -m json.tool
echo ""

# Test 5: Get Updated Context
echo "=== 5. GET /customer/{id}/context (After Multiple Interactions) ==="
curl -s "$BASE_URL/customer/test_customer_123/context" | python3 -m json.tool
echo ""

# Test 6: Action Trigger
echo "=== 6. POST /action/trigger ==="
curl -s -X POST "$BASE_URL/action/trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "send_notification",
    "customer_id": "test_customer_123",
    "parameters": {
      "message": "Follow up with customer about premium features",
      "priority": "medium"
    }
  }' | python3 -m json.tool
echo ""

echo "=============================================="
echo "API Tests Complete!"
echo "=============================================="
