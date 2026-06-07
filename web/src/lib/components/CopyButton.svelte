<script lang="ts">
	let { text }: { text: string } = $props();
	let copied = $state(false);

	async function copy() {
		await navigator.clipboard.writeText(text);
		copied = true;
		setTimeout(() => (copied = false), 2000);
	}
</script>

<button onclick={copy} class:copied>
	{copied ? '✓ Copied' : 'Copy'}
</button>

<style>
	button {
		background: var(--bg);
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text-muted);
		font-size: 0.8rem;
		padding: 0.35rem 0.8rem;
		transition: all 0.15s;
	}
	button:hover { border-color: var(--accent); color: var(--accent); }
	button.copied { border-color: var(--accent); color: var(--accent); }
</style>
