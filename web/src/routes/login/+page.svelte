<script lang="ts">
	import type { ActionData } from './$types';
	let { form }: { form: ActionData } = $props();
</script>

<svelte:head><title>Login — KiMedia Dashboard</title></svelte:head>

<div class="login-wrap">
	<div class="brand">KiMedia<span class="dot">■</span></div>
	<h1>Dashboard</h1>
	{#if form?.error}
		<p class="error">{form.error}</p>
	{/if}
	<form method="POST">
		<label>
			Username
			<input name="username" type="text" autocomplete="username" required />
		</label>
		<label>
			Password
			<input name="password" type="password" autocomplete="current-password" required />
		</label>
		<button type="submit">Masuk</button>
	</form>
</div>

<style>
	.login-wrap {
		max-width: 360px;
		margin: 20vh auto 0;
		padding: 2rem;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}
	.brand { font-size: 1.5rem; font-weight: 900; letter-spacing: -0.5px; }
	.dot { color: var(--accent); margin-left: 2px; }
	h1 { font-size: 1.1rem; color: var(--text-muted); font-weight: 400; }
	.error {
		background: rgba(255,96,96,0.12);
		border: 1px solid var(--skipped);
		color: var(--skipped);
		padding: 0.6rem 0.8rem;
		border-radius: 4px;
		font-size: 0.875rem;
	}
	form { display: flex; flex-direction: column; gap: 1rem; }
	label { display: flex; flex-direction: column; gap: 0.4rem; font-size: 0.875rem; color: var(--text-muted); }
	input {
		background: var(--bg);
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text);
		font-family: inherit;
		font-size: 1rem;
		padding: 0.6rem 0.75rem;
	}
	input:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
	button {
		background: var(--accent);
		border: none;
		border-radius: var(--radius);
		color: #000;
		font-size: 1rem;
		font-weight: 700;
		padding: 0.75rem;
		transition: opacity 0.15s;
	}
	button:hover { opacity: 0.85; }
</style>
