<script>
  import axios from 'axios';
  
  let history = [];
  let loading = true;
  
  async function loadHistory() {
    loading = true;
    try {
      const response = await axios.get('/console/consent/history?limit=50');
      history = response.data.records || [];
    } catch (e) {
      console.error('Failed to load consent history:', e);
    } finally {
      loading = false;
    }
  }
  
  const decisionColors = {
    approved: '#4ade80',
    denied: '#f87171',
    deferred: '#fbbf24'
  };
  
  loadHistory();
</script>

<div class="consent-manager">
  <h2>✅ Consent History</h2>
  
  {#if loading}
    <div class="loading">Loading...</div>
  {:else if history.length === 0}
    <div class="empty">No consent records yet</div>
  {:else}
    <div class="records">
      {#each history as record}
        <div class="record-card" style="border-left: 4px solid {decisionColors[record.decision]}">
          <div class="record-header">
            <span class="decision" style="color: {decisionColors[record.decision]}">
              {record.decision.toUpperCase()}
            </span>
            <span class="timestamp">{new Date(record.timestamp).toLocaleString()}</span>
          </div>
          <div class="record-body">
            <div class="plan-id">Plan: {record.plan_id}</div>
            <div class="reason">{record.reason}</div>
            <div class="user">By: {record.user}</div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .consent-manager {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.75rem;
    padding: 1.5rem;
  }
  
  h2 {
    margin-bottom: 1.5rem;
    color: #fff;
  }
  
  .loading, .empty {
    text-align: center;
    color: #888;
    padding: 2rem;
  }
  
  .record-card {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.5rem;
    padding: 1rem;
    margin-bottom: 1rem;
  }
  
  .record-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.75rem;
  }
  
  .decision {
    font-weight: 600;
    font-size: 0.9rem;
  }
  
  .timestamp {
    color: #888;
    font-size: 0.8rem;
  }
  
  .plan-id {
    color: #667eea;
    font-size: 0.85rem;
    margin-bottom: 0.5rem;
  }
  
  .reason {
    color: #fff;
    margin-bottom: 0.5rem;
  }
  
  .user {
    color: #888;
    font-size: 0.8rem;
  }
</style>
