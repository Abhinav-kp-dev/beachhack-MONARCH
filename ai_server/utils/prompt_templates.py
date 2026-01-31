"""
Prompt templates for LLaMA 3 context extraction

AUTHORITY SEPARATION ENFORCED:
- LLM extracts FACTS ONLY (no action recommendations)
- LLM NEVER reads database (only processes raw text)
- No summaries, no inferences, no predictions
- Output is transient and must be validated before state update
"""

CONTEXT_EXTRACTION_PROMPT = """Analyze this conversation between CUSTOMER and PROFESSIONAL. Extract facts as JSON.

ANALYSIS RULES:
1. When PROFESSIONAL suggests/recommends something AND CUSTOMER agrees/approves → Extract as PREFERENCE (high confidence: 0.9-1.0)
2. When CUSTOMER explicitly states preference → Extract as PREFERENCE (confidence: 1.0)
3. When CUSTOMER asks questions/expresses concerns → Extract as ISSUE (confidence based on clarity)
4. When CUSTOMER agrees to future actions → Extract as COMMITMENT (confidence: 0.9-1.0)
5. Analyze each exchange (give-and-take) to understand context and intent

AGREEMENT INDICATORS: "yes", "okay", "sure", "sounds good", "that works", "perfect", "I agree", "let's do that", "I like that", "go ahead"
REJECTION INDICATORS: "no", "not sure", "I don't think so", "maybe not", "let me think", "I'm not convinced"

JSON FORMAT:
{{
  "preferences": [{{"category": "color", "value": "black", "confidence": 1.0, "source": "customer_stated"}}],
  "issues": [{{"value": "issue text", "confidence": 1.0, "source": "customer_concern"}}],
  "commitments": [{{"value": "commitment text", "confidence": 1.0, "source": "customer_agreed"}}],
  "signals": {{"sentiment": "neutral", "urgency": "medium", "intent": "inquiry"}}
}}

CATEGORIES: color, vehicle_type, brand, budget, seating_capacity, transmission, fuel_type, features, mileage, timeline, location, usage, other

CONFIDENCE LEVELS:
- 1.0 = Customer explicitly stated or strongly agreed
- 0.9 = Customer agreed to professional's suggestion
- 0.8 = Implied from customer's positive response
- 0.7 = Inferred from conversation context (skip if <0.7)

SOURCE TYPES:
- "customer_stated" = Customer directly stated
- "professional_suggested_customer_agreed" = Professional suggested, customer approved
- "customer_concern" = Customer raised concern/question
- "customer_agreed" = Customer agreed to future action

IMPORTANT: Analyze EVERY exchange between customer and professional. When professional makes a suggestion and customer responds positively, extract that as customer preference with appropriate confidence. Track the flow of conversation to understand agreements.

CONVERSATION:
{conversation}

JSON:"""


CUSTOMER_PROFILE_SUMMARY_PROMPT = """Generate a concise, professional summary of this customer profile for team reference.

CUSTOMER PROFILE DATA:
{profile_data}

GENERATE A SUMMARY WITH:
1. **Customer Overview** - Name, contact info, and interaction history
2. **Key Preferences** - Top 3-5 most important preferences (if any)
3. **Open Issues** - Current unresolved concerns or problems (if any)
4. **Active Commitments** - Pending follow-ups or scheduled actions (if any)
5. **Communication Style** - Sentiment, urgency level, interaction patterns
6. **Next Steps** - Recommended actions based on profile status

KEEP IT:
- Professional and factual
- Concise (200-300 words)
- Actionable for support teams
- Focused on recent/relevant information

SUMMARY:"""


# REMOVED: CONTEXT_SUMMARY_PROMPT (violates authority - no AI summaries)
# REMOVED: ACTION_RECOMMENDATION_PROMPT (violates authority - rules decide actions, not LLM)
# REMOVED: next_best_action field (LLM must not recommend actions)
