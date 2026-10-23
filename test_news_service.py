"""Run with python -m unittest test_news_service (no database writes)."""
import unittest
from datetime import datetime

from news_service import news_fields, sanitize_article


class NewsContentTests(unittest.TestCase):
    def test_preserves_article_format(self):
        value = '<h2>标题</h2><p>正文<strong>重点</strong></p><ul><li>项目</li></ul><img src="/uploads/news.webp" alt="图片">'
        clean = sanitize_article(value)
        self.assertIn('<h2>标题</h2>', clean)
        self.assertIn('<strong>重点</strong>', clean)
        self.assertIn('<ul><li>项目</li></ul>', clean)
        self.assertIn('src="/uploads/news.webp"', clean)

    def test_removes_active_content_and_inline_styling(self):
        clean = sanitize_article('<script>alert(1)</script><iframe>secret</iframe><p style="color:red" onclick="alert(1)">正常</p><img src="javascript:alert(1)" onerror="alert(1)">')
        self.assertEqual(clean, '<p>正常</p>')

    def test_blocks_script_links_and_escapes_attributes(self):
        clean = sanitize_article('<a href="javascript:alert(1)">链接</a><img src="/assets/x&quot; onerror=&quot;alert(1)" alt="&quot;">')
        self.assertIn('<a>链接</a>', clean)
        self.assertNotIn('src="/assets/x"', clean)
        self.assertIn('&quot;', clean)

    def test_preserves_safe_links(self):
        self.assertIn('href="https://example.com/news"', sanitize_article('<a href="https://example.com/news">链接</a>'))

    def test_requires_title_and_readable_chinese_body(self):
        for value in ({}, {'title_zh': '新闻', 'content_zh': '<p>&nbsp;<br></p>'}):
            with self.assertRaises(ValueError):
                news_fields(value)

    def test_converts_beijing_time_to_utc(self):
        fields = news_fields({'title_zh': '新闻', 'content_zh': '<p>正文</p>', 'published_at': '2026-10-10T09:00'})
        self.assertEqual(fields['published_at'], datetime(2026, 10, 10, 1))

    def test_respects_explicit_time_zone(self):
        fields = news_fields({'title_zh': '新闻', 'content_zh': '正文', 'published_at': '2026-10-10T01:00:00Z'})
        self.assertEqual(fields['published_at'], datetime(2026, 10, 10, 1))

    def test_rejects_invalid_categories_status_and_dates(self):
        for extra in ({'category': 'other'}, {'status': 'deleted'}, {'published_at': 'invalid'}, {'sort_order': 1_000_001}, {'image_url': 'javascript:alert(1)'}):
            with self.assertRaises(ValueError):
                news_fields({'title_zh': '新闻', 'content_zh': '正文', **extra})


if __name__ == '__main__':
    unittest.main()
