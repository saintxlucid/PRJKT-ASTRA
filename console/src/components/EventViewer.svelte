<script>
  let eventType = '';
  let events = [];
  
  function loadEvents() {
    // Placeholder - will integrate with /console/events
    console.log('Load events:', eventType);
  }
</script>

<div class="event-viewer">
  <h2>📊 Event Log Viewer</h2>
  
  <div class="filters">
    <input bind:value={eventType} type="text" placeholder="Filter by event type..." />
    <button on:click={loadEvents}>🔄 Refresh</button>
  </div>
  
  <div class="pending">
    <p>⏳ Integration with EventStore pending</p>
    <p class="note">This will enable event replay and "Why did ASTRA do X?" queries</p>
  </div>
</div>

<style>
  .event-viewer {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.75rem;
    padding: 1.5rem;
  }
  
  h2 {
    margin-bottom: 1.5rem;
    color: #fff;
  }
  
  .filters {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 1rem;
    margin-bottom: 2rem;
  }
  
  input {
    padding: 0.75rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.5rem;
    color: #fff;
  }
  
  button {
    padding: 0.75rem 1.5rem;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    border-radius: 0.5rem;
    color: #fff;
    cursor: pointer;
  }
  
  .pending {
    text-align: center;
    padding: 3rem;
    color: #888;
  }
  
  .note {
    margin-top: 0.5rem;
    font-size: 0.9rem;
  }
</style>
