<script lang="ts">
	let { count, limit }: { count: number; limit: number } = $props();
	const over = $derived(count > limit);
	const pct  = $derived(Math.min(100, Math.round((count / limit) * 100)));
</script>

<span class="counter" class:over>
	{count}/{limit}
</span>

<style>
	.counter { font-size: 0.75rem; color: var(--text-muted); font-variant-numeric: tabular-nums; }
	.counter.over { color: var(--skipped); font-weight: 700; }
</style>
