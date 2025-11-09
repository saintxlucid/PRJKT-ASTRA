<script>
  let query = '';
  let filterSource = '';
  let memories = [];
  
  function searchMemories() {
    // Placeholder - will integrate with /console/memory/browse
    console.log('Search:', query, filterSource);
  }
</script>

<div class="memory-browser">
  <h2>🧠 Memory Browser</h2>
  
  <div class="search-bar">
    <input bind:value={query} type="text" placeholder="Semantic search query..." />
    <input bind:value={filterSource} type="text" placeholder="Filter by source..." />
    <button on:click={searchMemories}>🔍 Search</button>
  </div>
  
  <div class="pending">
    <p>⏳ Integration with ChromaMemoryGatewayBGE pending</p>
    <p class="note">This will enable semantic search with provenance tracking</p>
  </div>
</div>

<style>
  .memory-browser {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.75rem;
    padding: 1.5rem;
  }
  
  h2 {
    margin-bottom: 1.5rem;
    color: #fff;
  }
  
  .search-bar {
    display: grid;
    grid-template-columns: 1fr 1fr auto;
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
