<script>
  import PlanPreview from './components/PlanPreview.svelte';
  import ConsentManager from './components/ConsentManager.svelte';
  import MemoryBrowser from './components/MemoryBrowser.svelte';
  import EventViewer from './components/EventViewer.svelte';

  let activeTab = 'plan';
  
  const tabs = [
    { id: 'plan', label: 'Plan Preview', icon: '📋' },
    { id: 'consent', label: 'Consent', icon: '✅' },
    { id: 'memory', label: 'Memory', icon: '🧠' },
    { id: 'events', label: 'Events', icon: '📊' }
  ];
</script>

<main>
  <header>
    <h1>🌌 ASTRA Operator Console</h1>
    <p class="subtitle">Local-First Intelligence Control</p>
  </header>

  <nav>
    {#each tabs as tab}
      <button
        class:active={activeTab === tab.id}
        on:click={() => activeTab = tab.id}
      >
        <span class="icon">{tab.icon}</span>
        <span class="label">{tab.label}</span>
      </button>
    {/each}
  </nav>

  <div class="content">
    {#if activeTab === 'plan'}
      <PlanPreview />
    {:else if activeTab === 'consent'}
      <ConsentManager />
    {:else if activeTab === 'memory'}
      <MemoryBrowser />
    {:else if activeTab === 'events'}
      <EventViewer />
    {/if}
  </div>
</main>

<style>
  main {
    min-height: 100vh;
    background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
  }

  header {
    padding: 2rem;
    background: rgba(255, 255, 255, 0.03);
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }

  h1 {
    font-size: 2rem;
    font-weight: 600;
    color: #fff;
    margin-bottom: 0.5rem;
  }

  .subtitle {
    color: #888;
    font-size: 0.9rem;
  }

  nav {
    display: flex;
    gap: 0.5rem;
    padding: 1rem 2rem;
    background: rgba(255, 255, 255, 0.02);
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }

  button {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1.5rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.5rem;
    color: #aaa;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 0.9rem;
  }

  button:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #fff;
  }

  button.active {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-color: transparent;
    color: #fff;
  }

  .icon {
    font-size: 1.2rem;
  }

  .content {
    padding: 2rem;
    max-width: 1400px;
    margin: 0 auto;
  }
</style>
