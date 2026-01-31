"""
Utility functions for calculating business metrics and context quality scores
"""

from typing import Dict, Any
from models import CustomerProfile
from datetime import datetime


def calculate_context_quality_score(customer_state: CustomerProfile) -> Dict[str, Any]:
    """
    Calculate context completeness score for a customer
    
    Scoring algorithm:
    - Each preference: +10 points (max 50)
    - Each open issue: +15 points (max 45)
    - Each commitment: +20 points (max 40)
    - Having name/email/phone: +5 points each
    - Recent interaction (< 30 days): +10 points
    
    Returns:
        Dict with score (0-100), breakdown, and quality level
    """
    score = 0
    breakdown = {}
    
    # Preferences (max 50 points)
    pref_score = min(len(customer_state.preferences) * 10, 50)
    score += pref_score
    breakdown['preferences'] = {
        'count': len(customer_state.preferences),
        'score': pref_score,
        'max': 50
    }
    
    # Issues (max 45 points)
    issues_score = min(len(customer_state.issues) * 15, 45)
    score += issues_score
    breakdown['issues'] = {
        'count': len(customer_state.issues),
        'score': issues_score,
        'max': 45
    }
    
    # Commitments (max 40 points)
    commitments_score = min(len(customer_state.commitments) * 20, 40)
    score += commitments_score
    breakdown['commitments'] = {
        'count': len(customer_state.commitments),
        'score': commitments_score,
        'max': 40
    }
    
    # Contact information completeness (15 points total)
    contact_score = 0
    if customer_state.name:
        contact_score += 5
    if customer_state.email:
        contact_score += 5
    if customer_state.phone:
        contact_score += 5
    score += contact_score
    breakdown['contact_info'] = {
        'has_name': bool(customer_state.name),
        'has_email': bool(customer_state.email),
        'has_phone': bool(customer_state.phone),
        'score': contact_score,
        'max': 15
    }
    
    # Recent interaction bonus (10 points)
    recency_score = 0
    if customer_state.last_interaction:
        days_since = (datetime.now() - customer_state.last_interaction).days
        if days_since < 30:
            recency_score = 10
        elif days_since < 90:
            recency_score = 5
    score += recency_score
    breakdown['recency'] = {
        'score': recency_score,
        'max': 10
    }
    
    # Determine quality level
    if score >= 80:
        quality_level = "excellent"
    elif score >= 60:
        quality_level = "good"
    elif score >= 40:
        quality_level = "fair"
    else:
        quality_level = "needs_improvement"
    
    return {
        'score': score,
        'max_score': 160,
        'percentage': round((score / 160) * 100, 1),
        'quality_level': quality_level,
        'breakdown': breakdown
    }


def calculate_time_saved(customer_state: CustomerProfile) -> Dict[str, Any]:
    """
    Estimate time saved by having context available
    
    Assumptions:
    - Each preference saves 15 seconds (not asking again)
    - Each issue tracked saves 30 seconds (continuity)
    - Each commitment tracked saves 20 seconds (follow-up efficiency)
    - Having contact info saves 10 seconds
    
    Returns:
        Dict with time saved in seconds, minutes, and per-interaction average
    """
    time_saved_seconds = 0
    breakdown = {}
    
    # Preferences time saved
    pref_time = len(customer_state.preferences) * 15
    time_saved_seconds += pref_time
    breakdown['preferences'] = {
        'count': len(customer_state.preferences),
        'seconds_saved': pref_time
    }
    
    # Issues time saved
    issues_time = len(customer_state.issues) * 30
    time_saved_seconds += issues_time
    breakdown['issues'] = {
        'count': len(customer_state.issues),
        'seconds_saved': issues_time
    }
    
    # Commitments time saved
    commitments_time = len(customer_state.commitments) * 20
    time_saved_seconds += commitments_time
    breakdown['commitments'] = {
        'count': len(customer_state.commitments),
        'seconds_saved': commitments_time
    }
    
    # Contact info time saved
    contact_time = 0
    if customer_state.name:
        contact_time += 3
    if customer_state.email:
        contact_time += 4
    if customer_state.phone:
        contact_time += 3
    time_saved_seconds += contact_time
    breakdown['contact_info'] = {
        'seconds_saved': contact_time
    }
    
    return {
        'total_seconds': time_saved_seconds,
        'total_minutes': round(time_saved_seconds / 60, 2),
        'formatted': f"{time_saved_seconds // 60}m {time_saved_seconds % 60}s",
        'breakdown': breakdown
    }


def calculate_roi_metrics(total_conversations: int, 
                         cost_per_conversation: float = 0.0025,
                         manual_cost_per_conversation: float = 5.0) -> Dict[str, Any]:
    """
    Calculate ROI metrics for the system
    
    Args:
        total_conversations: Total number of conversations processed
        cost_per_conversation: System cost per conversation (with optimizations)
        manual_cost_per_conversation: Cost of manual processing
        
    Returns:
        Dict with cost savings, ROI percentage, and breakdowns
    """
    system_cost = total_conversations * cost_per_conversation
    manual_cost = total_conversations * manual_cost_per_conversation
    savings = manual_cost - system_cost
    roi_percentage = ((savings / system_cost) * 100) if system_cost > 0 else 0
    
    return {
        'total_conversations': total_conversations,
        'system_cost': round(system_cost, 2),
        'manual_cost': round(manual_cost, 2),
        'total_savings': round(savings, 2),
        'roi_percentage': round(roi_percentage, 1),
        'cost_per_conversation': cost_per_conversation,
        'savings_per_conversation': round(manual_cost_per_conversation - cost_per_conversation, 2),
        'cost_reduction_percentage': round(((manual_cost - system_cost) / manual_cost) * 100, 1)
    }
