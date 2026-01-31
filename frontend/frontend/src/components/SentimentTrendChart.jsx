import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';
import './SentimentTrendChart.css';

const SentimentTrendChart = ({ sentimentHistory }) => {
    // Transform sentiment history for charting
    const chartData = sentimentHistory.map((item, idx) => ({
        index: idx + 1,
        sentiment: item.sentiment || 0,
        timestamp: item.timestamp ? new Date(item.timestamp).toLocaleDateString() : `Day ${idx + 1}`,
        label: item.sentiment >= 0 ? 'Positive' : 'Negative'
    }));

    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload;
            return (
                <div className="sentiment-tooltip">
                    <p className="tooltip-date">{data.timestamp}</p>
                    <p className={`tooltip-sentiment ${data.sentiment >= 0 ? 'positive' : 'negative'}`}>
                        Sentiment: {(data.sentiment * 100).toFixed(0)}%
                    </p>
                    <p className="tooltip-label">{data.label}</p>
                </div>
            );
        }
        return null;
    };

    if (!sentimentHistory || sentimentHistory.length === 0) {
        return (
            <div className="sentiment-chart-widget">
                <h3>📈 Sentiment Trend</h3>
                <div className="no-data-chart">
                    <p>No sentiment data available yet</p>
                </div>
            </div>
        );
    }

    return (
        <div className="sentiment-chart-widget">
            <h3>📈 Sentiment Trend</h3>
            <div className="chart-container">
                <ResponsiveContainer width="100%" height={250}>
                    <AreaChart data={chartData}>
                        <defs>
                            <linearGradient id="sentimentGradient" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                                <stop offset="95%" stopColor="#10b981" stopOpacity={0.1} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis
                            dataKey="timestamp"
                            stroke="#6b7280"
                            style={{ fontSize: '12px' }}
                        />
                        <YAxis
                            domain={[-1, 1]}
                            ticks={[-1, -0.5, 0, 0.5, 1]}
                            stroke="#6b7280"
                            style={{ fontSize: '12px' }}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Area
                            type="monotone"
                            dataKey="sentiment"
                            stroke="#10b981"
                            strokeWidth={3}
                            fill="url(#sentimentGradient)"
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
            <div className="sentiment-legend">
                <div className="legend-item">
                    <span className="legend-dot positive"></span>
                    <span>Positive</span>
                </div>
                <div className="legend-item">
                    <span className="legend-dot negative"></span>
                    <span>Negative</span>
                </div>
            </div>
        </div>
    );
};

export default SentimentTrendChart;
