import type { PageServerLoad } from './$types';
import { listArticles } from '$lib/server/db';

export const load: PageServerLoad = async ({ platform, url }) => {
	const db   = platform?.env?.DB;
	const date = url.searchParams.get('date') ?? undefined;
	const seq  = url.searchParams.get('seq')  ? Number(url.searchParams.get('seq'))  : undefined;

	const articles = db
		? await listArticles(db, { limit: 100, date, seq })
		: [];   // dev fallback — no DB binding locally without wrangler

	return { articles, filter: { date, seq } };
};
