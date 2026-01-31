/**
 * Context Intelligence Dashboard
 * Shows semantic search, context reliability tracking, and conversation timeline
 */

import React, { useState, useEffect } from 'react';
import { customerAPI } from '../services/api';
import './ContextIntelligence.css';

const ContextIntelligence = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [customerContext, setCustomerContext] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [loading, setLoading] = useState(false);
  const [customers, setCustomers] = useState([]);

  useEffect(() => {
    loadCustomers();
    loadTimeline();
  }, []);

  const loadCustomers = async () => {
    try {
      const data = await customerAPI.getCustomers();
      setCustomers(data);
    } catch (error) {
      console.error('Failed to load customers:', error);
    }
  };

  const loadTimeline = async () => {
    try {
      const response = await fetch('http://localhost:8000/context/timeline?limit=10');
      const data = await response.json();
      setTimeline(data.timeline || []);
    } catch (error) {
      console.error('Failed to load timeline:', error);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    
    setLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/context/search?query=${encodeURIComponent(searchQuery)}&limit=5`);
      const data = await response.json();
      setSearchResults(data.results || []);
    } catch (error) {
      console.error('Search failed:', error);
      setSearchResults([]);
    } finally {
      setLoading(false);
    }
  };

  const loadCustomerContext = async (customerId) => {
    setSelectedCustomer(customerId);
    setLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/context/customer/${customerId}`);
      const data = await response.json();
      setCustomerContext(data);
    } catch (error) {
      console.error('Failed to load customer context:', error);
      setCustomerContext(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="context-intelligence">
      <div className="ci-header">
        <h1>🧠 Context Intelligence</h1>
        <p className="ci-subtitle">Semantic Search & Reliability Tracking</p>
      </div>

      {/* Semantic Search Section */}
      <div className="ci-section search-section">
        <h2>🔍 Semantic Search</h2>
        <div className="search-box">
          <input
            type="text"
            placeholder="Search conversations by meaning (e.g., 'delivery issues', 'prefers email')"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            className="search-input"
          />
          <button onClick={handleSearch} className="search-button" disabled={loading}>
            {loading ? '⏳' : '🔍'} Search
          </button>
        </div>

        {searchResults.length > 0 && (
          <div className="search-results">
            <h3>Search Results ({searchResults.length})</h3>
            {searchResults.map((result, index) => (
              <div key={index} className="search-result-card">
                <div className="result-header">
                  <span className="result-customer" onClick={() => loadCustomerContext(result.customer_id)}>
                    👤 {result.customer_name || 'Unknown'}
                  </span>
                  <span className="result-similarity">
                    {(result.similarity * 100).toFixed(1)}% match
                  </span>
                </div>
                <div className="result-preview">{result.text_preview}</div>
                <div className="result-meta">
                  <span>📅 {new Date(result.timestamp).toLocaleString()}</span>
                  <span>🆔 {result.conversation_id.substring(0, 8)}...</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Customer Context Section */}
      <div className="ci-section context-section">
        <h2>📊 Customer Context Analysis</h2>
        
        <div className="customer-selector">
          <select 
            onChange={(e) => e.target.value && loadCustomerContext(e.target.value)}
            value={selectedCustomer || ''}
            className="customer-dropdown"
          >
            <option value="">Select a customer to view context...</option>
            {customers.map(customer => (
              <option key={customer.customer_id} value={customer.customer_id}>
                {customer.name || customer.customer_id.substring(0, 8)} - {customer.email}
              </option>
            ))}
          </select>
        </div>

        {customerContext && (
          <div className="context-details">
            <div className="context-cards">
              {/* Profile Card */}
              <div className="context-card profile-card">
                <h3>👤 Customer Profile</h3>
                <div className="profile-info">
                  <p><strong>Name:</strong> {customerContext.profile.name || 'N/A'}</p>
                  <p><strong>Email:</strong> {customerContext.profile.email || 'N/A'}</p>
                  <p><strong>Phone:</strong> {customerContext.profile.phone || 'N/A'}</p>
                  <p><strong>Total Interactions:</strong> {customerContext.profile.total_interactions}</p>
                  <p><strong>Last Interaction:</strong> {customerContext.profile.last_interaction ? new Date(customerContext.profile.last_interaction).toLocaleString() : 'N/A'}</p>
                </div>
              </div>

              {/* Context Summary Card */}
              <div className="context-card summary-card">
                <h3>📝 Context Summary</h3>
                <div className="summary-stats">
                  <div className="stat-item">
                    <span className="stat-value">{customerContext.context.preferences_count}</span>
                    <span className="stat-label">Preferences</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-value">{customerContext.context.open_issues_count}</span>
                    <span className="stat-label">Open Issues</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-value">{customerContext.context.commitments_count}</span>
                    <span className="stat-label">Commitments</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-value">{customerContext.conversations_count}</span>
                    <span className="stat-label">Conversations</span>
                  </div>
                </div>
              </div>

              {/* Reliability Tracking Card */}
              <div className="context-card reliability-card">
                <h3>⭐ Context Reliability</h3>
                <div className="reliability-info">
                  <p><strong>Total Updates:</strong> {customerContext.reliability.total_updates}</p>
                  <p><strong>Tracked Preferences:</strong> {Object.keys(customerContext.reliability.preference_scores || {}).length}</p>
                </div>
                {customerContext.reliability.most_reliable_preferences?.length > 0 && (
                  <div className="reliable-prefs">
                    <h4>Most Reliable Preferences:</h4>
                    <ul>
                      {customerContext.reliability.most_reliable_preferences.slice(0, 5).map(([pref, score], index) => (
                        <li key={index}>
                          <span className="pref-text">{pref}</span>
                          <span className="pref-score">✓ {score}x confirmed</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>

            {/* Preferences List */}
            {customerContext.context.preferences && Object.keys(customerContext.context.preferences).length > 0 && (
              <div className="context-list">
                <h3>💡 All Preferences</h3>
                {Object.entries(customerContext.context.preferences).map(([category, values]) => (
                  <div key={category} className="preference-category-group">
                    <h4>{category.replace(/_/g, ' ').toUpperCase()}</h4>
                    <div className="preference-chips">
                      {values.map((pref, index) => {
                        const score = customerContext.reliability.preference_scores?.[pref.toLowerCase()] || 1;
                        return (
                          <span key={index} className={`pref-chip score-${Math.min(score, 5)}`}>
                            {pref} {score > 1 && `(${score}x)`}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Issues List */}
            {customerContext.context.issues?.length > 0 && (
              <div className="context-list">
                <h3>⚠️ Issues</h3>
                <div className="issues-list">
                  {customerContext.context.issues.map((issue, index) => (
                    <div key={index} className={`issue-item ${issue.status}`}>
                      <span className="issue-status">{issue.status === 'open' ? '🔴' : '✅'}</span>
                      <div className="issue-content">
                        <p className="issue-description">{issue.description}</p>
                        <p className="issue-date">Reported: {new Date(issue.reported_at).toLocaleDateString()}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Timeline Section */}
      <div className="ci-section timeline-section">
        <h2>📅 Recent Activity Timeline</h2>
        {timeline.length > 0 ? (
          <div className="timeline-list">
            {timeline.map((entry, index) => (
              <div key={index} className="timeline-entry">
                <div className="timeline-marker"></div>
                <div className="timeline-content">
                  <div className="timeline-header">
                    <span className="timeline-customer" onClick={() => loadCustomerContext(entry.customer_id)}>
                      👤 {entry.customer_name}
                    </span>
                    <span className="timeline-channel">{entry.channel === 'call' ? '📞' : '💬'} {entry.channel}</span>
                  </div>
                  <p className="timeline-preview">{entry.text_preview}</p>
                  <span className="timeline-time">📅 {new Date(entry.timestamp).toLocaleString()}</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="no-data">No recent activity</p>
        )}
      </div>
    </div>
  );
};

export default ContextIntelligence;
