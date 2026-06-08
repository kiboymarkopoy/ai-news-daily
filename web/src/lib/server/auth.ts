/**
 * Auth helpers — session cookie signing + password verification.
 *
 * Password auth: simple SHA-256 hash (deterministic, no salt).
 * Store SHA-256(password) in ADMIN_PASSWORD_HASH env var.
 *
 * Session: HMAC-SHA-256 signed cookie.
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

/** Verify a session token and return the username, or null if invalid / expired. */
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

// ── Password verification — simple SHA-256 (deterministic, no salt) ───────
// ADMIN_PASSWORD_HASH = SHA-256(password) as hex string.
// Generate with: node -e "const c=require('crypto');console.log(c.createHash('sha256').update('yourpassword').digest('hex'))"

export async function sha256hex(text: string): Promise<string> {
	const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
	return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, '0')).join('');
}

export async function verifyPassword(plaintext: string, storedHash: string): Promise<boolean> {
	if (!storedHash) return false;
	const hash = await sha256hex(plaintext);
	return hash === storedHash.toLowerCase().trim();
}

/** Hash a password for storage — SHA-256 hex. */
export async function hashPassword(plaintext: string): Promise<string> {
	return sha256hex(plaintext);
}
