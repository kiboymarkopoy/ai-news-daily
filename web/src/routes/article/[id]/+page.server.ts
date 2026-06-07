import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { getArticle } from '$lib/server/db';

export const load: PageServerLoad = async ({ params, platform }) => {
	const db = platform?.env?.DB;
	if (!db) return { article: null };

	const article = await getArticle(db, params.id);
	if (!article) throw error(404, 'Artikel tidak ditemukan');

	return { article };
};
