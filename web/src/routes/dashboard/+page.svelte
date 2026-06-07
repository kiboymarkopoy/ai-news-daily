<script lang="ts">
	import type { PageData } from './$types';
	import ArticleCard from '$lib/components/ArticleCard.svelte';

	let { data }: { data: PageData } = $props();
	const { articles, filter } = data;

	const CATS = [
		{ seq: 1, label: '🧠 Model' },
		{ seq: 2, label: '💰 Industry' },
		{ seq: 3, label: '⚖️ Regulasi' },
		{ seq: 4, label: '🤖 Robotics' },
		{ seq: 5, label: '🎬 Creative' },
	];
</script>

<svelte:head><title>Dashboard — KiMedia</title></svelte:head>

<div class="layout">
	<header>
		<div class="brand">KiMedia<span class="dot">■</span></div>
		<nav>
			<a href="/dashboard">Dashboard</a>
			<a href="/dashboard?seq=1">🧠</a>
			<a href="/dashboard?seq=2">💰</a>
			<a href="/dashboard?seq=3">⚖️</a>
			<a href="/dashboard?seq=4">🤖</a>
			<a href="/dashboard?seq=5">🎬</a>
			<a href="/logout" class="logout">Logout</a>
		</nav>
	</header>

	<main>
		<div class="filters">
			<a href="/dashboard" class="chip" class:active={!filter.seq}>Semua</a>
			{#each CATS as cat}
				<a href="/dashboard?seq={cat.seq}" class="chip" class:active={filter.seq === cat.seq}>
					{cat.label}
				</a>
			{/each}
		</div>

		{#if articles.length === 0}
			<div class="empty">Belum ada artikel. Kiboy belum publish ke dashboard.</div>
		{:else}
			<div class="grid">
				{#each articles as article (article.id)}
					<ArticleCard {article} />
				{/each}
			</div>
		{/if}
	</main>
</div>

<style>
	.layout { display: flex; flex-direction: column; min-height: 100vh; }
	header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.75rem 1.5rem;
		background: var(--bg-card);
		border-bottom: 1px solid var(--border);
		position: sticky; top: 0; z-index: 10;
	}
	.brand { font-size: 1.25rem; font-weight: 900; }
	.dot { color: var(--accent); }
	nav { display: flex; gap: 1rem; align-items: center; font-size: 0.9rem; }
	.logout { color: var(--text-muted); }
	main { padding: 1.5rem; flex: 1; }
	.filters { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
	.chip {
		padding: 0.35rem 0.75rem;
		border-radius: 999px;
		border: 1px solid var(--border);
		font-size: 0.8rem;
		color: var(--text-muted);
		transition: all 0.15s;
	}
	.chip:hover, .chip.active { border-color: var(--accent); color: var(--accent); text-decoration: none; }
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
		gap: 1rem;
	}
	.empty { color: var(--text-muted); padding: 3rem 0; text-align: center; }
</style>
