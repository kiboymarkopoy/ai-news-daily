<script lang="ts">
	import type { ArticleListItem } from '$lib/types';
	import StatusBadge from './StatusBadge.svelte';

	let { article }: { article: ArticleListItem } = $props();

	const posted = article.status
		? Object.values(article.status).filter((s) => s === 'posted').length
		: 0;
	const total = 3;
</script>

<a href="/article/{article.id}" class="card">
	<div class="thumb-wrap">
		{#if article.thumbnail_r2_url}
			<img src={article.thumbnail_r2_url} alt={article.title_short} loading="lazy" />
		{:else}
			<div class="thumb-placeholder">
				<span>{article.category.emoji}</span>
			</div>
		{/if}
		<span class="category-badge">{article.category.emoji} {article.category.label}</span>
	</div>

	<div class="info">
		<p class="title">{article.title_short}</p>
		<div class="meta">
			<span class="date">{article.date} {article.time}</span>
			<span class="status-count" class:all-posted={posted === total}>
				{posted}/{total} posted
			</span>
		</div>
		{#if article.status}
			<div class="badges">
				<StatusBadge platform="threads"   status={article.status.threads} />
				<StatusBadge platform="instagram" status={article.status.instagram} />
				<StatusBadge platform="twitter"   status={article.status.twitter} />
			</div>
		{/if}
	</div>
</a>

<style>
	.card {
		display: flex;
		flex-direction: column;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
		transition: border-color 0.15s;
		text-decoration: none;
		color: inherit;
	}
	.card:hover { border-color: var(--accent); }
	.thumb-wrap { position: relative; aspect-ratio: 4/5; overflow: hidden; background: #111; }
	.thumb-wrap img { width: 100%; height: 100%; object-fit: cover; }
	.thumb-placeholder {
		width: 100%; height: 100%;
		display: flex; align-items: center; justify-content: center;
		font-size: 2.5rem; background: #111;
	}
	.category-badge {
		position: absolute; bottom: 0.5rem; left: 0.5rem;
		background: rgba(0,0,0,0.7);
		color: var(--text-muted);
		font-size: 0.7rem;
		padding: 2px 6px;
		border-radius: 999px;
	}
	.info { padding: 0.75rem; display: flex; flex-direction: column; gap: 0.5rem; }
	.title { font-size: 0.875rem; font-weight: 600; line-height: 1.4; }
	.meta { display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--text-muted); }
	.status-count.all-posted { color: var(--accent); }
	.badges { display: flex; gap: 0.3rem; flex-wrap: wrap; }
</style>
