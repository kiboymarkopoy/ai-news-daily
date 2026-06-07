<script lang="ts">
	import type { Platform, PostStatusValue } from '$lib/types';

	let { platform, status }: { platform: Platform; status: PostStatusValue } = $props();

	const labels: Record<Platform, string> = {
		threads: 'TH', instagram: 'IG', twitter: 'TW'
	};
</script>

<span class="badge" data-status={status}>
	{labels[platform]}
</span>

<style>
	.badge {
		display: inline-block;
		font-size: 0.65rem;
		font-weight: 700;
		padding: 2px 5px;
		border-radius: 3px;
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}
	.badge[data-status="pending"]  { background: rgba(136,136,136,0.15); color: var(--pending); border: 1px solid rgba(136,136,136,0.3); }
	.badge[data-status="posted"]   { background: rgba(0,255,100,0.12);   color: var(--posted);  border: 1px solid rgba(0,255,100,0.3); }
	.badge[data-status="skipped"]  { background: rgba(255,96,96,0.12);   color: var(--skipped); border: 1px solid rgba(255,96,96,0.3); }
</style>
