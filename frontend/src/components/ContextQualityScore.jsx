/**
 * Context Quality Score Widget
 * Shows circular progress for context completeness
 */

import React from 'react';
import './ContextQualityScore.css';

const ContextQualityScore = ({ contextQuality }) => {
  if (!contextQuality) {
    return null;
  }

  const { score, max_score, percentage, quality_level, breakdown } = contextQuality;

  const getQualityColor = (level) => {
    switch (level) {
      case 'excellent': return '#4caf50';
      case 'good': return '#8bc34a';
      case 'fair': return '#ffc107';
      case 'needs_improvement': return '#ff9800';
      default: return '#ccc';
    }
  };

  const getQualityLabel = (level) => {
    switch (level) {
      case 'excellent': return '🌟 Excellent';
      case 'good': return '✓ Good';
      case 'fair': return '→ Fair';
      case 'needs_improvement': return '⚠ Needs Improvement';
      default: return 'Unknown';
    }
  };

  const color = getQualityColor(quality_level);
  const circumference = 2 * Math.PI * 45; // radius = 45
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className="context-quality-widget">
      <h3>Context Completeness</h3>
      
      {/* Circular Progress */}
      <div className="circular-progress">
        <svg width="120" height="120">
          {/* Background circle */}
          <circle
            cx="60"
            cy="60"
            r="45"
            fill="none"
            stroke="rgba(255,255,255,0.2)"
            strokeWidth="10"
          />
          {/* Progress circle */}
          <circle
            cx="60"
            cy="60"
            r="45"
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            transform="rotate(-90 60 60)"
            style={{ transition: 'stroke-dashoffset 0.5s ease' }}
          />
        </svg>
        <div className="progress-text">
          <div className="progress-percentage">{percentage}%</div>
          <div className="progress-label">{getQualityLabel(quality_level)}</div>
        </div>
      </div>

      {/* Breakdown */}
      <div className="quality-breakdown">
        <div className="breakdown-item">
          <div className="breakdown-icon">📝</div>
          <div className="breakdown-info">
            <div className="breakdown-label">Preferences</div>
            <div className="breakdown-value">
              {breakdown.preferences.count} items • {breakdown.preferences.score}/{breakdown.preferences.max} pts
            </div>
          </div>
          <div className="breakdown-bar">
            <div 
              className="breakdown-progress"
              style={{
                width: `${(breakdown.preferences.score / breakdown.preferences.max) * 100}%`,
                backgroundColor: color
              }}
            />
          </div>
        </div>

        <div className="breakdown-item">
          <div className="breakdown-icon">⚠️</div>
          <div className="breakdown-info">
            <div className="breakdown-label">Issues</div>
            <div className="breakdown-value">
              {breakdown.issues.count} items • {breakdown.issues.score}/{breakdown.issues.max} pts
            </div>
          </div>
          <div className="breakdown-bar">
            <div 
              className="breakdown-progress"
              style={{
                width: `${(breakdown.issues.score / breakdown.issues.max) * 100}%`,
                backgroundColor: color
              }}
            />
          </div>
        </div>

        <div className="breakdown-item">
          <div className="breakdown-icon">✅</div>
          <div className="breakdown-info">
            <div className="breakdown-label">Commitments</div>
            <div className="breakdown-value">
              {breakdown.commitments.count} items • {breakdown.commitments.score}/{breakdown.commitments.max} pts
            </div>
          </div>
          <div className="breakdown-bar">
            <div 
              className="breakdown-progress"
              style={{
                width: `${(breakdown.commitments.score / breakdown.commitments.max) * 100}%`,
                backgroundColor: color
              }}
            />
          </div>
        </div>

        <div className="breakdown-item">
          <div className="breakdown-icon">📞</div>
          <div className="breakdown-info">
            <div className="breakdown-label">Contact Info</div>
            <div className="breakdown-value">
              {breakdown.contact_info.has_name ? '✓' : '✗'} Name • 
              {breakdown.contact_info.has_email ? '✓' : '✗'} Email • 
              {breakdown.contact_info.has_phone ? '✓' : '✗'} Phone
            </div>
          </div>
          <div className="breakdown-bar">
            <div 
              className="breakdown-progress"
              style={{
                width: `${(breakdown.contact_info.score / breakdown.contact_info.max) * 100}%`,
                backgroundColor: color
              }}
            />
          </div>
        </div>
      </div>

      <div className="quality-score-total">
        <strong>Total Score:</strong> {score}/{max_score} points
      </div>
    </div>
  );
};

export default ContextQualityScore;
