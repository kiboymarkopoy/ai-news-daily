/**
 * R2 helpers — upload thumbnail PNG and return public URL.
 */

/** Upload PNG bytes to R2 and return the public URL. */
export async function uploadThumbnail(
	r2: R2Bucket,
	key: string,            // e.g. "2026-06-07/16.44-02.png"
	data: Uint8Array,
	publicBaseUrl: string   // e.g. "https://img.kimedia.ai" or r2.dev URL
): Promise<string> {
	await r2.put(key, data, {
		httpMetadata: { contentType: 'image/png' },
	});
	return `${publicBaseUrl.replace(/\/$/, '')}/${key}`;
}
