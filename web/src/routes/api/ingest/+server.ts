/**
 * POST /api/ingest — Kiboy publisher sends article + thumbnail here.
 *
 * Auth: Authorization: Bearer <INGEST_TOKEN>
 * Body: IngestPayload JSON (thumbnail_png_b64 = base64 PNG)
 * Returns: { ok: true, data: { id, thumbnail_r2_url } }
 */
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { upsertArticle } from '$lib/server/db';
import { uploadThumbnail } from '$lib/server/r2';

export const POST: RequestHandler = async ({ request, platform }) => {
	// ── Auth ──────────────────────────────────────────────────────────────
	const ingestToken = platform?.env?.INGEST_TOKEN ?? '';
	const authHeader  = request.headers.get('Authorization') ?? '';
	if (!ingestToken || authHeader !== `Bearer ${ingestToken}`) {
		return json({ ok: false, error: 'Unauthorized' }, { status: 401 });
	}

	const db = platform?.env?.DB;
	const r2 = platform?.env?.R2;
	if (!db || !r2) {
		return json({ ok: false, error: 'Service unavailable (bindings missing)' }, { status: 503 });
	}

	// ── Parse payload ─────────────────────────────────────────────────────
	let payload: Record<string, unknown>;
	try {
		payload = await request.json();
	} catch {
		return json({ ok: false, error: 'Invalid JSON body' }, { status: 400 });
	}

	const required = ['id','date','time','seq','title_short','title_id','body_md',
	                  'source_url','variants','generated_at'];
	for (const f of required) {
		if (!(f in payload)) {
			return json({ ok: false, error: `Missing required field: ${f}` }, { status: 400 });
		}
	}

	// ── Upload thumbnail to R2 ────────────────────────────────────────────
	let thumbnailR2Url = '';
	const b64 = payload.thumbnail_png_b64 as string;
	if (b64 && b64 !== '__PLACEHOLDER_BASE64_PNG__') {
		try {
			const pngBytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
			const key = `${payload.date}/${(payload.id as string).split('_')[1]}.png`;
			// Public base URL — uses custom domain if set, else r2.dev.
			// TODO: replace with real R2 public URL after CF setup.
			const baseUrl = `https://pub-REPLACE.r2.dev`;
			thumbnailR2Url = await uploadThumbnail(r2, key, pngBytes, baseUrl);
		} catch (err) {
			console.error('R2 upload failed:', err);
			// Non-fatal — article still ingested without thumbnail URL.
		}
	}

	// ── Upsert into D1 ────────────────────────────────────────────────────
	try {
		await upsertArticle(db, {
			...payload,
			thumbnail_r2_url: thumbnailR2Url || null,
			has_real_image:   Boolean(payload.image_original),
			variants_json:    JSON.stringify(payload.variants),
		});
	} catch (err) {
		console.error('D1 upsert failed:', err);
		return json({ ok: false, error: 'Database error' }, { status: 500 });
	}

	return json({
		ok: true,
		data: {
			id:              payload.id,
			thumbnail_r2_url: thumbnailR2Url,
		}
	});
};
