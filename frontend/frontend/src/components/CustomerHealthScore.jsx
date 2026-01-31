import React from 'react';
import './CustomerHealthScore.css';

const CustomerHealthScore = ({ healthScore, healthStatus }) => {
    const getColor = () => {
        if (healthScore >= 80) return '#10b981'; // Green
        if (healthScore >= 50) return '#f59e0b'; // Orange
        return '#ef4444'; // Red
    };

    const getStatusEmoji = () => {
        if (healthStatus === 'healthy') return '🟢';
        if (healthStatus === 'at_risk') return '🟡';
        if (healthStatus === 'critical') return '🔴';
        return '⚪';
    };

    const getStatusText = () => {
        if (healthStatus === 'healthy') return 'Healthy';
        if (healthStatus === 'at_risk') return 'At Risk';
        if (healthStatus === 'critical') return 'Critical';
        return 'Unknown';
    };

    // Calculate circle progress
    const circumference = 2 * Math.PI * 45;
    const progress = circumference - (healthScore / 100) * circumference;

    return (
        <div className="health-score-widget">
            <h3>Customer Health Score</h3>
            <div className="health-score-content">
                <div className="health-gauge">
                    <svg width="120" height="120" viewBox="0 0 120 120">
                        {/* Background circle */}
                        <circle
                            cx="60"
                            cy="60"
                            r="45"
                            fill="none"
                            stroke="#e5e7eb"
                            strokeWidth="10"
                        />
                        {/* Progress circle */}
                        <circle
                            cx="60"
                            cy="60"
                            r="45"
                            fill="none"
                            stroke={getColor()}
                            strokeWidth="10"
                            strokeDasharray={circumference}
                            strokeDashoffset={progress}
                            strokeLinecap="round"
                            transform="rotate(-90 60 60)"
                            style={{ transition: 'stroke-dashoffset 1s ease' }}
                        />
                    </svg>
                    <div className="health-score-value">
                        <div className="score-number">{Math.round(healthScore)}</div>
                        <div className="score-label">/ 100</div>
                    </div>
                </div>
                <div className="health-status">
                    <span className="status-emoji">{getStatusEmoji()}</span>
                    <span className={`status-text ${healthStatus}`}>{getStatusText()}</span>
                </div>
            </div>
        </div>
    );
};

export default CustomerHealthScore;
