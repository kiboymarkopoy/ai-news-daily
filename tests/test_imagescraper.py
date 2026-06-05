"""Tests for kiboy.imagescraper — OG extraction, block-page & icon filtering.

These lock in the Telegraph/Akamai bug fix: a bot-challenge page must never
yield a logo/icon/SVG as the article image.
"""

from kiboy.imagescraper import (
    _extract_og_from_html,
    _is_block_page,
    _is_usable_image_url,
    is_gn_url,
)


# The exact shape of the Akamai challenge page that broke the Telegraph article.
AKAMAI_BLOCK_HTML = """<!DOCTYPE html><html lang="en"><body>
<script src="/aqT5wEUJvu7/chOENzbu9OaG?t=919848412"></script>
<div id="sec-if-cpt-container" role="main" style="display: none">
  <div class="behavioral-content">
    <div class="scf-akamai-logo-img">
      <img src="https://www.akamai.com/site/ko/images/logo/akamai-logo1.svg"
           class="scf-akamai-logo" alt="Akamai">
    </div>
  </div>
</div></body></html>"""

REAL_ARTICLE_HTML = """<!DOCTYPE html><html><head>
<meta property="og:image" content="https://img.example.com/photo.jpg">
<meta name="twitter:image" content="https://img.example.com/tw.jpg">
</head><body>%s<p>real article body</p></body></html>""" % ("x" * 5000)


class TestIsBlockPage:
    def test_detects_akamai_challenge(self):
        assert _is_block_page(AKAMAI_BLOCK_HTML) is True

    def test_empty_is_block(self):
        assert _is_block_page("") is True

    def test_real_article_not_block(self):
        assert _is_block_page(REAL_ARTICLE_HTML) is False

    def test_large_page_with_akamai_word_not_block(self):
        # A real article merely mentioning "akamai" must not be flagged.
        html = "<html><body>" + ("we use akamai cdn. " * 500) + "</body></html>"
        assert _is_block_page(html) is False


class TestIsUsableImageUrl:
    def test_rejects_svg(self):
        assert _is_usable_image_url("https://x.com/logo.svg") is False

    def test_rejects_logo_in_path(self):
        assert _is_usable_image_url("https://www.akamai.com/images/logo/akamai-logo1.svg") is False

    def test_rejects_icon_and_favicon(self):
        assert _is_usable_image_url("https://x.com/favicon.png") is False
        assert _is_usable_image_url("https://x.com/ui/icon-share.png") is False

    def test_accepts_real_photo(self):
        assert _is_usable_image_url(
            "https://www.telegraph.co.uk/content/dam/business/2026/06/04/TELEMM.jpeg?imwidth=1920"
        ) is True

    def test_empty_is_unusable(self):
        assert _is_usable_image_url("") is False


class TestExtractOgFromHtml:
    def test_block_page_returns_empty(self):
        # The core regression: Akamai page must NOT yield the logo SVG.
        assert _extract_og_from_html(AKAMAI_BLOCK_HTML, "https://telegraph.co.uk/x") == ""

    def test_real_og_image_extracted(self):
        out = _extract_og_from_html(REAL_ARTICLE_HTML, "https://example.com/a")
        assert out == "https://img.example.com/photo.jpg"

    def test_skips_svg_og_falls_to_next(self):
        html = """<html><head>%s
        <meta property="og:image" content="https://x.com/logo.svg">
        <meta name="twitter:image" content="https://x.com/real.jpg">
        </head></html>""" % ("y" * 5000)
        assert _extract_og_from_html(html, "https://x.com") == "https://x.com/real.jpg"

    def test_no_image_returns_empty(self):
        html = "<html><head>%s</head><body>no images</body></html>" % ("z" * 5000)
        assert _extract_og_from_html(html, "https://x.com") == ""


class TestIsGnUrl:
    def test_detects_gn_redirect(self):
        assert is_gn_url("https://news.google.com/rss/articles/CBMiabc123") is True

    def test_plain_url_not_gn(self):
        assert is_gn_url("https://techcrunch.com/article") is False

    def test_empty(self):
        assert is_gn_url("") is False
