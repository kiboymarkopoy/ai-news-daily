-- KiMedia Dashboard — D1 Schema
-- Run: wrangler d1 execute kimedia-db --file=web/schema.sql
-- Local: wrangler d1 execute kimedia-db --local --file=web/schema.sql

-- ─────────────────────────────────────────────
-- ARTICLES — sumber data dashboard (bukan git)
-- Diisi oleh Kiboy publisher via POST /api/ingest tiap cron run.
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS articles (
    id               TEXT PRIMARY KEY,   -- "<YYYY-MM-DD>_<HH.MM>-<NN>" e.g. "2026-06-07_16.44-02"
    date             TEXT NOT NULL,      -- "2026-06-07"
    time             TEXT NOT NULL,      -- "16.44"
    seq              INTEGER NOT NULL,   -- 1-5 (kategori slot)
    category_key     TEXT NOT NULL,      -- "industry_business"
    category_label   TEXT NOT NULL,      -- "Industry & Business"
    category_emoji   TEXT NOT NULL,      -- "💰"
    title_short      TEXT NOT NULL,      -- dari "# NN — emoji <ini>" (judul singkat)
    title_id         TEXT NOT NULL,      -- judul lengkap Indonesia (dari "## <ini>")
    body_md          TEXT NOT NULL,      -- body artikel markdown
    thumb_headline   TEXT,               -- dengan **accent** markup
    source_domain    TEXT,               -- "wired.com"
    source_name      TEXT,               -- "Wired" (display name)
    source_url       TEXT NOT NULL,      -- URL ASLI artikel (bukan GN redirect)
    image_original   TEXT,               -- OG image dari artikel asli
    thumbnail_r2_url TEXT,               -- thumbnail KiMedia di R2 (1080x1350)
    has_real_image   INTEGER NOT NULL DEFAULT 0,  -- 0=gradient, 1=foto asli
    variants_json    TEXT NOT NULL,      -- JSON string: {threads, instagram, twitter}
    generated_at     TEXT NOT NULL,      -- ISO timestamp saat publisher jalan (WIB)
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(date DESC);
CREATE INDEX IF NOT EXISTS idx_articles_seq  ON articles(seq);
CREATE INDEX IF NOT EXISTS idx_articles_date_seq ON articles(date DESC, seq);

-- ─────────────────────────────────────────────
-- POST_STATUS — status posting per artikel per platform (mutable)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS post_status (
    article_id  TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    platform    TEXT NOT NULL CHECK(platform IN ('threads','instagram','twitter')),
    status      TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','posted','skipped')),
    posted_at   TEXT,          -- ISO timestamp saat ditandai posted
    posted_by   TEXT,          -- username
    note        TEXT,          -- catatan opsional
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (article_id, platform)
);

CREATE INDEX IF NOT EXISTS idx_post_status_article  ON post_status(article_id);
CREATE INDEX IF NOT EXISTS idx_post_status_platform ON post_status(platform, status);

-- ─────────────────────────────────────────────
-- USERS — satu user admin (hash di env sebagai fallback)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    username      TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,   -- scrypt hash (Web Crypto API)
    display_name  TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────
-- ACTIVITY_LOG — audit trail aksi posting & login
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activity_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id  TEXT,           -- NULL untuk aksi non-artikel (e.g. login)
    platform    TEXT,
    action      TEXT NOT NULL,  -- 'marked_posted' | 'unmarked' | 'skipped' | 'login'
    username    TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_activity_log_article  ON activity_log(article_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_created  ON activity_log(created_at DESC);
