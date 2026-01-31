import React from 'react';
import './CommitmentTracker.css';

const CommitmentTracker = ({ commitmentStatus }) => {
    if (!commitmentStatus || commitmentStatus.total === 0) {
        return null;
    }

    const { total, completed, pending, overdue, fulfillment_rate, details } = commitmentStatus;

    const getProgressColor = () => {
        if (fulfillment_rate >= 80) return '#10b981';
        if (fulfillment_rate >= 50) return '#f59e0b';
        return '#ef4444';
    };

    return (
        <div className="commitment-tracker-widget">
            <h3>📋 Commitment Tracker</h3>

            <div className="commitment-stats">
                <div className="stat-card completed">
                    <div className="stat-icon">✅</div>
                    <div className="stat-content">
                        <div className="stat-value">{completed}</div>
                        <div className="stat-label">Completed</div>
                    </div>
                </div>

                <div className="stat-card pending">
                    <div className="stat-icon">⏳</div>
                    <div className="stat-content">
                        <div className="stat-value">{pending}</div>
                        <div className="stat-label">Pending</div>
                    </div>
                </div>

                <div className="stat-card overdue">
                    <div className="stat-icon">🚨</div>
                    <div className="stat-content">
                        <div className="stat-value">{overdue}</div>
                        <div className="stat-label">Overdue</div>
                    </div>
                </div>
            </div>

            <div className="fulfillment-section">
                <div className="fulfillment-header">
                    <span className="fulfillment-label">Fulfillment Rate</span>
                    <span className="fulfillment-value" style={{ color: getProgressColor() }}>
                        {fulfillment_rate}%
                    </span>
                </div>
                <div className="fulfillment-bar">
                    <div
                        className="fulfillment-progress"
                        style={{
                            width: `${fulfillment_rate}%`,
                            backgroundColor: getProgressColor()
                        }}
                    ></div>
                </div>
            </div>

            {details && details.length > 0 && (
                <div className="commitment-details">
                    <h4>Recent Commitments</h4>
                    <div className="commitments-list">
                        {details.map((commitment, idx) => (
                            <div key={idx} className={`commitment-item ${commitment.status}`}>
                                <div className="commitment-status-icon">
                                    {commitment.status === 'completed' && '✅'}
                                    {commitment.status === 'pending' && '⏳'}
                                    {commitment.status === 'overdue' && '🚨'}
                                </div>
                                <div className="commitment-text">
                                    {commitment.description || commitment.commitment || 'Commitment'}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default CommitmentTracker;
