CREATE TABLE IF NOT EXISTS hero_slides (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
              title_zh TEXT NOT NULL,
              title_en TEXT NOT NULL,
              title_ru TEXT NOT NULL,
              lead_zh TEXT NOT NULL,
              lead_en TEXT NOT NULL,
              lead_ru TEXT NOT NULL,
              image_url TEXT NOT NULL,
              sort_order INTEGER NOT NULL DEFAULT 0,
              is_active INTEGER NOT NULL DEFAULT 1,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS home_metrics (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
              `value` TEXT NOT NULL,
              label_zh TEXT NOT NULL,
              label_en TEXT NOT NULL,
              label_ru TEXT NOT NULL,
              sort_order INTEGER NOT NULL DEFAULT 0,
              is_active INTEGER NOT NULL DEFAULT 1,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS vehicles (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
              vehicle_type VARCHAR(20) NOT NULL CHECK(vehicle_type IN ('new', 'used')),
              title TEXT NOT NULL,
              brand TEXT NOT NULL,
              model TEXT NOT NULL DEFAULT (''),
              model_year TEXT NOT NULL DEFAULT (''),
              engine TEXT NOT NULL DEFAULT (''),
              mileage TEXT NOT NULL DEFAULT (''),
              price TEXT NOT NULL DEFAULT (''),
              category_zh TEXT NOT NULL DEFAULT (''),
              category_en TEXT NOT NULL DEFAULT (''),
              category_ru TEXT NOT NULL DEFAULT (''),
              catalog_category_key TEXT NOT NULL DEFAULT (''),
              tag_keys_json TEXT NOT NULL DEFAULT ('[]'),
              image_url TEXT NOT NULL,
              gallery_json TEXT NOT NULL DEFAULT ('[]'),
              description_zh TEXT NOT NULL DEFAULT (''),
              description_en TEXT NOT NULL DEFAULT (''),
              description_ru TEXT NOT NULL DEFAULT (''),
              specs_json TEXT NOT NULL DEFAULT ('{}'),
              sort_order INTEGER NOT NULL DEFAULT 0,
              is_featured INTEGER NOT NULL DEFAULT 0,
              is_active INTEGER NOT NULL DEFAULT 1,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS parts (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
              title TEXT NOT NULL,
              category_key VARCHAR(64) NOT NULL DEFAULT 'engine',
              category_zh TEXT NOT NULL DEFAULT (''),
              category_en TEXT NOT NULL DEFAULT (''),
              category_ru TEXT NOT NULL DEFAULT (''),
              tag_keys_json TEXT NOT NULL DEFAULT ('[]'),
              brand TEXT NOT NULL DEFAULT (''),
              part_no TEXT NOT NULL DEFAULT (''),
              compatible_models TEXT NOT NULL DEFAULT (''),
              price TEXT NOT NULL DEFAULT (''),
              image_url TEXT NOT NULL,
              gallery_json TEXT NOT NULL DEFAULT ('[]'),
              description_zh TEXT NOT NULL DEFAULT (''),
              description_en TEXT NOT NULL DEFAULT (''),
              description_ru TEXT NOT NULL DEFAULT (''),
              sort_order INTEGER NOT NULL DEFAULT 0,
              is_featured INTEGER NOT NULL DEFAULT 0,
              is_active INTEGER NOT NULL DEFAULT 1,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS catalog_terms (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
              scope VARCHAR(32) NOT NULL CHECK(scope IN ('new_vehicle', 'part')),
              term_type VARCHAR(32) NOT NULL CHECK(term_type IN ('category', 'tag')),
              term_key VARCHAR(128) NOT NULL,
              label_zh TEXT NOT NULL DEFAULT (''),
              label_en TEXT NOT NULL DEFAULT (''),
              label_ru TEXT NOT NULL DEFAULT (''),
              description_zh TEXT NOT NULL DEFAULT (''),
              description_en TEXT NOT NULL DEFAULT (''),
              description_ru TEXT NOT NULL DEFAULT (''),
              icon TEXT NOT NULL DEFAULT (''),
              sort_order INTEGER NOT NULL DEFAULT 0,
              is_system INTEGER NOT NULL DEFAULT 0,
              is_active INTEGER NOT NULL DEFAULT 1,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(scope, term_type, term_key)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS admin_users (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
              username VARCHAR(190) NOT NULL UNIQUE,
              password_salt TEXT NOT NULL,
              password_hash TEXT NOT NULL,
              role TEXT NOT NULL DEFAULT ('超级管理员'),
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS admin_sessions (
              token VARCHAR(128) PRIMARY KEY,
              user_id BIGINT UNSIGNED NOT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              expires_at DATETIME NOT NULL,
              FOREIGN KEY(user_id) REFERENCES admin_users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS public_users (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
              account VARCHAR(190) NOT NULL UNIQUE,
              display_name TEXT NOT NULL DEFAULT (''),
              email TEXT NOT NULL DEFAULT (''),
              phone TEXT NOT NULL DEFAULT (''),
              region TEXT NOT NULL DEFAULT (''),
              company TEXT NOT NULL DEFAULT (''),
              avatar_url TEXT NOT NULL DEFAULT (''),
              password_salt TEXT NOT NULL,
              password_hash TEXT NOT NULL,
              role TEXT NOT NULL DEFAULT ('普通用户'),
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              last_login_at DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS public_sessions (
              token VARCHAR(128) PRIMARY KEY,
              user_id BIGINT UNSIGNED NOT NULL,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              expires_at DATETIME NOT NULL,
              FOREIGN KEY(user_id) REFERENCES public_users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS forum_posts (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
              user_kind VARCHAR(16) NOT NULL CHECK(user_kind IN ('admin', 'public')),
              user_id BIGINT UNSIGNED NOT NULL,
              account VARCHAR(190) NOT NULL DEFAULT '',
              author_name TEXT NOT NULL DEFAULT (''),
              title TEXT NOT NULL,
              brand TEXT NOT NULL DEFAULT (''),
              model TEXT NOT NULL DEFAULT (''),
              model_year TEXT NOT NULL DEFAULT (''),
              image_url TEXT NOT NULL DEFAULT (''),
              media_json TEXT NOT NULL DEFAULT ('[]'),
              content TEXT NOT NULL DEFAULT (''),
              topic_category VARCHAR(32) NOT NULL DEFAULT 'general',
              is_featured INTEGER NOT NULL DEFAULT 0,
              is_active INTEGER NOT NULL DEFAULT 1,
              moderation_status VARCHAR(32) NOT NULL DEFAULT 'approved',
              admin_note TEXT NOT NULL DEFAULT (''),
              reviewed_at DATETIME,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS inquiries (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
              user_id BIGINT UNSIGNED,
              name TEXT NOT NULL DEFAULT (''),
              contact TEXT NOT NULL DEFAULT (''),
              destination TEXT NOT NULL DEFAULT (''),
              vehicle_interest TEXT NOT NULL DEFAULT (''),
              budget TEXT NOT NULL DEFAULT (''),
              message TEXT NOT NULL DEFAULT (''),
              source_page TEXT NOT NULL DEFAULT (''),
              status VARCHAR(32) NOT NULL DEFAULT '新询盘',
              admin_note TEXT NOT NULL DEFAULT (''),
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS chat_threads (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
              user_id BIGINT UNSIGNED,
              guest_token VARCHAR(128) NOT NULL DEFAULT '',
              contact_name TEXT NOT NULL DEFAULT (''),
              contact_info TEXT NOT NULL DEFAULT (''),
              product_type VARCHAR(32) NOT NULL DEFAULT '',
              product_id BIGINT UNSIGNED,
              product_title TEXT NOT NULL DEFAULT (''),
              product_url TEXT NOT NULL DEFAULT (''),
              product_image TEXT NOT NULL DEFAULT (''),
              status VARCHAR(32) NOT NULL DEFAULT 'open',
              last_message TEXT NOT NULL DEFAULT (''),
              last_sender VARCHAR(16) NOT NULL DEFAULT '',
              last_message_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              admin_unread INTEGER NOT NULL DEFAULT 0,
              user_unread INTEGER NOT NULL DEFAULT 0,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY(user_id) REFERENCES public_users(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS chat_messages (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
              thread_id BIGINT UNSIGNED NOT NULL,
              sender_kind VARCHAR(16) NOT NULL CHECK(sender_kind IN ('guest', 'user', 'admin', 'system')),
              sender_name TEXT NOT NULL DEFAULT (''),
              body TEXT NOT NULL DEFAULT (''),
              is_read INTEGER NOT NULL DEFAULT 0,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY(thread_id) REFERENCES chat_threads(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS forum_upload_usage (
              user_kind VARCHAR(16) NOT NULL,
              user_id BIGINT UNSIGNED NOT NULL,
              usage_date DATE NOT NULL,
              bytes_used BIGINT UNSIGNED NOT NULL DEFAULT 0,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY(user_kind, user_id, usage_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS site_settings (
              `key` VARCHAR(190) PRIMARY KEY,
              `value` TEXT NOT NULL DEFAULT (''),
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS page_sections (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
              page_key VARCHAR(64) NOT NULL,
              section_key VARCHAR(128) NOT NULL,
              label TEXT NOT NULL DEFAULT (''),
              eyebrow TEXT NOT NULL DEFAULT (''),
              title_zh TEXT NOT NULL DEFAULT (''),
              title_en TEXT NOT NULL DEFAULT (''),
              title_ru TEXT NOT NULL DEFAULT (''),
              body_zh TEXT NOT NULL DEFAULT (''),
              body_en TEXT NOT NULL DEFAULT (''),
              body_ru TEXT NOT NULL DEFAULT (''),
              image_url TEXT NOT NULL DEFAULT (''),
              link_url TEXT NOT NULL DEFAULT (''),
              link_label_zh TEXT NOT NULL DEFAULT (''),
              link_label_en TEXT NOT NULL DEFAULT (''),
              link_label_ru TEXT NOT NULL DEFAULT (''),
              sort_order INTEGER NOT NULL DEFAULT 0,
              is_active INTEGER NOT NULL DEFAULT 1,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(page_key, section_key)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS page_section_items (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
              section_id BIGINT UNSIGNED NOT NULL,
              title_zh TEXT NOT NULL DEFAULT (''),
              title_en TEXT NOT NULL DEFAULT (''),
              title_ru TEXT NOT NULL DEFAULT (''),
              body_zh TEXT NOT NULL DEFAULT (''),
              body_en TEXT NOT NULL DEFAULT (''),
              body_ru TEXT NOT NULL DEFAULT (''),
              image_url TEXT NOT NULL DEFAULT (''),
              link_url TEXT NOT NULL DEFAULT (''),
              sort_order INTEGER NOT NULL DEFAULT 0,
              is_active INTEGER NOT NULL DEFAULT 1,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY(section_id) REFERENCES page_sections(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS page_media (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
              page_key VARCHAR(64) NOT NULL,
              media_key VARCHAR(128) NOT NULL,
              label TEXT NOT NULL DEFAULT (''),
              group_label TEXT NOT NULL DEFAULT (''),
              image_url TEXT NOT NULL DEFAULT (''),
              default_url TEXT NOT NULL DEFAULT (''),
              keep_original INTEGER NOT NULL DEFAULT 0,
              sort_order INTEGER NOT NULL DEFAULT 0,
              is_active INTEGER NOT NULL DEFAULT 1,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(page_key, media_key)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE TABLE IF NOT EXISTS news_articles (
              id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
              slug VARCHAR(128) NOT NULL UNIQUE,
              category VARCHAR(24) NOT NULL DEFAULT 'company',
              title_zh TEXT NOT NULL,
              title_en TEXT NOT NULL DEFAULT (''),
              title_ru TEXT NOT NULL DEFAULT (''),
              summary_zh TEXT NOT NULL DEFAULT (''),
              summary_en TEXT NOT NULL DEFAULT (''),
              summary_ru TEXT NOT NULL DEFAULT (''),
              content_zh MEDIUMTEXT NOT NULL,
              content_en MEDIUMTEXT NOT NULL DEFAULT (''),
              content_ru MEDIUMTEXT NOT NULL DEFAULT (''),
              source VARCHAR(200) NOT NULL DEFAULT '通利华汽车集团',
              image_url TEXT NOT NULL DEFAULT (''),
              status VARCHAR(24) NOT NULL DEFAULT 'draft',
              published_at DATETIME NULL,
              sort_order INTEGER NOT NULL DEFAULT 0,
              created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

            CREATE INDEX idx_news_public ON news_articles(status, sort_order, published_at);
            CREATE INDEX idx_inquiries_user_id ON inquiries(user_id);
            CREATE INDEX idx_inquiries_status_id ON inquiries(status, id);
            CREATE INDEX idx_vehicles_admin_list ON vehicles(is_active, vehicle_type, sort_order, id);
            CREATE INDEX idx_parts_admin_list ON parts(is_active, category_key, sort_order, id);
            CREATE INDEX idx_forum_posts_admin_list ON forum_posts(is_active, moderation_status, topic_category, is_featured, id);
            CREATE INDEX idx_chat_threads_admin_list ON chat_threads(status, last_message_at, id);
            CREATE INDEX idx_catalog_terms_scope_type ON catalog_terms(scope, term_type, sort_order);
            CREATE INDEX idx_chat_threads_user_id ON chat_threads(user_id, updated_at);
            CREATE INDEX idx_chat_threads_guest ON chat_threads(guest_token, updated_at);
            CREATE INDEX idx_chat_messages_thread ON chat_messages(thread_id, created_at);
            CREATE INDEX idx_page_sections_page ON page_sections(page_key, sort_order);
            CREATE INDEX idx_page_items_section ON page_section_items(section_id, sort_order);
            CREATE INDEX idx_page_media_page ON page_media(page_key, sort_order);
