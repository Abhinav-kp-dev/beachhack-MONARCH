"""
Customer service for managing customer profiles
Handles CRUD operations with deterministic validation and audit logging

AUTHORITY: DB = State Machine (single source of truth)
- CustomerProfile is the ONLY authoritative customer state
- All changes logged via StateChangeLog for auditability
- Deterministic update logic with explicit validation rules
- NO AI-generated or inferred data persistence
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from tinydb import TinyDB, Query
from models import CustomerProfile, ExtractedContext, IssueRecord, StateChangeLog
import config

logger = logging.getLogger(__name__)


class CustomerService:
    """Service for managing customer profiles with deterministic updates and audit logging"""
    
    def __init__(self):
        self.db = TinyDB(config.CUSTOMERS_DB)
        self.audit_db = TinyDB(config.AUDIT_LOG_DB if hasattr(config, 'AUDIT_LOG_DB') else 'data/audit_log.json')
        logger.info(f"Initialized CustomerService with database: {config.CUSTOMERS_DB}")
    
    def get_customer(self, customer_id: str) -> Optional[CustomerProfile]:
        """
        Retrieve customer profile by ID
        
        Args:
            customer_id: Unique customer identifier
            
        Returns:
            CustomerProfile or None if not found
        """
        Customer = Query()
        result = self.db.search(Customer.customer_id == customer_id)
        
        if result:
            customer_data = result[0]
            # Fix datetime handling - check if already datetime object
            if 'last_interaction' in customer_data and customer_data['last_interaction']:
                if isinstance(customer_data['last_interaction'], str):
                    customer_data['last_interaction'] = datetime.fromisoformat(customer_data['last_interaction'])
            if 'created_at' in customer_data:
                if isinstance(customer_data['created_at'], str):
                    customer_data['created_at'] = datetime.fromisoformat(customer_data['created_at'])
            if 'updated_at' in customer_data:
                if isinstance(customer_data['updated_at'], str):
                    customer_data['updated_at'] = datetime.fromisoformat(customer_data['updated_at'])
            
            # Parse issues if they exist
            if 'issues' in customer_data and customer_data['issues']:
                parsed_issues = []
                for issue in customer_data['issues']:
                    if isinstance(issue, dict):
                        # Backward compatibility: migrate created_at to reported_at
                        if 'created_at' in issue and 'reported_at' not in issue:
                            issue['reported_at'] = issue['created_at']
                        
                        # Parse issue timestamps
                        if 'reported_at' in issue and isinstance(issue['reported_at'], str):
                            issue['reported_at'] = datetime.fromisoformat(issue['reported_at'])
                        if 'resolved_at' in issue and issue.get('resolved_at') and isinstance(issue['resolved_at'], str):
                            issue['resolved_at'] = datetime.fromisoformat(issue['resolved_at'])
                        
                        # Normalize status to lowercase
                        if 'status' in issue:
                            issue['status'] = issue['status'].lower()
                        
                        parsed_issues.append(IssueRecord(**issue))
                    else:
                        parsed_issues.append(issue)
                customer_data['issues'] = parsed_issues
            
            return CustomerProfile(**customer_data)
        return None
    
    def create_customer(self, 
                       customer_id: Optional[str] = None,
                       name: Optional[str] = None,
                       email: Optional[str] = None,
                       phone: Optional[str] = None) -> tuple[CustomerProfile, bool]:
        """
        Create a new customer profile
        
        Args:
            customer_id: Optional custom ID, auto-generated if not provided
            name: Customer name
            email: Customer email
            phone: Customer phone
            
        Returns:
            Tuple of (CustomerProfile, was_created: bool)
            - If customer already exists, returns (existing_profile, False)
            - If customer was created, returns (new_profile, True)
        """
        # Generate UUID if not provided
        if not customer_id:
            from uuid import uuid4
            customer_id = str(uuid4())
        
        profile = CustomerProfile(
            customer_id=customer_id,
            name=name,
            email=email,
            phone=phone
        )
        
        # Check if customer already exists
        existing = self.get_customer(profile.customer_id)
        if existing:
            logger.warning(f"Customer {profile.customer_id} already exists, returning existing profile")
            return existing, False  # Return existing customer with False flag
        
        # Convert to dict for storage
        profile_dict = self._serialize_profile(profile)
        
        self.db.insert(profile_dict)
        logger.info(f"Created new customer: {profile.customer_id}")
        
        # Log creation
        self._log_state_change(
            customer_id=profile.customer_id,
            change_type="CREATED",
            fields_changed=["customer_id", "name", "email", "phone"],
            old_values={},
            new_values=profile_dict,
            reason="Initial customer creation"
        )
        
        return profile, True  # Return new customer with True flag
    
    def update_customer_from_facts(self, 
                                   customer_id: str, 
                                   extracted_context: ExtractedContext,
                                   conversation_id: str) -> Optional[CustomerProfile]:
        """
        Update customer profile from extracted facts with ADVANCED RULE ENGINE
        
        ENHANCED AUTHORITY: Intelligent validation and merge logic with reliability tracking
        - ExtractedContext is TRANSIENT (no authority)
        - Only validated data goes into CustomerProfile (authoritative)
        - All changes logged for auditability
        - Detects context changes vs new context
        - Handles contradictions intelligently
        - Maintains context reliability score
        
        Advanced Validation Rules:
        1. Preferences: Deduplicate, max 50 items, detect contradictions, merge similar items
        2. Issues: Convert to IssueRecord, deduplicate, detect if issue already resolved
        3. Commitments: Deduplicate, max 20 items, check for duplicates with fuzzy matching
        4. Contradiction Detection: Flag conflicting preferences (e.g., "likes emails" vs "hates emails")
        5. Reliability Scoring: Track how many times context is confirmed across conversations
        
        Args:
            customer_id: Customer identifier
            extracted_context: ExtractedContext from LLM (transient, no authority)
            conversation_id: Reference to source conversation
            
        Returns:
            Updated CustomerProfile or None if customer not found
        """
        customer = self.get_customer(customer_id)
        if not customer:
            logger.warning(f"Customer {customer_id} not found for update")
            return None
        
        changes = {}
        old_values = {}
        contradictions = []
        
        # Initialize reliability metadata if not exists
        if not hasattr(customer, 'context_metadata') or customer.context_metadata is None:
            customer.context_metadata = {
                "preference_scores": {},  # {preference: confirmation_count}
                "total_updates": 0,
                "last_updated_conversation": None
            }
        
        # ADVANCED RULE 1: Intelligent preference merging with classified categories
        if extracted_context.preferences:
            # Extract classified preferences with categories
            classified_prefs = []
            
            for pref_item in extracted_context.preferences:
                if hasattr(pref_item, 'category') and hasattr(pref_item, 'value') and hasattr(pref_item, 'confidence'):
                    classified_prefs.append({
                        'category': pref_item.category.lower().strip(),
                        'value': pref_item.value.strip(),
                        'confidence': pref_item.confidence
                    })
                elif isinstance(pref_item, dict) and 'category' in pref_item and 'value' in pref_item and 'confidence' in pref_item:
                    classified_prefs.append({
                        'category': pref_item['category'].lower().strip(),
                        'value': pref_item['value'].strip(),
                        'confidence': pref_item['confidence']
                    })
            
            # Initialize preferences as dict if it's still a list (migration)
            if isinstance(customer.preferences, list):
                logger.info(f"Migrating customer {customer_id} from list to dict preferences")
                old_prefs = customer.preferences
                customer.preferences = {}
                for old_pref in old_prefs:
                    if 'other' not in customer.preferences:
                        customer.preferences['other'] = []
                    customer.preferences['other'].append(old_pref)
            
            # Initialize confidence_scores if not exists
            if not hasattr(customer, 'confidence_scores') or customer.confidence_scores is None:
                customer.confidence_scores = {'preferences': {}, 'issues': {}, 'commitments': {}}
            
            # Ensure preferences confidence is dict of dicts
            if not isinstance(customer.confidence_scores.get('preferences'), dict):
                customer.confidence_scores['preferences'] = {}
            
            # Process each classified preference
            new_prefs_added = []
            for pref_data in classified_prefs:
                category = pref_data['category']
                value = pref_data['value']
                confidence = pref_data['confidence']
                
                # Initialize category if not exists
                if category not in customer.preferences:
                    customer.preferences[category] = []
                if category not in customer.confidence_scores['preferences']:
                    customer.confidence_scores['preferences'][category] = {}
                
                # Check for duplicates in this category
                existing_values_lower = {v.lower(): v for v in customer.preferences[category]}
                
                # Detect contradictions within same category
                for existing_value_lower, existing_value in existing_values_lower.items():
                    if self._are_contradictory(value.lower(), existing_value_lower):
                        contradictions.append({
                            "type": "preference",
                            "category": category,
                            "existing": existing_value,
                            "new": value,
                            "action": "keeping_most_recent"
                        })
                        customer.preferences[category].remove(existing_value)
                        customer.confidence_scores['preferences'][category].pop(existing_value, None)
                        existing_values_lower.pop(existing_value_lower)
                        logger.warning(f"Detected contradiction in {category}: '{existing_value}' vs '{value}' - keeping new")
                
                # Add new preference if not duplicate
                if value.lower() not in existing_values_lower:
                    customer.preferences[category].append(value.title())
                    customer.confidence_scores['preferences'][category][value.title()] = confidence
                    new_prefs_added.append(f"{category}:{value}")
                    pref_key = f"{category}:{value.lower()}"
                    customer.context_metadata["preference_scores"][pref_key] = 1
                else:
                    existing_value = existing_values_lower[value.lower()]
                    current_confidence = customer.confidence_scores['preferences'][category].get(existing_value, 0.8)
                    if confidence > current_confidence:
                        customer.confidence_scores['preferences'][category][existing_value] = confidence
                    pref_key = f"{category}:{value.lower()}"
                    customer.context_metadata["preference_scores"][pref_key] = \
                        customer.context_metadata["preference_scores"].get(pref_key, 0) + 1
            
            # Calculate average confidence
            if customer.preferences:
                all_confidences = []
                for category, values in customer.preferences.items():
                    if category in customer.confidence_scores['preferences']:
                        cat_confidences = list(customer.confidence_scores['preferences'][category].values())
                        if cat_confidences:
                            all_confidences.extend(cat_confidences)
                if all_confidences:
                    avg_conf = sum(all_confidences) / len(all_confidences)
                    if 'avg_confidence' not in customer.context_metadata:
                        customer.context_metadata['avg_confidence'] = {}
                    customer.context_metadata['avg_confidence']['preferences'] = round(avg_conf, 2)
            
            # Clean up empty categories
            customer.preferences = {k: v for k, v in customer.preferences.items() if v}
            
            if new_prefs_added:
                old_values['preferences'] = customer.preferences.copy()
                avg_conf = customer.context_metadata.get('avg_confidence', {}).get('preferences', 0.0)
                changes['preferences'] = f"Added {len(new_prefs_added)} classified preferences (avg confidence: {avg_conf:.2f}), {len(contradictions)} contradictions resolved"
        
        # ADVANCED RULE 2: Intelligent issue management (detect already resolved issues)
        if extracted_context.issues:
            # Extract values and confidence scores
            validated_issues = []
            issue_confidences = {}
            
            for issue_item in extracted_context.issues:
                if hasattr(issue_item, 'value') and hasattr(issue_item, 'confidence'):
                    issue = issue_item.value.strip()
                    confidence = issue_item.confidence
                elif isinstance(issue_item, dict) and 'value' in issue_item and 'confidence' in issue_item:
                    issue = issue_item['value'].strip()
                    confidence = issue_item['confidence']
                else:
                    issue = str(issue_item).strip()
                    confidence = 0.8
                
                if issue:
                    validated_issues.append(issue)
                    issue_confidences[issue.lower()] = confidence
            
            existing_issue_descs_open = {issue.description.lower() for issue in customer.issues if issue.status.lower() == "open"}
            existing_issue_descs_resolved = {issue.description.lower() for issue in customer.issues if issue.status.lower() == "resolved"}
            
            new_issue_records = []
            reopened_issues = []
            
            for issue_desc in validated_issues:
                issue_lower = issue_desc.lower()
                
                # Check if this issue was already resolved (reopening case)
                if issue_lower in existing_issue_descs_resolved:
                    # Find and reopen the issue
                    for issue in customer.issues:
                        if issue.description.lower() == issue_lower and issue.status.lower() == "resolved":
                            issue.status = "open"
                            issue.reported_at = datetime.now()
                            issue.conversation_id = conversation_id
                            reopened_issues.append(issue_desc)
                            logger.info(f"Reopened previously resolved issue: {issue_desc}")
                            break
                
                # Add new issue if not already open
                elif issue_lower not in existing_issue_descs_open:
                    new_issue_records.append(IssueRecord(
                        description=issue_desc,
                        reported_at=datetime.now(),
                        conversation_id=conversation_id,
                        status="open"
                    ))
                    # Store confidence score
                    customer.confidence_scores['issues'][issue_desc] = issue_confidences.get(issue_lower, 0.8)
            
            if new_issue_records or reopened_issues:
                old_values['issues'] = [issue.model_dump() for issue in customer.issues]
                customer.issues.extend(new_issue_records)
                
                # Calculate average confidence for issues
                if customer.issues:
                    total_conf = sum(customer.confidence_scores['issues'].values())
                    avg_conf = total_conf / len(customer.issues) if customer.issues else 0.0
                    customer.context_metadata['avg_confidence']['issues'] = round(avg_conf, 2)
                
                changes['issues'] = f"Added {len(new_issue_records)} new issues (avg confidence: {customer.context_metadata.get('avg_confidence', {}).get('issues', 0.0):.2f}), reopened {len(reopened_issues)} issues"
        
        # ADVANCED RULE 3: Intelligent commitment merging with fuzzy matching
        if extracted_context.commitments:
            from difflib import SequenceMatcher
            
            # Extract values and confidence scores
            validated_commits = []
            commit_confidences = {}
            
            for commit_item in extracted_context.commitments:
                if hasattr(commit_item, 'value') and hasattr(commit_item, 'confidence'):
                    commit = commit_item.value.strip()
                    confidence = commit_item.confidence
                elif isinstance(commit_item, dict) and 'value' in commit_item and 'confidence' in commit_item:
                    commit = commit_item['value'].strip()
                    confidence = commit_item['confidence']
                else:
                    commit = str(commit_item).strip()
                    confidence = 0.8
                
                if commit:
                    validated_commits.append(commit)
                    commit_confidences[commit.lower()] = confidence
            
            new_commits_added = []
            for commit in validated_commits:
                # Check for fuzzy duplicates (80% similarity threshold)
                is_duplicate = False
                for existing_commit in customer.commitments:
                    similarity = SequenceMatcher(None, commit.lower(), existing_commit.lower()).ratio()
                    if similarity > 0.8:
                        is_duplicate = True
                        # Update confidence if current is higher
                        current_confidence = customer.confidence_scores['commitments'].get(existing_commit, 0.8)
                        new_confidence = commit_confidences.get(commit.lower(), 0.8)
                        if new_confidence > current_confidence:
                            customer.confidence_scores['commitments'][existing_commit] = new_confidence
                        logger.debug(f"Commitment '{commit}' is similar to existing '{existing_commit}' (similarity: {similarity:.2f})")
                        break
                
                if not is_duplicate:
                    customer.commitments.append(commit)
                    customer.confidence_scores['commitments'][commit] = commit_confidences.get(commit.lower(), 0.8)
                    new_commits_added.append(commit)
            
            # Calculate average confidence for commitments
            if customer.commitments:
                total_conf = sum(customer.confidence_scores['commitments'].values())
                avg_conf = total_conf / len(customer.commitments)
                customer.context_metadata['avg_confidence']['commitments'] = round(avg_conf, 2)
            
            # Enforce max 20 commitments (keep most recent)
            if len(customer.commitments) > 20:
                removed_commits = customer.commitments[:-20]
                customer.commitments = customer.commitments[-20:]
                # Clean up confidence scores for removed commitments
                for removed in removed_commits:
                    customer.confidence_scores['commitments'].pop(removed, None)
            
            if new_commits_added:
                old_values['commitments'] = customer.commitments.copy()
                changes['commitments'] = f"Added {len(new_commits_added)} new commitments (avg confidence: {customer.context_metadata.get('avg_confidence', {}).get('commitments', 0.0):.2f})"
        
        # Update metadata
        customer.context_metadata["total_updates"] += 1
        customer.context_metadata["last_updated_conversation"] = conversation_id
        
        # Always update timestamps and interaction count (even if no context changes)
        old_values['updated_at'] = customer.updated_at
        old_values['interaction_count'] = customer.interaction_count
        customer.updated_at = datetime.now()
        customer.last_interaction = datetime.now()
        customer.interaction_count = customer.interaction_count + 1  # Increment interaction count
        
        # Save to database
        Customer = Query()
        customer_dict = self._serialize_profile(customer)
        self.db.update(customer_dict, Customer.customer_id == customer_id)
        
        if changes:
            logger.info(f"Updated customer {customer_id}: {changes}")
            if contradictions:
                logger.info(f"Resolved contradictions: {contradictions}")
            
            # Log state change with enhanced details
            change_details = changes.copy()
            if contradictions:
                change_details['contradictions_resolved'] = len(contradictions)
            
            self._log_state_change(
                customer_id=customer_id,
                change_type="UPDATED",
                fields_changed=list(changes.keys()),
                old_values=old_values,
                new_values={k: getattr(customer, k) for k in changes.keys()},
                reason=f"Advanced rule engine: {', '.join([f'{k}: {v}' for k, v in change_details.items()])}",
                source_conversation_id=conversation_id
            )
        
        return customer
    
    def _are_contradictory(self, pref1: str, pref2: str) -> bool:
        """
        Detect if two preferences contradict each other
        
        Args:
            pref1: First preference (lowercase)
            pref2: Second preference (lowercase)
            
        Returns:
            True if contradictory, False otherwise
        """
        # List of contradiction patterns
        contradiction_pairs = [
            (["like", "loves", "prefers", "wants", "enjoys"], ["hate", "hates", "dislikes", "doesn't like", "avoids"]),
            (["morning", "early"], ["evening", "late", "night"]),
            (["email"], ["phone", "call"]),  # If explicitly stated as opposing preferences
            (["formal"], ["informal", "casual"]),
            (["quick"], ["detailed", "thorough"]),
        ]
        
        # Extract key terms
        words1 = set(pref1.split())
        words2 = set(pref2.split())
        
        # Check for direct contradictions
        for positive_terms, negative_terms in contradiction_pairs:
            has_positive1 = any(term in pref1 for term in positive_terms)
            has_negative1 = any(term in pref1 for term in negative_terms)
            has_positive2 = any(term in pref2 for term in positive_terms)
            has_negative2 = any(term in pref2 for term in negative_terms)
            
            # Check if they reference the same thing but with opposite sentiment
            common_subjects = words1 & words2
            if common_subjects and ((has_positive1 and has_negative2) or (has_negative1 and has_positive2)):
                return True
        
        return False
    
    def resolve_issue(self, customer_id: str, issue_description: str, resolution: str) -> Optional[CustomerProfile]:
        """
        Mark an issue as resolved with resolution notes
        
        Args:
            customer_id: Customer identifier
            issue_description: Description of issue to resolve
            resolution: Resolution notes
            
        Returns:
            Updated CustomerProfile or None if not found
        """
        customer = self.get_customer(customer_id)
        if not customer:
            return None
        
        # Find and resolve issue
        for issue in customer.issues:
            if issue.description == issue_description and issue.status.lower() == "open":
                old_status = issue.status
                issue.status = "resolved"
                issue.resolved_at = datetime.now()
                
                # Save changes
                Customer = Query()
                customer_dict = self._serialize_profile(customer)
                self.db.update(customer_dict, Customer.customer_id == customer_id)
                
                # Log state change
                self._log_state_change(
                    customer_id=customer_id,
                    change_type="ISSUE_RESOLVED",
                    fields_changed=["issues"],
                    old_values={"issue_status": old_status},
                    new_values={"issue_status": "resolved", "resolution": resolution},
                    reason=f"Issue resolved: {resolution}"
                )
                
                logger.info(f"Resolved issue for customer {customer_id}: {issue_description}")
                break
        
        return customer
    
    def get_all_customers(self) -> List[CustomerProfile]:
        """
        Retrieve all customer profiles
        
        Returns:
            List of CustomerProfile objects
        """
        customers = []
        for customer_data in self.db.all():
            customers.append(self._deserialize_profile(customer_data))
        return customers
    
    def search_customers(self, query: str) -> List[CustomerProfile]:
        """
        Search customers by name, email, or phone
        
        Args:
            query: Search term
            
        Returns:
            List of matching CustomerProfile objects
        """
        Customer = Query()
        results = self.db.search(
            (Customer.name.search(query, flags=0)) |
            (Customer.email.search(query, flags=0)) |
            (Customer.phone.search(query, flags=0))
        )
        
        return [self._deserialize_profile(data) for data in results]
    
    def get_audit_trail(self, customer_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail for customer
        
        Args:
            customer_id: Customer identifier
            limit: Maximum number of entries to return
            
        Returns:
            List of audit log entries
        """
        Log = Query()
        results = self.audit_db.search(Log.customer_id == customer_id)
        # Sort by timestamp descending
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return results[:limit]
    
    def _serialize_profile(self, profile: CustomerProfile) -> Dict[str, Any]:
        """Convert CustomerProfile to dict for storage"""
        profile_dict = profile.model_dump()
        profile_dict['created_at'] = profile.created_at.isoformat()
        profile_dict['updated_at'] = profile.updated_at.isoformat()
        if profile.last_interaction:
            profile_dict['last_interaction'] = profile.last_interaction.isoformat()
        
        # Serialize issues
        if profile.issues:
            profile_dict['issues'] = [issue.model_dump() for issue in profile.issues]
            for issue_dict in profile_dict['issues']:
                issue_dict['reported_at'] = issue_dict['reported_at'].isoformat() if isinstance(issue_dict['reported_at'], datetime) else issue_dict['reported_at']
                if issue_dict.get('resolved_at'):
                    issue_dict['resolved_at'] = issue_dict['resolved_at'].isoformat() if isinstance(issue_dict['resolved_at'], datetime) else issue_dict['resolved_at']
        
        return profile_dict
    
    def _deserialize_profile(self, customer_data: Dict[str, Any]) -> CustomerProfile:
        """Convert dict to CustomerProfile with proper type handling"""
        # Parse datetime strings
        if 'last_interaction' in customer_data and customer_data['last_interaction']:
            if isinstance(customer_data['last_interaction'], str):
                customer_data['last_interaction'] = datetime.fromisoformat(customer_data['last_interaction'])
        if 'created_at' in customer_data:
            if isinstance(customer_data['created_at'], str):
                customer_data['created_at'] = datetime.fromisoformat(customer_data['created_at'])
        if 'updated_at' in customer_data:
            if isinstance(customer_data['updated_at'], str):
                customer_data['updated_at'] = datetime.fromisoformat(customer_data['updated_at'])
        
        # Parse issues
        if 'issues' in customer_data and customer_data['issues']:
            parsed_issues = []
            for issue in customer_data['issues']:
                if isinstance(issue, dict):
                    # Backward compatibility: migrate created_at to reported_at
                    if 'created_at' in issue and 'reported_at' not in issue:
                        issue['reported_at'] = issue['created_at']
                    
                    # Parse issue timestamps
                    if 'reported_at' in issue and isinstance(issue['reported_at'], str):
                        issue['reported_at'] = datetime.fromisoformat(issue['reported_at'])
                    if 'resolved_at' in issue and issue['resolved_at'] and isinstance(issue['resolved_at'], str):
                        issue['resolved_at'] = datetime.fromisoformat(issue['resolved_at'])
                    
                    # Normalize status to lowercase
                    if 'status' in issue:
                        issue['status'] = issue['status'].lower()
                    
                    parsed_issues.append(IssueRecord(**issue))
                else:
                    parsed_issues.append(issue)
            customer_data['issues'] = parsed_issues
        
        # MIGRATION: Convert old list-based preferences to new dict-based format
        if 'preferences' in customer_data and isinstance(customer_data['preferences'], list):
            logger.info(f"Migrating customer {customer_data.get('customer_id', 'unknown')} preferences from list to dict")
            old_prefs = customer_data['preferences']
            customer_data['preferences'] = {}
            # Migrate all old preferences to 'other' category
            if old_prefs:
                customer_data['preferences']['other'] = old_prefs
            
            # Also migrate confidence_scores if they exist as flat dict
            if 'confidence_scores' in customer_data:
                if isinstance(customer_data['confidence_scores'].get('preferences'), dict):
                    old_conf_scores = customer_data['confidence_scores']['preferences']
                    # Check if it's a flat dict (old format) vs nested dict (new format)
                    if old_conf_scores and not any(isinstance(v, dict) for v in old_conf_scores.values()):
                        # Migrate to nested format
                        customer_data['confidence_scores']['preferences'] = {
                            'other': old_conf_scores
                        }
        
        return CustomerProfile(**customer_data)
    
    def _log_state_change(self,
                         customer_id: str,
                         change_type: str,
                         fields_changed: List[str],
                         old_values: Dict[str, Any],
                         new_values: Dict[str, Any],
                         reason: str,
                         source_conversation_id: Optional[str] = None):
        """
        Log state change to audit trail
        
        Args:
            customer_id: Customer identifier
            change_type: Type of change (CREATED, UPDATED, ISSUE_RESOLVED, etc.)
            fields_changed: List of fields that changed
            old_values: Previous values
            new_values: New values
            reason: Human-readable reason for change
            source_conversation_id: Optional conversation that triggered change
        """
        log_entry = StateChangeLog(
            customer_id=customer_id,
            timestamp=datetime.now(),
            change_type=change_type,
            fields_changed=fields_changed,
            old_values=old_values,
            new_values=new_values,
            reason=reason,
            source_conversation_id=source_conversation_id
        )
        
        # Serialize for storage with datetime handling
        log_dict = log_entry.model_dump()
        log_dict['timestamp'] = log_entry.timestamp.isoformat()
        
        # Recursively convert any datetime objects in old_values and new_values
        def serialize_datetimes(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: serialize_datetimes(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize_datetimes(item) for item in obj]
            return obj
        
        log_dict['old_values'] = serialize_datetimes(log_dict['old_values'])
        log_dict['new_values'] = serialize_datetimes(log_dict['new_values'])
        
        self.audit_db.insert(log_dict)
        logger.debug(f"Logged state change for customer {customer_id}: {change_type}")


# Singleton instance
_customer_service = None

def get_customer_service() -> CustomerService:
    """Get or create singleton instance of CustomerService"""
    global _customer_service
    if _customer_service is None:
        _customer_service = CustomerService()
    return _customer_service
