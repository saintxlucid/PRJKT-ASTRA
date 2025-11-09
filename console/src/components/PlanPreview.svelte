<script>
  import axios from 'axios';
  
  let planId = 'plan_' + Date.now();
  let title = 'Example Plan';
  let description = 'Modify system configuration';
  let actions = [
    {
      type: 'read',
      description: 'Read current config',
      resources: { file: '/etc/config.yaml' },
      dependencies: []
    }
  ];
  
  let plan = null;
  let loading = false;
  let error = null;
  
  const actionTypes = ['read', 'write', 'execute', 'network', 'memory', 'query'];
  const riskColors = {
    low: '#4ade80',
    medium: '#fbbf24',
    high: '#f87171',
    critical: '#dc2626'
  };
  
  function addAction() {
    actions = [...actions, {
      type: 'read',
      description: '',
      resources: {},
      dependencies: []
    }];
  }
  
  function removeAction(index) {
    actions = actions.filter((_, i) => i !== index);
  }
  
  async function previewPlan() {
    loading = true;
    error = null;
    
    try {
      const response = await axios.post('/console/plan/preview', {
        plan_id: planId,
        title,
        description,
        actions
      });
      
      plan = response.data;
    } catch (e) {
      error = e.response?.data?.detail || e.message;
    } finally {
      loading = false;
    }
  }
</script>

<div class="plan-preview">
  <div class="editor">
    <h2>📋 Create Plan</h2>
    
    <div class="form-group">
      <label>Plan ID</label>
      <input bind:value={planId} type="text" placeholder="plan_001" />
    </div>
    
    <div class="form-group">
      <label>Title</label>
      <input bind:value={title} type="text" placeholder="Plan title" />
    </div>
    
    <div class="form-group">
      <label>Description</label>
      <textarea bind:value={description} placeholder="What does this plan do?" />
    </div>
    
    <h3>Actions</h3>
    {#each actions as action, i}
      <div class="action-card">
        <div class="action-header">
          <span class="action-num">Action {i + 1}</span>
          <button class="remove-btn" on:click={() => removeAction(i)}>🗑️</button>
        </div>
        
        <div class="form-group">
          <label>Type</label>
          <select bind:value={action.type}>
            {#each actionTypes as type}
              <option value={type}>{type}</option>
            {/each}
          </select>
        </div>
        
        <div class="form-group">
          <label>Description</label>
          <input bind:value={action.description} type="text" placeholder="What does this action do?" />
        </div>
      </div>
    {/each}
    
    <button class="add-btn" on:click={addAction}>+ Add Action</button>
    <button class="preview-btn" on:click={previewPlan} disabled={loading}>
      {loading ? '⏳ Generating...' : '🔍 Preview Plan'}
    </button>
  </div>
  
  <div class="visualization">
    <h2>📊 Plan Visualization</h2>
    
    {#if error}
      <div class="error">❌ {error}</div>
    {:else if plan}
      <div class="plan-summary">
        <div class="summary-card">
          <div class="summary-label">Risk Level</div>
          <div class="summary-value" style="color: {riskColors[plan.max_risk_level]}">
            {plan.max_risk_level.toUpperCase()}
          </div>
        </div>
        
        <div class="summary-card">
          <div class="summary-label">Duration</div>
          <div class="summary-value">{plan.total_duration_ms}ms</div>
        </div>
        
        <div class="summary-card">
          <div class="summary-label">Reversible</div>
          <div class="summary-value">{plan.reversible ? '✅' : '❌'}</div>
        </div>
        
        <div class="summary-card">
          <div class="summary-label">Consent Required</div>
          <div class="summary-value">{plan.requires_consent ? '✅ Yes' : '❌ No'}</div>
        </div>
      </div>
      
      <div class="action-list">
        {#each plan.nodes as node}
          <div class="action-node" style="border-left: 4px solid {riskColors[node.risk_level]}">
            <div class="node-header">
              <span class="node-type">{node.type}</span>
              <span class="node-risk" style="background: {riskColors[node.risk_level]}">{node.risk_level}</span>
            </div>
            <div class="node-description">{node.description}</div>
            <div class="node-meta">
              <span>⏱️ {node.estimated_duration_ms}ms</span>
              <span>{node.reversible ? '🔄 Reversible' : '⚠️ Irreversible'}</span>
              {#if node.requires_consent}
                <span class="consent-badge">✅ Consent Required</span>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {:else}
      <div class="empty-state">
        <p>👈 Create a plan to see visualization</p>
      </div>
    {/if}
  </div>
</div>

<style>
  .plan-preview {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
    height: calc(100vh - 250px);
  }
  
  .editor, .visualization {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.75rem;
    padding: 1.5rem;
    overflow-y: auto;
  }
  
  h2 {
    margin-bottom: 1.5rem;
    color: #fff;
    font-size: 1.3rem;
  }
  
  h3 {
    margin: 1.5rem 0 1rem;
    color: #aaa;
    font-size: 1rem;
  }
  
  .form-group {
    margin-bottom: 1rem;
  }
  
  label {
    display: block;
    margin-bottom: 0.5rem;
    color: #aaa;
    font-size: 0.85rem;
  }
  
  input, textarea, select {
    width: 100%;
    padding: 0.75rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.5rem;
    color: #fff;
    font-size: 0.9rem;
  }
  
  textarea {
    min-height: 80px;
    resize: vertical;
  }
  
  .action-card {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.5rem;
    padding: 1rem;
    margin-bottom: 1rem;
  }
  
  .action-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }
  
  .action-num {
    color: #667eea;
    font-weight: 600;
  }
  
  .remove-btn {
    background: rgba(248, 113, 113, 0.2);
    border: 1px solid rgba(248, 113, 113, 0.3);
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    cursor: pointer;
  }
  
  .add-btn, .preview-btn {
    width: 100%;
    padding: 0.75rem;
    margin-top: 1rem;
    border-radius: 0.5rem;
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .add-btn {
    background: rgba(255, 255, 255, 0.05);
    border: 1px dashed rgba(255, 255, 255, 0.2);
    color: #aaa;
  }
  
  .add-btn:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #fff;
  }
  
  .preview-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    color: #fff;
    font-weight: 600;
  }
  
  .preview-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  .error {
    padding: 1rem;
    background: rgba(248, 113, 113, 0.1);
    border: 1px solid rgba(248, 113, 113, 0.3);
    border-radius: 0.5rem;
    color: #f87171;
  }
  
  .plan-summary {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
    margin-bottom: 2rem;
  }
  
  .summary-card {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.5rem;
    padding: 1rem;
  }
  
  .summary-label {
    color: #888;
    font-size: 0.8rem;
    margin-bottom: 0.5rem;
  }
  
  .summary-value {
    color: #fff;
    font-size: 1.2rem;
    font-weight: 600;
  }
  
  .action-node {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.5rem;
    padding: 1rem;
    margin-bottom: 1rem;
  }
  
  .node-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }
  
  .node-type {
    color: #667eea;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.8rem;
  }
  
  .node-risk {
    padding: 0.25rem 0.75rem;
    border-radius: 1rem;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
  }
  
  .node-description {
    color: #fff;
    margin-bottom: 0.75rem;
  }
  
  .node-meta {
    display: flex;
    gap: 1rem;
    color: #888;
    font-size: 0.8rem;
  }
  
  .consent-badge {
    color: #4ade80;
  }
  
  .empty-state {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #666;
    font-size: 1.1rem;
  }
</style>
