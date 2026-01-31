import React from 'react';
import './NextBestAction.css';

const NextBestAction = ({ nextBestAction }) => {
    if (!nextBestAction) {
        return null;
    }

    const getPriorityColor = (priority) => {
        switch (priority) {
            case 'urgent':
                return '#ef4444';
            case 'high':
                return '#f59e0b';
            case 'medium':
                return '#3b82f6';
            case 'low':
                return '#10b981';
            default:
                return '#6b7280';
        }
    };

    const getPriorityIcon = (priority) => {
        switch (priority) {
            case 'urgent':
                return '🚨';
            case 'high':
                return '⚡';
            case 'medium':
                return '📌';
            case 'low':
                return '💡';
            default:
                return '📋';
        }
    };

    const isRedirection = nextBestAction.category === 'redirection';

    return (
        <div className={`next-best-action-widget ${isRedirection ? 'redirection-mode' : ''}`}>
            <div className="nba-header">
                <h3>{isRedirection ? '🔄 Intelligent Redirection' : '🎯 Next Best Action'}</h3>
                <span
                    className="priority-badge"
                    style={{ backgroundColor: getPriorityColor(nextBestAction.priority) }}
                >
                    {getPriorityIcon(nextBestAction.priority)} {nextBestAction.priority?.toUpperCase()}
                </span>
            </div>

            <div className="nba-content">
                <div className="nba-action">
                    <h4>{nextBestAction.action}</h4>
                </div>

                <div className="nba-reasoning">
                    <span className="reasoning-label">Analysis:</span>
                    <p>{nextBestAction.reasoning}</p>
                </div>

                <div className="nba-footer">
                    <div className="confidence-indicator">
                        <span className="confidence-label">Confidence:</span>
                        <div className="confidence-bar">
                            <div
                                className="confidence-fill"
                                style={{ width: `${nextBestAction.confidence * 100}%` }}
                            ></div>
                        </div>
                        <span className="confidence-value">{Math.round(nextBestAction.confidence * 100)}%</span>
                    </div>

                    <button className={`take-action-btn ${isRedirection ? 'redirect-btn' : ''}`}>
                        {isRedirection ? 'Initiate Transfer →' : 'Take Action →'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default NextBestAction;
