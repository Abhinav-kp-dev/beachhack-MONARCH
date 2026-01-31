/**
 * Agent Dashboard Component
 * Shows customer context, conversation history, and action recommendations
 */

import React, { useState, useEffect } from 'react';
import { customerAPI } from '../services/api';
import ContextQualityScore from './ContextQualityScore';
import CustomerHealthScore from './CustomerHealthScore';
import SentimentTrendChart from './SentimentTrendChart';
import NextBestAction from './NextBestAction';
import RiskAlerts from './RiskAlerts';
import CommitmentTracker from './CommitmentTracker';
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
          {/* Top Row: Intelligence Grid */}
          <div className="premium-intelligence-grid">
            <CustomerHealthScore
              healthScore={context.health_score || 50}
              healthStatus={context.health_status || 'unknown'}
            />
            <NextBestAction nextBestAction={context.next_best_action} />
          </div>

          {/* Alert Bar */}
          <RiskAlerts riskAlerts={context.risk_alerts} />

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

          {/* Customer Profile - Top Section */}
          <div className="context-section profile-section">
            <h2>Customer Profile</h2>
            {context.customer_profile ? (
              <>
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
                            {Array.isArray(values) && values.map((value, idx) => (
                              <li key={idx}>{value}</li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {context.customer_profile.issues && context.customer_profile.issues.length > 0 && (
                  <div className="profile-lists issues">
                    <h4>Issues ({context.customer_profile.issues.length}):</h4>
                    <ul>
                      {context.customer_profile.issues.map((issue, idx) => (
                        <li key={idx}>
                          <strong>{issue?.description || 'No description'}</strong>
                          <span className={`issue-status ${issue?.status}`}> [{issue?.status || 'Active'}]</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {context.customer_profile.commitments && context.customer_profile.commitments.length > 0 && (
                  <div className="profile-lists commitments">
                    <h4>Commitments ({context.customer_profile.commitments.length}):</h4>
                    <ul>
                      {context.customer_profile.commitments.map((commitment, idx) => (
                        <li key={idx}>{commitment}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            ) : (
              <div className="profile-info">
                <p><strong>ID:</strong> {context.customer_id || 'Unknown'}</p>
                <p><strong>Name:</strong> {context.name || 'N/A'}</p>
                <p><strong>Email:</strong> {context.email || 'N/A'}</p>
                <p><strong>Phone:</strong> {context.phone || 'N/A'}</p>

                {/* Unified Profile Attributes */}
                {context.preferences && Object.keys(context.preferences).length > 0 && (
                  <div className="profile-attributes">
                    <strong>📋 Unified Profile Attributes:</strong>
                    <div className="attributes-grid">
                      {Object.entries(context.preferences).map(([key, value]) => (
                        <div key={key} className="attribute-item">
                          <span className="attr-label">{key.replace(/_/g, ' ')}</span>
                          <span className="attr-value">{String(value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Integrated Summary */}
                <div className="profile-summary-box">
                  <strong>✨ AI Summary:</strong>
                  <p className="profile-summary-text">
                    {context.unified_summary || 'No summary available yet.'}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Suggested Follow-ups */}
          <div className="context-section questions-section">
            <h2>❓ Suggested Follow-ups</h2>
            <div className="questions-list">
              {context.suggested_questions && context.suggested_questions.length > 0 ? (
                context.suggested_questions.slice(0, 5).map((question, idx) => (
                  <div key={idx} className="question-chip">
                    "{question}"
                  </div>
                ))
              ) : (
                <div className="question-chip">"Is there anything else I can help you with today?"</div>
              )}
            </div>
          </div>

          {/* PREMIUM: Sentiment Trend Chart */}
          <SentimentTrendChart sentimentHistory={context.sentiment_history} />

          {/* PREMIUM: Commitment Tracker */}
          <CommitmentTracker commitmentStatus={context.commitment_status} />

          {/* AI Recommendations & Actions - Enhanced */}
          {context.recommendations && context.recommendations.length > 0 && (
            <div className="context-section recommendations-section">
              <h2>🤖 Recommended Actions & Insights</h2>
              <div className="recommendations-grid">
                {context.recommendations.map((rec, idx) => (
                  <div key={idx} className={`recommendation-card confidence-${rec.confidence} category-${rec.category ? rec.category.toLowerCase() : 'general'}`}>
                    <div className="recommendation-header">
                      <span className="recommendation-category">{rec.category}</span>
                      <span className={`confidence-badge ${rec.confidence >= 0.8 ? 'high' : rec.confidence >= 0.5 ? 'medium' : 'low'}`}>
                        {Math.round(rec.confidence * 100)}% Confidence
                      </span>
                    </div>
                    <div className="recommendation-body">
                      <p className="recommendation-text">{rec.recommendation}</p>
                      <p className="recommendation-reason">💡 {rec.reason}</p>
                    </div>
                    {/* Explicit Action Button for relevant categories */}
                    {(rec.category && (rec.category.toLowerCase() === 'support' || rec.category.toLowerCase() === 'sales' || rec.category.toLowerCase() === 'upsell')) && (
                      <button className="action-btn-small" onClick={() => alert(`Initiating action: ${rec.recommendation}`)}>
                        Take Action →
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Customer Timeline */}
          {context.recent_evidence && context.recent_evidence.length > 0 && (
            <Timeline conversations={context.recent_evidence} />
          )}

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
