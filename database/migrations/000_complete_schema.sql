-- ============================================================================
-- 完整数据库Schema（最新版本）
-- ============================================================================
-- 说明：此文件包含所有表的最新DDL定义，可直接用于创建新数据库
-- 日期：2026-01-28
-- ============================================================================

-- ============================================================================
-- 1. 创建触发器函数
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================================================
-- 2. 创建 play_news_sources 表（信号源配置表）
-- ============================================================================
-- 注意：必须先创建此表，因为其他表有外键依赖

CREATE TABLE IF NOT EXISTS play_news_sources (
    id BIGSERIAL PRIMARY KEY,
    source_name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    entry_url TEXT NOT NULL,
    content_scope VARCHAR(50) NOT NULL,
    update_frequency VARCHAR(20) NOT NULL, -- cron格式，如 '0 2 * * *'
    is_active BOOLEAN NOT NULL DEFAULT true,
    trust_level INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- 约束
    CONSTRAINT chk_source_type CHECK (source_type IN ('official', 'media', 'platform', 'realtor')),
    CONSTRAINT chk_content_scope CHECK (content_scope IN ('real_estate', 'housing', 'local_business')),
    -- 注意：update_frequency 不设置CHECK约束，允许cron格式（如 '0 2 * * *'）
    CONSTRAINT chk_trust_level CHECK (trust_level >= 1 AND trust_level <= 5)
);

-- play_news_sources 索引
CREATE INDEX IF NOT EXISTS idx_news_sources_is_active ON play_news_sources(is_active);
CREATE INDEX IF NOT EXISTS idx_news_sources_source_type ON play_news_sources(source_type);
CREATE INDEX IF NOT EXISTS idx_news_sources_content_scope ON play_news_sources(content_scope);

-- play_news_sources 触发器
CREATE TRIGGER update_news_sources_updated_at 
    BEFORE UPDATE ON play_news_sources 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 3. 创建 task_logs 表（任务日志表）
-- ============================================================================

CREATE TABLE IF NOT EXISTS task_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type TEXT NOT NULL, -- 'local_news' or 'real_estate'
    status TEXT NOT NULL, -- 'running', 'success', 'failed'
    zipcode TEXT, -- 仅local_news任务有值
    source TEXT, -- 仅real_estate任务有值
    source_id BIGINT, -- 关联play_news_sources.id
    articles_count INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 外键（在play_news_sources表创建后添加）
    CONSTRAINT fk_task_logs_source_id FOREIGN KEY (source_id) 
        REFERENCES play_news_sources(id) ON DELETE SET NULL
);

-- task_logs 索引
CREATE INDEX IF NOT EXISTS idx_task_logs_status ON task_logs(status);
CREATE INDEX IF NOT EXISTS idx_task_logs_started_at ON task_logs(started_at);
CREATE INDEX IF NOT EXISTS idx_task_logs_task_type ON task_logs(task_type);
CREATE INDEX IF NOT EXISTS idx_task_logs_source_id ON task_logs(source_id);

-- ============================================================================
-- 3. 创建 task_logs 表（任务日志表）
-- ============================================================================

CREATE TABLE IF NOT EXISTS task_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type TEXT NOT NULL, -- 'local_news' or 'real_estate'
    status TEXT NOT NULL, -- 'running', 'success', 'failed'
    zipcode TEXT, -- 仅local_news任务有值
    source TEXT, -- 仅real_estate任务有值
    source_id BIGINT, -- 关联play_news_sources.id
    articles_count INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- 外键（在play_news_sources表创建后添加）
    CONSTRAINT fk_task_logs_source_id FOREIGN KEY (source_id) 
        REFERENCES play_news_sources(id) ON DELETE SET NULL
);

-- task_logs 索引
CREATE INDEX IF NOT EXISTS idx_task_logs_status ON task_logs(status);
CREATE INDEX IF NOT EXISTS idx_task_logs_started_at ON task_logs(started_at);
CREATE INDEX IF NOT EXISTS idx_task_logs_task_type ON task_logs(task_type);
CREATE INDEX IF NOT EXISTS idx_task_logs_source_id ON task_logs(source_id);

-- ============================================================================
-- 4. 创建 play_raw_news 表（原始新闻表）
-- ============================================================================

CREATE TABLE IF NOT EXISTS play_raw_news (
    id BIGSERIAL PRIMARY KEY,
    source_id BIGINT NOT NULL,
    city VARCHAR(255) NOT NULL,
    zip_code VARCHAR(50), -- 邮政编码，从config.csv读取
    title TEXT NOT NULL,
    content TEXT, -- 完整内容，非摘要
    publish_date TIMESTAMPTZ,
    url TEXT NOT NULL,
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    raw_category VARCHAR(255), -- 原始分类标签
    crawl_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    discard_reason TEXT, -- 被丢弃原因
    status VARCHAR(20) NOT NULL DEFAULT 'new',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- 外键
    CONSTRAINT fk_raw_news_source_id FOREIGN KEY (source_id) 
        REFERENCES play_news_sources(id) ON DELETE CASCADE,
    
    -- 约束
    CONSTRAINT chk_status CHECK (status IN ('new', 'filtered', 'scored'))
);

-- play_raw_news 索引
CREATE INDEX IF NOT EXISTS idx_raw_news_source_id ON play_raw_news(source_id);
CREATE INDEX IF NOT EXISTS idx_raw_news_city ON play_raw_news(city);
CREATE INDEX IF NOT EXISTS idx_raw_news_zip_code ON play_raw_news(zip_code);
CREATE INDEX IF NOT EXISTS idx_raw_news_status ON play_raw_news(status);
CREATE INDEX IF NOT EXISTS idx_raw_news_publish_date ON play_raw_news(publish_date);
CREATE INDEX IF NOT EXISTS idx_raw_news_crawl_time ON play_raw_news(crawl_time);
CREATE INDEX IF NOT EXISTS idx_raw_news_url ON play_raw_news(url);

-- play_raw_news 触发器
CREATE TRIGGER update_raw_news_updated_at 
    BEFORE UPDATE ON play_raw_news 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 5. 初始化数据（信号源配置）
-- ============================================================================

INSERT INTO play_news_sources (
    source_name, source_type, entry_url, 
    content_scope, update_frequency, is_active, trust_level
) VALUES
-- Newsbreak - 局部新闻平台
(
    'Newsbreak', 'platform',
    'https://www.newsbreak.com/search',
    'local_business',
    '0 2 * * *',  -- 每天凌晨2点
    true,
    3
),
-- Patch.com - 局部新闻平台
(
    'Patch', 'platform',
    'https://patch.com/search',
    'local_business',
    '0 2 * * *',  -- 每天凌晨2点
    true,
    3
),
-- Realtor.com - 房地产平台
(
    'Realtor.com', 'platform',
    'https://www.realtor.com/news/real-estate-news/',
    'real_estate',
    '0 3 * * *',  -- 每天凌晨3点
    true,
    4
),
-- Redfin - 房地产平台
(
    'Redfin', 'platform',
    'https://www.redfin.com/news/all-redfin-reports/',
    'real_estate',
    '0 3 * * *',  -- 每天凌晨3点
    true,
    4
),
-- NAR (National Association of Realtors) - 官方组织
(
    'NAR', 'official',
    'https://www.nar.realtor/newsroom',
    'real_estate',
    '0 4 * * 1',  -- 每周一凌晨4点
    true,
    5
),
-- Freddie Mac - 官方机构
(
    'Freddie Mac', 'official',
    'https://freddiemac.gcs-web.com/?_gl=1*qtpff7*_gcl_au*MTY1ODc4ODI2MC4xNzY5NDkwOTAx*_ga*MTI2MTk2MjU0LjE3Njk0OTA5MDQ.*_ga_B5N0FKC09S*czE3Njk0OTA5MDQkbzEkZzEkdDE3Njk0OTA5MDQkajYwJGwwJGgw',
    'real_estate',
    '0 4 * * 1',  -- 每周一凌晨4点
    true,
    5
)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 6. 验证数据
-- ============================================================================

-- 验证信号源配置
SELECT 
    id, source_name, source_type, content_scope, 
    update_frequency, is_active, trust_level
FROM play_news_sources
ORDER BY id;

-- ============================================================================
-- 完成
-- ============================================================================
