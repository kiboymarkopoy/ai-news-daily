/**
 * D1 query helpers — thin wrappers over the D1 binding.
 *
 * All functions take `db: D1Database` so they're injectable and testable.
 */

import type { Article, ArticleListItem, ArticleStatus, Platform, PostStatusValue, Category } from '$lib/types';
import { CATEGORIES, DEFAULT_STATUS } from '$lib/types';

// ── Category helpers ───────────────────────────────────────────────────────

function categoryFromSeq(seq: number): Category {
	return CATEGORIES[seq as keyof typeof CATEGORIES] ?? { key: 'unknown', label: 'Unknown', emoji: '❓' };
}

// ── Article queries ────────────────────────────────────────────────────────

/** List articles for the dashboard grid, newest first. */
export async function listArticles(
	db: D1Database,
	opts: { limit?: number; offset?: number; date?: string; seq?: number } = {}
): Promise<ArticleListItem[]> {
	const conditions: string[] = [];
	const params: (string | number)[] = [];

	if (opts.date) { conditions.push('a.date = ?'); params.push(opts.date); }
	if (opts.seq)  { conditions.push('a.seq = ?');  params.push(opts.seq); }

	const where = conditions.length ? `WHERE ${conditions.join(' AND ')}` : '';
	const limit  = opts.limit  ?? 50;
	const offset = opts.offset ?? 0;
	params.push(limit, offset);

	const rows = await db
		.prepare(
			`SELECT a.id, a.date, a.time, a.seq, a.title_short,
			        a.thumbnail_r2_url, a.has_real_image, a.generated_at,
			        ps_t.status as status_threads,
			        ps_i.status as status_instagram,
			        ps_tw.status as status_twitter
			   FROM articles a
			   LEFT JOIN post_status ps_t  ON ps_t.article_id  = a.id AND ps_t.platform  = 'threads'
			   LEFT JOIN post_status ps_i  ON ps_i.article_id  = a.id AND ps_i.platform  = 'instagram'
			   LEFT JOIN post_status ps_tw ON ps_tw.article_id = a.id AND ps_tw.platform = 'twitter'
			   ${where}
			   ORDER BY a.date DESC, a.time DESC, a.seq ASC
			   LIMIT ? OFFSET ?`
		)
		.bind(...params)
		.all<Record<string, unknown>>();

	return (rows.results ?? []).map((r) => ({
		id:               r.id as string,
		date:             r.date as string,
		time:             r.time as string,
		seq:              r.seq as number,
		category:         categoryFromSeq(r.seq as number),
		title_short:      r.title_short as string,
		thumbnail_r2_url: r.thumbnail_r2_url as string | null,
		has_real_image:   Boolean(r.has_real_image),
		generated_at:     r.generated_at as string,
		status: {
			threads:   (r.status_threads  ?? 'pending') as PostStatusValue,
			instagram: (r.status_instagram ?? 'pending') as PostStatusValue,
			twitter:   (r.status_twitter   ?? 'pending') as PostStatusValue,
		}
	}));
}

/** Get full article by ID (includes body + variants). */
export async function getArticle(db: D1Database, id: string): Promise<Article | null> {
	const row = await db
		.prepare('SELECT * FROM articles WHERE id = ?')
		.bind(id)
		.first<Record<string, unknown>>();
	if (!row) return null;

	const statusRows = await db
		.prepare('SELECT platform, status FROM post_status WHERE article_id = ?')
		.bind(id)
		.all<{ platform: Platform; status: PostStatusValue }>();

	const status: ArticleStatus = { ...DEFAULT_STATUS };
	for (const s of statusRows.results ?? []) {
		status[s.platform] = s.status;
	}

	return {
		id:              row.id as string,
		date:            row.date as string,
		time:            row.time as string,
		seq:             row.seq as number,
		category:        categoryFromSeq(row.seq as number),
		title_short:     row.title_short as string,
		title_id:        row.title_id as string,
		body_md:         row.body_md as string,
		thumb_headline:  row.thumb_headline as string | null,
		source_domain:   row.source_domain as string | null,
		source_name:     row.source_name as string | null,
		source_url:      row.source_url as string,
		image_original:  row.image_original as string | null,
		thumbnail_r2_url: row.thumbnail_r2_url as string | null,
		has_real_image:  Boolean(row.has_real_image),
		variants:        JSON.parse(row.variants_json as string),
		generated_at:    row.generated_at as string,
		created_at:      row.created_at as string,
		status,
	};
}

// ── Ingest (upsert article + init status) ─────────────────────────────────

export async function upsertArticle(db: D1Database, payload: Record<string, unknown>): Promise<void> {
	const {
		id, date, time, seq,
		title_short, title_id, body_md, thumb_headline,
		source_domain, source_name, source_url,
		image_original, thumbnail_r2_url, has_real_image,
		variants_json, generated_at
	} = payload;

	await db.prepare(`
		INSERT INTO articles
			(id, date, time, seq, category_key, category_label, category_emoji,
			 title_short, title_id, body_md, thumb_headline,
			 source_domain, source_name, source_url,
			 image_original, thumbnail_r2_url, has_real_image,
			 variants_json, generated_at)
		VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
		ON CONFLICT(id) DO UPDATE SET
			thumbnail_r2_url = excluded.thumbnail_r2_url,
			has_real_image   = excluded.has_real_image,
			variants_json    = excluded.variants_json,
			generated_at     = excluded.generated_at
	`)
	.bind(
		id, date, time, seq,
		categoryFromSeq(seq as number).key,
		categoryFromSeq(seq as number).label,
		categoryFromSeq(seq as number).emoji,
		title_short, title_id, body_md, thumb_headline ?? '',
		source_domain ?? '', source_name ?? '', source_url ?? '',
		image_original ?? null, thumbnail_r2_url ?? null,
		has_real_image ? 1 : 0,
		variants_json, generated_at
	)
	.run();

	// Init post_status rows (pending) for all 3 platforms — skip if already exist.
	for (const platform of ['threads', 'instagram', 'twitter'] as Platform[]) {
		await db.prepare(`
			INSERT INTO post_status (article_id, platform, status, updated_at)
			VALUES (?, ?, 'pending', datetime('now'))
			ON CONFLICT(article_id, platform) DO NOTHING
		`).bind(id, platform).run();
	}
}

// ── Status update ──────────────────────────────────────────────────────────

export async function updateStatus(
	db: D1Database,
	articleId: string,
	platform: Platform,
	status: PostStatusValue,
	username: string
): Promise<void> {
	await db.prepare(`
		INSERT INTO post_status (article_id, platform, status, posted_at, posted_by, updated_at)
		VALUES (?, ?, ?, ?, ?, datetime('now'))
		ON CONFLICT(article_id, platform) DO UPDATE SET
			status    = excluded.status,
			posted_at = excluded.posted_at,
			posted_by = excluded.posted_by,
			updated_at = excluded.updated_at
	`)
	.bind(
		articleId, platform, status,
		status === 'posted' ? new Date().toISOString() : null,
		username
	)
	.run();

	await db.prepare(`
		INSERT INTO activity_log (article_id, platform, action, username, created_at)
		VALUES (?, ?, ?, ?, datetime('now'))
	`)
	.bind(articleId, platform, `marked_${status}`, username)
	.run();
}
