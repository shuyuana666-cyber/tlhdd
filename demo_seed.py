from __future__ import annotations

from content_defaults import PART_CATEGORIES, PART_CATEGORY_DEFAULT
from database import DatabaseConnection

DEMO_PARTS = [
    {
        "title": "发动机机油滤清器套装",
        "category_key": "engine",
        "brand": "OEM",
        "part_no": "TLHDD-ENG-001",
        "compatible_models": "Toyota / Nissan / Hyundai",
        "price": "询价",
        "image_url": "/assets/images/vehicle-placeholder.webp",
        "description_zh": "适合批量出口的发动机保养件，可按车型清单匹配规格。",
        "description_en": "Engine service parts for bulk export, matched by vehicle model list.",
        "description_ru": "Расходники двигателя для экспорта, подбираются по списку моделей.",
        "sort_order": 1,
        "is_featured": 1,
    },
    {
        "title": "制动片与刹车盘组合",
        "category_key": "chassis",
        "brand": "Aftermarket",
        "part_no": "TLHDD-BRK-002",
        "compatible_models": "SUV / Sedan",
        "price": "询价",
        "image_url": "/assets/images/vehicle-placeholder.webp",
        "description_zh": "底盘制动系统常用件，支持按车型批量配套。",
        "description_en": "Common brake system parts, available by model matching.",
        "description_ru": "Популярные детали тормозной системы с подбором по модели.",
        "sort_order": 2,
        "is_featured": 1,
    },
    {
        "title": "LED大灯与雾灯总成",
        "category_key": "electric",
        "brand": "OEM",
        "part_no": "TLHDD-LGT-003",
        "compatible_models": "多品牌车型",
        "price": "询价",
        "image_url": "/assets/images/parts-placeholder.webp",
        "description_zh": "电器与照明件，适合维修备货和经销商补货。",
        "description_en": "Electrical and lighting parts for repair stock and dealer replenishment.",
        "description_ru": "Электрика и свет для ремонта и пополнения склада дилера.",
        "sort_order": 3,
        "is_featured": 1,
    },
    {
        "title": "前保险杠与外观覆盖件",
        "category_key": "body",
        "brand": "OEM",
        "part_no": "TLHDD-BDY-004",
        "compatible_models": "按车型确认",
        "price": "询价",
        "image_url": "/assets/images/parts-placeholder.webp",
        "description_zh": "车身覆盖件可按车型、颜色和包装要求组织出口。",
        "description_en": "Body panels can be exported by model, color and packing requirements.",
        "description_ru": "Кузовные детали поставляются по модели, цвету и упаковке.",
        "sort_order": 4,
        "is_featured": 0,
    },
    {
        "title": "空气滤芯 / 空调滤芯组合",
        "category_key": "service",
        "brand": "Aftermarket",
        "part_no": "TLHDD-FLT-005",
        "compatible_models": "Toyota / Mazda / Volkswagen",
        "price": "询价",
        "image_url": "/assets/images/vehicle-placeholder.webp",
        "description_zh": "高频保养易损件，适合长期补货和批量采购。",
        "description_en": "High-frequency service parts for recurring replenishment and bulk orders.",
        "description_ru": "Популярные расходники для регулярного пополнения и опта.",
        "sort_order": 5,
        "is_featured": 0,
    },
    {
        "title": "冬季脚垫与防护用品",
        "category_key": "accessory",
        "brand": "通利华汽车集团",
        "part_no": "TLHDD-ACC-006",
        "compatible_models": "通用 / 定制",
        "price": "询价",
        "image_url": "/assets/images/vehicle-placeholder.webp",
        "description_zh": "适合俄罗斯寒区使用的随车用品和交付配套件。",
        "description_en": "Vehicle accessories for cold-region use and delivery kits.",
        "description_ru": "Аксессуары для холодного климата и комплектов выдачи.",
        "sort_order": 6,
        "is_featured": 0,
    },
]

def ensure_demo_parts(conn: DatabaseConnection) -> None:
    if conn.execute("SELECT COUNT(*) FROM parts").fetchone()[0] != 0:
        return
    parts = DEMO_PARTS
    for part in parts:
        zh, en, ru = PART_CATEGORIES.get(part["category_key"], PART_CATEGORIES[PART_CATEGORY_DEFAULT])
        payload = {
            "category_zh": zh,
            "category_en": en,
            "category_ru": ru,
            "gallery_json": "[]",
            "is_active": 1,
            **part,
        }
        conn.execute(
            """
            INSERT INTO parts
            (title, category_key, category_zh, category_en, category_ru, brand, part_no,
             compatible_models, price, image_url, gallery_json, description_zh,
             description_en, description_ru, sort_order, is_featured, is_active)
            VALUES
            (:title, :category_key, :category_zh, :category_en, :category_ru, :brand, :part_no,
             :compatible_models, :price, :image_url, :gallery_json, :description_zh,
             :description_en, :description_ru, :sort_order, :is_featured, :is_active)
            """,
            payload,
        )
