/**
 * Customer Timeline Component
 * Shows conversation history across channels with visual continuity
 */

import React from 'react';
import './Timeline.css';

const Timeline = ({ conversations }) => {
  if (!conversations || conversations.length === 0) {
    return (
      <div className="timeline-container">
        <p className="no-timeline">No conversation history available</p>
      </div>
    );
  }

  const getChannelIcon = (channel) => {
    switch (channel.toLowerCase()) {
      case 'chat': return '💬';
      case 'email': return '📧';
      case 'call': return '📞';
      default: return '💭';
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) {
      return `${diffMins} min${diffMins !== 1 ? 's' : ''} ago`;
    } else if (diffHours < 24) {
      return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    } else if (diffDays < 7) {
      return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  // Sort by timestamp descending
  const sortedConversations = [...conversations].sort(
    (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
  );

  return (
    <div className="timeline-container">
      <h3>📅 Customer Journey Timeline</h3>
      <p className="timeline-subtitle">Cross-channel conversation history</p>

      <div className="timeline">
        {sortedConversations.map((conv, index) => (
          <div key={conv.conversation_id || index} className="timeline-item">
            {/* Connector Line */}
            {index < sortedConversations.length - 1 && (
              <div className="timeline-connector" />
            )}

            {/* Timeline Dot */}
            <div className={`timeline-dot ${conv.channel}`}>
              <span className="dot-icon">{getChannelIcon(conv.channel)}</span>
            </div>

            {/* Content Card */}
            <div className="timeline-content">
              <div className="timeline-header">
                <span className={`channel-badge ${conv.channel}`}>
                  {getChannelIcon(conv.channel)} {conv.channel.toUpperCase()}
                </span>
                <span className="timeline-time">{formatTimestamp(conv.timestamp)}</span>
              </div>

              <div className="timeline-body">
                <p className="timeline-text">
                  {conv.raw_text || conv.summary || 'No text available'}
                </p>
              </div>

              {/* Show channel transition */}
              {index < sortedConversations.length - 1 &&
               sortedConversations[index + 1].channel !== conv.channel && (
                <div className="channel-transition">
                  <span className="transition-arrow">↓</span>
                  <span className="transition-text">
                    Channel switched: {sortedConversations[index + 1].channel}
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Summary Statistics */}
      <div className="timeline-stats">
        <div className="stat-item">
          <div className="stat-icon">💬</div>
          <div className="stat-info">
            <div className="stat-value">{conversations.length}</div>
            <div className="stat-label">Total Interactions</div>
          </div>
        </div>

        <div className="stat-item">
          <div className="stat-icon">📱</div>
          <div className="stat-info">
            <div className="stat-value">
              {new Set(conversations.map(c => c.channel)).size}
            </div>
            <div className="stat-label">Channels Used</div>
          </div>
        </div>

        <div className="stat-item success">
          <div className="stat-icon">✅</div>
          <div className="stat-info">
            <div className="stat-value">
              {conversations.length > 1 ? 'Yes' : 'N/A'}
            </div>
            <div className="stat-label">Context Preserved</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Timeline;
