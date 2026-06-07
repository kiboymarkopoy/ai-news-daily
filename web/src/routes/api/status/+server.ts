/**
 * GET  /api/status?article_id=  → current status for 3 platforms
 * POST /api/status               → update one platform status
 */
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { updateStatus } from '$lib/server/db';
import type { Platform, PostStatusValue } from '$lib/types';

const VALID_PLATFORMS = new Set(['threads', 'instagram', 'twitter']);
const VALID_STATUSES  = new Set(['pending', 'posted', 'skipped']);

export const GET: RequestHandler = async ({ url, platform }) => {
	const db = platform?.env?.DB;
	if (!db) return json({ ok: false, error: 'No DB' }, { status: 503 });

	const articleId = url.searchParams.get('article_id');
	if (!articleId) return json({ ok: false, error: 'Missing article_id' }, { status: 400 });

	const rows = await db
		.prepare('SELECT platform, status FROM post_status WHERE article_id = ?')
		.bind(articleId)
		.all<{ platform: string; status: string }>();

	const result: Record<string, string> = { threads: 'pending', instagram: 'pending', twitter: 'pending' };
	for (const r of rows.results ?? []) result[r.platform] = r.status;

	return json({ ok: true, data: result });
};

export const POST: RequestHandler = async ({ request, locals, platform }) => {
	const user = locals.user;
	if (!user) return json({ ok: false, error: 'Unauthorized' }, { status: 401 });

	const db = platform?.env?.DB;
	if (!db) return json({ ok: false, error: 'No DB' }, { status: 503 });

	let body: { article_id: string; platform: Platform; status: PostStatusValue };
	try { body = await request.json(); } catch {
		return json({ ok: false, error: 'Invalid JSON' }, { status: 400 });
	}

	if (!body.article_id || !VALID_PLATFORMS.has(body.platform) || !VALID_STATUSES.has(body.status)) {
		return json({ ok: false, error: 'Invalid fields' }, { status: 400 });
	}

	await updateStatus(db, body.article_id, body.platform, body.status, user);
	return json({ ok: true });
};
