/**
 * Agent Dashboard Component
 * Shows customer context, conversation history, and action recommendations
 */

import React, { useState, useEffect } from 'react';
import { customerAPI } from '../services/api';
import ContextQualityScore from './ContextQualityScore';
import Timeline from './Timeline';
import './AgentDashboard.css';

const AgentDashboard = () => {
  const [customerId, setCustomerId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [context, setContext] = useState(null);
  const [customers, setCustomers] = useState([]);

  useEffect(() => {
    loadCustomers();
    
    // Listen for viewCustomer event from CustomerInteraction
    const handleViewCustomer = (event) => {
      const { customerId } = event.detail;
      setCustomerId(customerId);
      // Reload customers list to ensure the new customer appears
      loadCustomers().then(() => {
        // Small delay to ensure the customer is loaded
        setTimeout(() => {
          handleLoadContext();
        }, 500);
      });
    };
    
    window.addEventListener('viewCustomer', handleViewCustomer);
    
    // Auto-refresh customer list every 10 seconds
    const refreshInterval = setInterval(() => {
      loadCustomers();
    }, 10000);
    
    return () => {
      window.removeEventListener('viewCustomer', handleViewCustomer);
      clearInterval(refreshInterval);
    };
  }, []);

  const loadCustomers = async () => {
    try {
      const data = await customerAPI.listCustomers();
      setCustomers(data);
      return data;
    } catch (err) {
      console.error('Failed to load customers:', err);
      return [];
    }
  };

  const handleLoadContext = async () => {
    if (!customerId.trim()) {
      setError('Please enter a customer ID');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await customerAPI.getContext(customerId);
      setContext(data);
      // Refresh customer list to show updated info
      loadCustomers();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load customer context');
      setContext(null);
    } finally {
      setLoading(false);
    }
  };

  const handleTriggerAction = async (actionType, details = {}) => {
    try {
      await customerAPI.triggerAction(actionType, customerId, details);
      alert(`${actionType} created successfully!`);
      // Reload context to show new action
      handleLoadContext();
    } catch (err) {
      alert(`Failed to create ${actionType}: ${err.response?.data?.detail || err.message}`);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="agent-dashboard">
      <h1>Agent Dashboard</h1>

      {/* Customer Selection */}
      <div className="customer-search">
        <div className="input-group">
          <input
            type="text"
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            placeholder="Enter Customer ID"
            onKeyPress={(e) => e.key === 'Enter' && handleLoadContext()}
          />
          <button onClick={handleLoadContext} disabled={loading}>
            {loading ? 'Loading...' : 'Load Context'}
          </button>
        </div>

        {customers.length > 0 && (
          <div className="customer-list">
            <h3>Recent Customers:</h3>
            <div className="customer-chips">
              {customers.slice(0, 10).map((customer) => (
                <button
                  key={customer.customer_id}
                  className="customer-chip"
                  onClick={() => {
                    setCustomerId(customer.customer_id);
                    setTimeout(() => handleLoadContext(), 100);
                  }}
                >
                  {customer.name || customer.customer_id}
                  <span className={`sentiment ${customer.sentiment_trend}`}>
                    {customer.sentiment_trend}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {error && <div className="error-message">{error}</div>}

      {/* Context Display */}
      {context && (
        <div className="context-container">
          {/* Top Row: Key Metrics */}
          <div className="metrics-row">
            {/* Context Quality Score */}
            {context.context_quality && (
              <ContextQualityScore contextQuality={context.context_quality} />
            )}

            {/* Time Saved Widget */}
            {context.time_saved && (
              <div className="time-saved-widget">
                <h3>⏱️ Time Efficiency</h3>
                <div className="time-saved-content">
                  <div className="time-saved-main">
                    <div className="time-value">{context.time_saved.total_minutes}</div>
                    <div className="time-label">Minutes Saved</div>
                  </div>
                  <div className="time-saved-detail">
                    <p>✅ Customer doesn't repeat information</p>
                    <p>✅ Agent has full context immediately</p>
                    <p>✅ Faster resolution time</p>
                    <div className="time-breakdown">
                      <strong>Breakdown:</strong>
                      <ul>
                        <li>{context.time_saved.breakdown.preferences.count} preferences saved ({context.time_saved.breakdown.preferences.seconds_saved}s)</li>
                        <li>{context.time_saved.breakdown.issues.count} issues tracked ({context.time_saved.breakdown.issues.seconds_saved}s)</li>
                        <li>{context.time_saved.breakdown.commitments.count} commitments recorded ({context.time_saved.breakdown.commitments.seconds_saved}s)</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* AI Recommendations */}
          {context.recommendations && context.recommendations.length > 0 && (
            <div className="context-section recommendations-section">
              <h2>🤖 AI-Powered Recommendations</h2>
              <div className="recommendations-grid">
                {context.recommendations.map((rec, idx) => (
                  <div key={idx} className={`recommendation-card confidence-${rec.confidence}`}>
                    <div className="recommendation-header">
                      <span className="recommendation-category">{rec.category}</span>
                      <span className={`confidence-badge ${rec.confidence}`}>{rec.confidence}</span>
                    </div>
                    <div className="recommendation-body">
                      <p className="recommendation-text">{rec.recommendation}</p>
                      <p className="recommendation-reason">💡 {rec.reason}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Customer Timeline */}
          {context.recent_evidence && context.recent_evidence.length > 0 && (
            <Timeline conversations={context.recent_evidence} />
          )}

          {/* Customer Profile */}
          <div className="context-section profile-section">
            <h2>Customer Profile</h2>
            <div className="profile-info">
              <p><strong>ID:</strong> {context.customer_profile.customer_id}</p>
              <p><strong>Name:</strong> {context.customer_profile.name || 'N/A'}</p>
              <p><strong>Email:</strong> {context.customer_profile.email || 'N/A'}</p>
              <p><strong>Phone:</strong> {context.customer_profile.phone || 'N/A'}</p>
              {context.customer_profile.last_interaction && (
                <p><strong>Last Interaction:</strong> {formatDate(context.customer_profile.last_interaction)}</p>
              )}
            </div>

            {context.customer_profile.preferences && Object.keys(context.customer_profile.preferences).length > 0 && (
              <div className="profile-lists">
                <h4>Preferences ({
                  Object.values(context.customer_profile.preferences).reduce((sum, arr) => sum + arr.length, 0)
                }):</h4>
                <div className="preferences-by-category">
                  {Object.entries(context.customer_profile.preferences).map(([category, values]) => (
                    <div key={category} className="preference-category">
                      <strong>{category.replace(/_/g, ' ').toUpperCase()}:</strong>
                      <ul>
                        {values.map((value, idx) => (
                          <li key={idx}>{value}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {context.customer_profile.issues.length > 0 && (
              <div className="profile-lists issues">
                <h4>Issues ({context.customer_profile.issues.length}):</h4>
                <ul>
                  {context.customer_profile.issues.map((issue, idx) => (
                    <li key={idx}>
                      <strong>{issue.description}</strong>
                      <span className={`issue-status ${issue.status}`}> [{issue.status}]</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {context.customer_profile.commitments.length > 0 && (
              <div className="profile-lists commitments">
                <h4>Commitments ({context.customer_profile.commitments.length}):</h4>
                <ul>
                  {context.customer_profile.commitments.map((commitment, idx) => (
                    <li key={idx}>{commitment}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Statistics Summary */}
          {context.statistics && (
            <div className="context-section stats-section">
              <h2>📊 Context Statistics</h2>
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-value">{context.statistics.total_preferences}</div>
                  <div className="stat-label">Preferences</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{context.statistics.open_issues}</div>
                  <div className="stat-label">Open Issues</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{context.statistics.total_commitments}</div>
                  <div className="stat-label">Commitments</div>
                </div>
                <div className="stat-card">
                  <div className="stat-value">{context.statistics.evidence_count}</div>
                  <div className="stat-label">Conversations</div>
                </div>
              </div>
            </div>
          )}

          {/* Agent Summary - REMOVED as it doesn't exist in new API */}
          {/* <div className="context-section summary-section">
            <h2>Agent Summary</h2>
            <p className="agent-summary">{context.agent_summary}</p>
          </div> */}

          {/* Recent Conversations - REMOVED, replaced by Timeline */}
          {/* <div className="context-section conversations-section">
            <h2>Recent Conversations ({context.recent_conversations.length})</h2>
            <div className="conversations-list">
              {context.recent_conversations.map((conv) => (
                <div key={conv.conversation_id} className="conversation-card">
                  <div className="conv-header">
                    <span className={`channel-badge ${conv.channel}`}>{conv.channel}</span>
                    <span className="conv-time">{formatDate(conv.timestamp)}</span>
                  </div>
                  <p className="conv-summary">{conv.summary}</p>
                  {conv.extracted_context && (
                    <div className="conv-context">
                      <span className="context-tag">Intent: {conv.extracted_context.intent}</span>
                      <span className={`context-tag urgency-${conv.extracted_context.urgency}`}>
                        Urgency: {conv.extracted_context.urgency}
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div> */}

          {/* Pending Actions - Keeping this as-is */}
          {/* <div className="context-section actions-section">
            <h2>Pending Actions ({context.pending_actions.length})</h2>
            {context.pending_actions.length > 0 ? (
              <div className="actions-list">
                {context.pending_actions.map((action) => (
                  <div key={action.action_id} className={`action-card ${action.type}`}>
                    <div className="action-header">
                      <span className="action-type">{action.type}</span>
                      <span className={`priority-badge ${action.priority}`}>{action.priority}</span>
                    </div>
                    <p className="action-details">{JSON.stringify(action.details)}</p>
                    <small>{formatDate(action.created_at)}</small>
                  </div>
                ))}
              </div>
            ) : (
              <p className="no-data">No pending actions</p>
            )}
          </div> */}

          {/* Action Triggers */}
          <div className="context-section trigger-section">
            <h2>Create Action</h2>
            <div className="action-buttons">
              <button
                className="action-btn ticket"
                onClick={() => handleTriggerAction('ticket', {
                  issue: 'Support request from agent dashboard',
                  priority: 'medium'
                })}
              >
                Create Ticket
              </button>
              <button
                className="action-btn lead"
                onClick={() => handleTriggerAction('lead', {
                  opportunity: 'Sales opportunity from conversation',
                  value: null
                })}
              >
                Create Lead
              </button>
              <button
                className="action-btn reminder"
                onClick={() => handleTriggerAction('reminder', {
                  task: 'Follow-up with customer',
                  due_date: null
                })}
              >
                Create Reminder
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentDashboard;
