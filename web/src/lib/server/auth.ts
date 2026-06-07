/**
 * Auth helpers — session cookie signing + password verification.
 *
 * Uses Web Crypto API (available in Cloudflare Workers / edge runtime).
 * No external dependencies.
 */

const SESSION_TTL_SECONDS = 60 * 60 * 24 * 7; // 7 days

// ── HMAC session cookie ────────────────────────────────────────────────────

async function importKey(secret: string): Promise<CryptoKey> {
	const enc = new TextEncoder().encode(secret);
	return crypto.subtle.importKey('raw', enc, { name: 'HMAC', hash: 'SHA-256' }, false, [
		'sign',
		'verify'
	]);
}

/** Create a signed session token for *username*. */
export async function createSession(username: string, secret: string): Promise<string> {
	const expires = Math.floor(Date.now() / 1000) + SESSION_TTL_SECONDS;
	const payload = JSON.stringify({ username, expires });
	const encoded = btoa(payload);
	const key = await importKey(secret);
	const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(encoded));
	const sigHex = Array.from(new Uint8Array(sig))
		.map((b) => b.toString(16).padStart(2, '0'))
		.join('');
	return `${encoded}.${sigHex}`;
}

/**
 * Verify a session token and return the username, or null if invalid / expired.
 */
export async function verifySession(token: string, secret: string): Promise<string | null> {
	try {
		const [encoded, sigHex] = token.split('.');
		if (!encoded || !sigHex) return null;

		const key = await importKey(secret);
		const sigBytes = new Uint8Array(sigHex.match(/.{2}/g)!.map((h) => parseInt(h, 16)));
		const valid = await crypto.subtle.verify('HMAC', key, sigBytes, new TextEncoder().encode(encoded));
		if (!valid) return null;

		const { username, expires } = JSON.parse(atob(encoded));
		if (Math.floor(Date.now() / 1000) > expires) return null;

		return username as string;
	} catch {
		return null;
	}
}

// ── Password verification (scrypt via Web Crypto) ─────────────────────────

/**
 * Verify a plaintext password against a stored "salt:hash" scrypt record.
 *
 * Hash format (from .env.example generation command):
 *   <saltHex>:<hashHex>
 */
export async function verifyPassword(plaintext: string, storedHash: string): Promise<boolean> {
	try {
		const [saltHex, hashHex] = storedHash.split(':');
		if (!saltHex || !hashHex) return false;

		const salt = new Uint8Array(saltHex.match(/.{2}/g)!.map((h) => parseInt(h, 16)));
		const keyMaterial = await crypto.subtle.importKey(
			'raw',
			new TextEncoder().encode(plaintext),
			'PBKDF2',
			false,
			['deriveBits']
		);
		// Use PBKDF2 (Web Crypto doesn't have scrypt; PBKDF2 is the available alternative)
		const derived = await crypto.subtle.deriveBits(
			{ name: 'PBKDF2', hash: 'SHA-256', salt, iterations: 200_000 },
			keyMaterial,
			512
		);
		const derivedHex = Array.from(new Uint8Array(derived))
			.map((b) => b.toString(16).padStart(2, '0'))
			.join('');
		return derivedHex === hashHex;
	} catch {
		return false;
	}
}

/**
 * Hash a plaintext password for storage (PBKDF2-SHA256, 200k iterations).
 * Run once when setting up the admin password — paste result into env var.
 */
export async function hashPassword(plaintext: string): Promise<string> {
	const salt = crypto.getRandomValues(new Uint8Array(16));
	const keyMaterial = await crypto.subtle.importKey(
		'raw',
		new TextEncoder().encode(plaintext),
		'PBKDF2',
		false,
		['deriveBits']
	);
	const derived = await crypto.subtle.deriveBits(
		{ name: 'PBKDF2', hash: 'SHA-256', salt, iterations: 200_000 },
		keyMaterial,
		512
	);
	const saltHex = Array.from(salt).map((b) => b.toString(16).padStart(2, '0')).join('');
	const hashHex = Array.from(new Uint8Array(derived)).map((b) => b.toString(16).padStart(2, '0')).join('');
	return `${saltHex}:${hashHex}`;
}
