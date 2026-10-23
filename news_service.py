"""News CRUD and a restricted HTML format for the public article reader."""
from __future__ import annotations

import html
import json
import re
import uuid
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

from database import BASE_DIR, connect
from record_utils import row_to_dict
from url_utils import valid_public_image_url


class ArticleHTML(HTMLParser):
    tags = {"p", "div", "h2", "h3", "h4", "strong", "b", "em", "i", "u", "ul", "ol", "li", "blockquote", "br", "a", "img", "figure", "figcaption", "hr"}
    blocked = {"script", "style", "iframe", "object", "svg", "math", "textarea"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []
        self.suppressed: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.blocked:
            self.suppressed.append(tag)
            return
        if self.suppressed or tag not in self.tags:
            return
        values = dict(attrs)
        safe_attrs = ""
        if tag == "a":
            url = values.get("href") or ""
            parsed = urlparse(url)
            if parsed.scheme in {"http", "https"} or (not parsed.scheme and not parsed.netloc and url.startswith(("/", "#"))):
                safe_attrs = f' href="{html.escape(url, quote=True)}" rel="noopener noreferrer"'
        elif tag == "img":
            try:
                url = valid_public_image_url(values.get("src"), required=True)
            except ValueError:
                return
            safe_attrs = f' src="{html.escape(url, quote=True)}" alt="{html.escape(values.get("alt") or "", quote=True)}" loading="lazy"'
        self.output.append(f"<{tag}{safe_attrs}>")

    def handle_endtag(self, tag):
        if self.suppressed:
            if tag == self.suppressed[-1]:
                self.suppressed.pop()
            return
        if tag in self.tags and tag not in {"img", "br", "hr"}:
            self.output.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.suppressed:
            self.output.append(html.escape(data))


def sanitize_article(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) > 500_000:
        raise ValueError("单个语言的新闻正文不能超过50万字符")
    parser = ArticleHTML()
    parser.feed(text)
    parser.close()
    return "".join(parser.output)


def list_news(*, admin: bool = False, query: str = "", status: str = "", category: str = "") -> list[dict[str, Any]]:
    clauses, params = [], []
    if not admin:
        clauses.append("status='published' AND (published_at IS NULL OR published_at<=UTC_TIMESTAMP())")
    elif status in {"draft", "published"}:
        clauses.append("status=?")
        params.append(status)
    if category in {"company", "industry"}:
        clauses.append("category=?")
        params.append(category)
    if query.strip():
        clauses.append("(title_zh LIKE ? OR title_en LIKE ? OR title_ru LIKE ? OR source LIKE ?)")
        params.extend([f"%{query.strip()}%"] * 4)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with connect() as conn:
        rows = conn.execute("SELECT * FROM news_articles" + where + " ORDER BY sort_order ASC, published_at DESC, id DESC", params).fetchall()
    return [row_to_dict(row) for row in rows]


def get_news(identifier: str | int, *, admin: bool = False) -> dict[str, Any]:
    value = str(identifier)
    item_id = int(value) if value.isascii() and value.isdigit() and len(value) < 19 else 0
    visible = "" if admin else " AND status='published' AND (published_at IS NULL OR published_at<=UTC_TIMESTAMP())"
    with connect() as conn:
        item = conn.execute("SELECT * FROM news_articles WHERE (id=? OR slug=?)" + visible + " LIMIT 1", (item_id, value)).fetchone()
    if item:
        return row_to_dict(item)
    raise ValueError("新闻不存在或尚未发布")


def news_fields(data: dict[str, Any]) -> dict[str, Any]:
    fields = {f"{kind}_{lang}": str(data.get(f"{kind}_{lang}", "")).strip() for kind in ("title", "summary") for lang in ("zh", "en", "ru")}
    for lang in ("zh", "en", "ru"):
        fields[f"content_{lang}"] = sanitize_article(data.get(f"content_{lang}"))
        if len(fields[f"title_{lang}"]) > 300 or len(fields[f"summary_{lang}"]) > 2000:
            raise ValueError("标题最多300字，摘要最多2000字")
    if not fields["title_zh"] or not re.sub(r"<[^>]*>|&nbsp;|\s", "", fields["content_zh"]):
        raise ValueError("请填写中文标题和正文")
    fields["category"] = str(data.get("category", "company"))
    fields["status"] = str(data.get("status", "draft"))
    if fields["category"] not in {"company", "industry"} or fields["status"] not in {"draft", "published"}:
        raise ValueError("新闻分类或发布状态无效")
    fields["source"] = str(data.get("source", "通利华汽车集团")).strip()[:200]
    fields["image_url"] = valid_public_image_url(data.get("image_url"))
    try:
        fields["sort_order"] = int(data.get("sort_order") or 0)
        if not -1_000_000 <= fields["sort_order"] <= 1_000_000:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError("排序值需为有效整数") from None
    published = data.get("published_at")
    try:
        if published:
            date = datetime.fromisoformat(str(published).replace("Z", "+00:00"))
            # Admin datetime-local fields represent Beijing time.
            date = date.replace(tzinfo=timezone(timedelta(hours=8))) if date.tzinfo is None else date
            fields["published_at"] = date.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            fields["published_at"] = None
    except ValueError:
        raise ValueError("发布时间格式无效") from None
    return fields


def save_news(data: dict[str, Any], item_id: int | None = None) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("新闻内容必须为对象")
    if item_id:
        original = get_news(item_id, admin=True)
        # Existing database datetimes are UTC, while user input is explicit local time.
        if original.get("published_at"):
            original["published_at"] = original["published_at"].replace(" ", "T") + "Z"
        data = {**original, **data}
    fields = news_fields(data)
    if fields["status"] == "published" and not fields["published_at"]:
        fields["published_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
    with connect() as conn:
        if item_id:
            fields["id"] = item_id
            assignments = ", ".join(f"{key}=:{key}" for key in fields if key != "id")
            conn.execute(f"UPDATE news_articles SET {assignments}, updated_at=UTC_TIMESTAMP() WHERE id=:id", fields)
        else:
            fields["slug"] = uuid.uuid4().hex
            columns = ", ".join(fields)
            placeholders = ", ".join(f":{key}" for key in fields)
            result = conn.execute(f"INSERT INTO news_articles ({columns}) VALUES ({placeholders})", fields)
            item_id = int(result.lastrowid)
    return get_news(item_id, admin=True)


def delete_news(item_id: int) -> dict[str, bool]:
    with connect() as conn:
        result = conn.execute("DELETE FROM news_articles WHERE id=?", (item_id,))
        if not result.rowcount:
            raise ValueError("新闻不存在或已删除")
    return {"ok": True}


def seed_news() -> None:
    """Import the existing website articles once, preserving their public slugs."""
    marker = "migration.news.v1"
    with connect() as conn:
        if conn.execute("SELECT 1 FROM site_settings WHERE `key`=?", (marker,)).fetchone():
            return
        legacy = conn.execute("SELECT * FROM page_sections WHERE page_key='news'").fetchall()
        articles = json.loads((BASE_DIR / "assets/data/news-initial.json").read_text(encoding="utf-8"))
        entries = []
        if legacy:
            for row in legacy:
                entry = dict(row)
                entry["slug"] = row["section_key"]
                entry["category"] = "industry" if row["eyebrow"] in {"industry", "行业动态"} else "company"
                entry["status"] = "published" if row["is_active"] else "draft"
                items = conn.execute("SELECT * FROM page_section_items WHERE section_id=? AND is_active=1 ORDER BY sort_order,id", (row["id"],)).fetchall()
                for lang in ("zh", "en", "ru"):
                    body = row[f"body_{lang}"] or ""
                    entry[f"summary_{lang}"] = body.split("\n")[0]
                    entry[f"content_{lang}"] = "".join(f"<p>{html.escape(line)}</p>" for line in body.splitlines() if line.strip())
                    for item in items:
                        entry[f"content_{lang}"] += f'<h2>{html.escape(item[f"title_{lang}"] or "")}</h2>' + "".join(f"<p>{html.escape(line)}</p>" for line in (item[f"body_{lang}"] or "").splitlines() if line.strip())
                entries.append(entry)
        else:
            for order, item in enumerate(articles):
                entry = {"slug": item["id"], "category": "company", "status": "published", "sort_order": order, "source": "通利华汽车集团"}
                for lang in ("zh", "en", "ru"):
                    entry[f"title_{lang}"] = item["title"][lang]
                    entry[f"summary_{lang}"] = item["summary"][lang]
                    entry[f"content_{lang}"] = f'<p>{html.escape(item["summary"][lang])}</p>' + "".join(f'<h2>{html.escape(section["title"][lang])}</h2>' + "".join(f"<p>{html.escape(line)}</p>" for line in section["body"][lang].splitlines() if line.strip()) for section in item["sections"])
                entries.append(entry)
        for entry in entries:
            fields = news_fields(entry)
            fields["slug"] = entry["slug"]
            columns = ", ".join(fields)
            conn.execute(f"INSERT IGNORE INTO news_articles ({columns}) VALUES ({', '.join(':'+key for key in fields)})", fields)
        conn.execute("INSERT INTO site_settings (`key`, `value`) VALUES (?, '1')", (marker,))
