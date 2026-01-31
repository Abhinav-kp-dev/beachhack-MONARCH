import React from 'react';
import './RiskAlerts.css';

const RiskAlerts = ({ riskAlerts }) => {
    if (!riskAlerts || riskAlerts.length === 0) {
        return null;
    }

    const getSeverityIcon = (severity) => {
        switch (severity) {
            case 'high':
                return '🚨';
            case 'medium':
                return '⚠️';
            case 'low':
                return 'ℹ️';
            default:
                return '📢';
        }
    };

    const getSeverityClass = (severity) => {
        return `alert-${severity}`;
    };

    return (
        <div className="risk-alerts-widget">
            <h3>⚡ Risk Alerts</h3>
            <div className="alerts-container">
                {riskAlerts.map((alert, idx) => (
                    <div key={idx} className={`risk-alert ${getSeverityClass(alert.severity)}`}>
                        <div className="alert-icon">
                            {getSeverityIcon(alert.severity)}
                        </div>
                        <div className="alert-content">
                            <div className="alert-header">
                                <span className="alert-type">{alert.type?.replace(/_/g, ' ').toUpperCase()}</span>
                                <span className={`severity-badge ${alert.severity}`}>
                                    {alert.severity?.toUpperCase()}
                                </span>
                            </div>
                            <p className="alert-message">{alert.message}</p>
                            <div className="alert-action">
                                <span className="action-label">Recommended:</span>
                                <span className="action-text">{alert.action}</span>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default RiskAlerts;
