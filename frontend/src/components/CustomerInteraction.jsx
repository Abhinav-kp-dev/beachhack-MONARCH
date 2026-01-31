/**
 * Customer Interaction Component
 * For creating new conversations via chat, email, or call
 */

import React, { useState } from 'react';
import { customerAPI } from '../services/api';
import './CustomerInteraction.css';

const CustomerInteraction = () => {
  const [channel, setChannel] = useState('chat');
  const [customerId, setCustomerId] = useState('');
  const [customerName, setCustomerName] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [text, setText] = useState('');
  const [audioFile, setAudioFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSubmitConversation = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await customerAPI.submitConversation({
        customer_id: customerId || null,
        customer_name: customerName || null,
        customer_email: customerEmail || null,
        customer_phone: customerPhone || null,
        channel: channel,
        text: text,
      });

      setResult(data);
      // Reset form
      setText('');
      
      // Show success message with customer ID
      if (data.is_new_customer) {
        alert(`✅ New customer created!\nCustomer ID: ${data.customer_id}\n\nYou can now view this customer in the Agent Dashboard.`);
      } else {
        alert('Conversation submitted successfully!');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit conversation');
    } finally {
      setLoading(false);
    }
  };

  const handleUploadAudio = async (e) => {
    e.preventDefault();
    if (!audioFile) {
      setError('Please select an audio file');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await customerAPI.transcribeAudio(
        audioFile, 
        customerId || null,
        customerName || null,
        customerEmail || null,
        customerPhone || null
      );
      setResult(data);
      
      // Show success message with customer ID
      if (data.is_new_customer) {
        alert(`✅ New customer created!\nCustomer ID: ${data.customer_id}\n\nYou can now view this customer in the Agent Dashboard.`);
      } else {
        alert('Audio transcribed successfully!');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to transcribe audio');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="customer-interaction">
      <h1>Customer Interaction</h1>

      <div className="channel-selector">
        <button
          className={channel === 'chat' ? 'active' : ''}
          onClick={() => setChannel('chat')}
        >
          Chat
        </button>
        <button
          className={channel === 'email' ? 'active' : ''}
          onClick={() => setChannel('email')}
        >
          Email
        </button>
        <button
          className={channel === 'call' ? 'active' : ''}
          onClick={() => setChannel('call')}
        >
          Call
        </button>
      </div>

      {/* Customer Info Form */}
      <div className="customer-info">
        <h3>Customer Information (Optional)</h3>
        <div className="form-row">
          <input
            type="text"
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            placeholder="Customer ID (leave empty for new customer)"
          />
          <input
            type="text"
            value={customerName}
            onChange={(e) => setCustomerName(e.target.value)}
            placeholder="Customer Name"
          />
        </div>
        <div className="form-row">
          <input
            type="email"
            value={customerEmail}
            onChange={(e) => setCustomerEmail(e.target.value)}
            placeholder="Email"
          />
          <input
            type="tel"
            value={customerPhone}
            onChange={(e) => setCustomerPhone(e.target.value)}
            placeholder="Phone"
          />
        </div>
      </div>

      {/* Text Input (Chat/Email) */}
      {(channel === 'chat' || channel === 'email') && (
        <form onSubmit={handleSubmitConversation} className="interaction-form">
          <h3>{channel === 'chat' ? 'Chat Message' : 'Email Content'}</h3>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={`Enter ${channel} message...`}
            rows="10"
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Submitting...' : 'Submit Conversation'}
          </button>
        </form>
      )}

      {/* Audio Upload (Call) */}
      {channel === 'call' && (
        <form onSubmit={handleUploadAudio} className="interaction-form">
          <h3>Upload Call Recording</h3>
          <input
            type="file"
            accept="audio/*"
            onChange={(e) => setAudioFile(e.target.files[0])}
            required
          />
          <p className="help-text">Supported formats: MP3, WAV, M4A, etc.</p>
          <button type="submit" disabled={loading}>
            {loading ? 'Transcribing...' : 'Upload & Transcribe'}
          </button>
        </form>
      )}

      {/* Error Display */}
      {error && <div className="error-message">{error}</div>}

      {/* Result Display */}
      {result && (
        <div className="result-section">
          <h3>✅ Success!</h3>
          <div className="result-card">
            {result.is_new_customer && (
              <div className="new-customer-alert">
                🎉 <strong>New Customer Created!</strong>
              </div>
            )}
            
            <div className="result-row highlight">
              <strong>Customer ID:</strong>
              <div className="id-display">
                <code className="customer-id">{result.customer_id}</code>
                <button 
                  className="copy-btn"
                  onClick={() => {
                    navigator.clipboard.writeText(result.customer_id);
                    alert('Customer ID copied to clipboard!');
                  }}
                  title="Copy to clipboard"
                >
                  📋 Copy
                </button>
                <a 
                  href="#"
                  className="view-btn"
                  onClick={(e) => {
                    e.preventDefault();
                    // Trigger a custom event that AgentDashboard can listen to
                    window.dispatchEvent(new CustomEvent('viewCustomer', { 
                      detail: { customerId: result.customer_id } 
                    }));
                    alert('Switch to Agent Dashboard to view this customer');
                  }}
                >
                  👁️ View in Dashboard
                </a>
              </div>
            </div>
            
            {result.conversation_id && (
              <div className="result-row">
                <strong>Conversation ID:</strong>
                <code className="conversation-id">{result.conversation_id}</code>
              </div>
            )}
            
            <div className="result-row">
              <strong>Status:</strong> 
              <span className="status-badge">{result.status}</span>
            </div>
            
            {result.customer && (
              <div className="customer-summary">
                <h4>📊 Customer Summary</h4>
                <div className="summary-stats">
                  <div className="stat">
                    <span className="stat-label">Name:</span>
                    <span className="stat-value">{result.customer.name || 'N/A'}</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Email:</span>
                    <span className="stat-value">{result.customer.email || 'N/A'}</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Phone:</span>
                    <span className="stat-value">{result.customer.phone || 'N/A'}</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Preferences:</span>
                    <span className="stat-value">{result.customer.preferences_count}</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Open Issues:</span>
                    <span className="stat-value">{result.customer.issues_count}</span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Total Interactions:</span>
                    <span className="stat-value">{result.customer.total_interactions}</span>
                  </div>
                </div>
              </div>
            )}
            
            {result.transcript && (
              <div className="transcript">
                <strong>📝 Transcript:</strong>
                <p className="transcript-text">{result.transcript}</p>
              </div>
            )}
            
            {result.extracted_context && (
              <div className="extracted-context">
                <strong>🧠 Extracted Context:</strong>
                <div className="context-grid">
                  {result.extracted_context.preferences?.length > 0 && (
                    <div className="context-item">
                      <strong>💡 Preferences ({result.extracted_context.preferences.length}):</strong>
                      <ul>
                        {result.extracted_context.preferences.map((pref, i) => (
                          <li key={i}>
                            {typeof pref === 'string' 
                              ? pref 
                              : `${pref.category}: ${pref.value} (${(pref.confidence * 100).toFixed(0)}% confident)`
                            }
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {result.extracted_context.issues?.length > 0 && (
                    <div className="context-item">
                      <strong>⚠️ Issues ({result.extracted_context.issues.length}):</strong>
                      <ul>
                        {result.extracted_context.issues.map((issue, i) => (
                          <li key={i}>
                            {typeof issue === 'string' 
                              ? issue 
                              : `${issue.value} (${(issue.confidence * 100).toFixed(0)}% confident)`
                            }
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {result.extracted_context.commitments?.length > 0 && (
                    <div className="context-item">
                      <strong>✅ Commitments ({result.extracted_context.commitments.length}):</strong>
                      <ul>
                        {result.extracted_context.commitments.map((commit, i) => (
                          <li key={i}>
                            {typeof commit === 'string' 
                              ? commit 
                              : `${commit.value} (${(commit.confidence * 100).toFixed(0)}% confident)`
                            }
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {result.recommended_action && (
              <div className="recommended-action">
                <strong>🎯 Recommended Action:</strong>
                <div className="action-details">
                  <p><strong>Type:</strong> {result.recommended_action.action_type}</p>
                  <p><strong>Priority:</strong> {result.recommended_action.priority}</p>
                  <p><strong>Reason:</strong> {result.recommended_action.reason}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CustomerInteraction;
