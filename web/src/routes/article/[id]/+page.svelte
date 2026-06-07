<script lang="ts">
	import type { PageData } from './$types';
	import type { Platform, PostStatusValue, PlatformPost } from '$lib/types';
	import CopyButton from '$lib/components/CopyButton.svelte';
	import CharCounter from '$lib/components/CharCounter.svelte';
	import StatusBadge from '$lib/components/StatusBadge.svelte';

	let { data }: { data: PageData } = $props();
	const article = data.article;

	type Tab = 'threads' | 'instagram' | 'twitter';
	let activeTab = $state<Tab>('threads');

	// Local status state — updated optimistically on click.
	let status = $state({ ...article?.status });

	async function markPosted(platform: Platform) {
		const current: PostStatusValue = status[platform] ?? 'pending';
		const next: PostStatusValue = current === 'posted' ? 'pending' : 'posted';
		status = { ...status, [platform]: next };
		await fetch('/api/status', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ article_id: article?.id, platform, status: next }),
		});
	}

	const LIMITS: Record<Tab, number> = { threads: 490, instagram: 2000, twitter: 260 };

	function mainPostText(tab: Tab): string {
		if (!article) return '';
		if (tab === 'instagram') return article.variants.instagram.caption;
		const posts = tab === 'threads'
			? article.variants.threads.posts
			: article.variants.twitter.posts;
		return (posts as PlatformPost[]).find((p) => p.index === 1)?.text ?? '';
	}

	function sourceText(tab: Tab): string {
		if (!article) return '';
		if (tab === 'instagram') return '';
		const posts = tab === 'threads'
			? article.variants.threads.posts
			: article.variants.twitter.posts;
		return (posts as PlatformPost[]).find((p) => p.index === 2)?.text ?? '';
	}

	function charCount(tab: Tab): number {
		const t = mainPostText(tab);
		return t.length;
	}
</script>

<svelte:head>
	<title>{article?.title_short ?? 'Artikel'} — KiMedia</title>
</svelte:head>

{#if !article}
	<div class="empty">Artikel tidak ditemukan.</div>
{:else}
<div class="layout">
	<!-- Breadcrumb -->
	<nav class="breadcrumb">
		<a href="/dashboard">← Dashboard</a>
		<span>{article.date} {article.time}</span>
		<span>{article.category.emoji} {article.category.label}</span>
	</nav>

	<div class="content">
		<!-- Left: thumbnail + meta -->
		<aside class="sidebar">
			{#if article.thumbnail_r2_url}
				<img src={article.thumbnail_r2_url} alt={article.title_short} class="thumb" />
				<a href={article.thumbnail_r2_url} download class="btn-outline">⬇ Download Thumbnail</a>
			{:else}
				<div class="thumb-placeholder">{article.category.emoji}</div>
			{/if}

			<div class="meta">
				<p class="title-short">{article.title_short}</p>
				<p class="title-id">{article.title_id}</p>
				{#if article.source_url}
					<a href={article.source_url} target="_blank" rel="noopener" class="source">
						↗ {article.source_name || article.source_domain}
					</a>
				{/if}
			</div>

			<!-- Status per platform -->
			<div class="status-panel">
				{#each (['threads','instagram','twitter'] as Platform[]) as platform}
					<button
						class="status-row"
						onclick={() => markPosted(platform)}
						data-status={status[platform]}
					>
						<StatusBadge {platform} status={status[platform] ?? 'pending'} />
						<span class="platform-label">{platform}</span>
						<span class="toggle-hint">
							{status[platform] === 'posted' ? 'Unmark' : 'Mark posted'}
						</span>
					</button>
				{/each}
			</div>
		</aside>

		<!-- Right: platform tabs -->
		<section class="tabs-section">
			<div class="tabs">
				{#each (['threads','instagram','twitter'] as Tab[]) as tab}
					<button
						class="tab"
						class:active={activeTab === tab}
						onclick={() => (activeTab = tab)}
					>
						{tab === 'threads' ? '🧵 Threads' : tab === 'instagram' ? '📸 Instagram' : '🐦 Twitter'}
						<StatusBadge platform={tab} status={status[tab] ?? 'pending'} />
					</button>
				{/each}
			</div>

			<div class="tab-content">
				<div class="post-block">
					<div class="post-header">
						<span class="post-label">Post 1</span>
						<CharCounter count={charCount(activeTab)} limit={LIMITS[activeTab]} />
						<CopyButton text={mainPostText(activeTab)} />
					</div>
					<pre class="post-text">{mainPostText(activeTab)}</pre>
				</div>

				{#if sourceText(activeTab)}
					<div class="post-block source">
						<div class="post-header">
							<span class="post-label">Post 2 — Source</span>
							<CopyButton text={sourceText(activeTab)} />
						</div>
						<pre class="post-text">{sourceText(activeTab)}</pre>
					</div>
				{/if}

				{#if activeTab === 'instagram' && article.variants.instagram.hashtags?.length}
					<div class="hashtags">
						{#each article.variants.instagram.hashtags as tag}
							<span class="tag">{tag}</span>
						{/each}
					</div>
				{/if}
			</div>
		</section>
	</div>
</div>
{/if}

<style>
	.layout { max-width: 1100px; margin: 0 auto; padding: 1.5rem; }
	.breadcrumb { display: flex; gap: 1rem; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1.5rem; }
	.breadcrumb a { color: var(--accent); }
	.content { display: grid; grid-template-columns: 280px 1fr; gap: 2rem; }
	@media (max-width: 700px) { .content { grid-template-columns: 1fr; } }

	.sidebar { display: flex; flex-direction: column; gap: 1rem; }
	.thumb { width: 100%; border-radius: var(--radius); aspect-ratio: 4/5; object-fit: cover; }
	.thumb-placeholder {
		width: 100%; aspect-ratio: 4/5; background: #111;
		display: flex; align-items: center; justify-content: center;
		font-size: 4rem; border-radius: var(--radius);
	}
	.btn-outline {
		display: block; text-align: center;
		border: 1px solid var(--border); border-radius: var(--radius);
		padding: 0.5rem; font-size: 0.875rem; color: var(--text-muted);
	}
	.btn-outline:hover { border-color: var(--accent); color: var(--accent); text-decoration: none; }
	.meta { display: flex; flex-direction: column; gap: 0.4rem; }
	.title-short { font-size: 1rem; font-weight: 700; }
	.title-id { font-size: 0.8rem; color: var(--text-muted); }
	.source { font-size: 0.8rem; }

	.status-panel { display: flex; flex-direction: column; gap: 0.4rem; }
	.status-row {
		display: flex; align-items: center; gap: 0.6rem;
		background: var(--bg-card); border: 1px solid var(--border);
		border-radius: 6px; padding: 0.5rem 0.75rem; width: 100%;
		text-align: left; transition: border-color 0.15s;
	}
	.status-row:hover { border-color: var(--accent); }
	.status-row[data-status="posted"] { border-color: rgba(0,255,100,0.4); }
	.platform-label { font-size: 0.85rem; flex: 1; text-transform: capitalize; }
	.toggle-hint { font-size: 0.7rem; color: var(--text-muted); }

	.tabs-section { display: flex; flex-direction: column; gap: 1rem; }
	.tabs { display: flex; gap: 0.5rem; border-bottom: 1px solid var(--border); padding-bottom: 0.75rem; }
	.tab {
		display: flex; align-items: center; gap: 0.4rem;
		background: none; border: 1px solid transparent;
		border-radius: var(--radius); color: var(--text-muted);
		font-size: 0.875rem; padding: 0.4rem 0.8rem;
		transition: all 0.15s;
	}
	.tab:hover { color: var(--text); }
	.tab.active { border-color: var(--accent); color: var(--accent); }

	.post-block {
		background: var(--bg-card); border: 1px solid var(--border);
		border-radius: var(--radius); overflow: hidden;
	}
	.post-block.source { opacity: 0.7; }
	.post-header {
		display: flex; align-items: center; gap: 0.75rem;
		padding: 0.6rem 0.9rem; border-bottom: 1px solid var(--border);
		background: var(--bg);
	}
	.post-label { font-size: 0.75rem; font-weight: 600; color: var(--text-muted); flex: 1; }
	.post-text {
		font-family: inherit; font-size: 0.9rem; line-height: 1.6;
		white-space: pre-wrap; padding: 1rem;
		max-height: 320px; overflow-y: auto;
	}
	.hashtags { display: flex; gap: 0.4rem; flex-wrap: wrap; }
	.tag {
		background: rgba(0,255,100,0.08); color: var(--accent);
		border: 1px solid rgba(0,255,100,0.2);
		border-radius: 999px; font-size: 0.75rem; padding: 2px 8px;
	}
	.empty { text-align: center; padding: 4rem; color: var(--text-muted); }
</style>
