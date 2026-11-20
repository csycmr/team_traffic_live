-- 서울교통라이브 뉴스룸 · MySQL 8 초기 스키마
-- 대상 데이터베이스에 접속한 상태에서 실행한다.

CREATE TABLE IF NOT EXISTS analysis_snapshots (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    analysis_type VARCHAR(100) NOT NULL,
    filters_json JSON NOT NULL,
    facts_json JSON NOT NULL,
    source_info_json JSON NOT NULL,
    verification_status VARCHAR(32) NOT NULL,
    data_as_of DATE NOT NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS source_documents (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    title VARCHAR(500) NOT NULL,
    source_org VARCHAR(200) NOT NULL,
    source_type VARCHAR(32) NOT NULL,
    source_url TEXT NOT NULL,
    published_at DATETIME(6) NULL,
    retrieved_at DATETIME(6) NOT NULL,
    content_excerpt TEXT NULL,
    content_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    verification_status VARCHAR(32) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_source_documents_content_hash (content_hash)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS story_ideas (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    analysis_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(500) NOT NULL,
    angle TEXT NOT NULL,
    news_value TEXT NOT NULL,
    source_ids_json JSON NOT NULL,
    reporting_gaps_json JSON NOT NULL,
    readiness VARCHAR(32) NOT NULL,
    created_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT fk_story_ideas_analysis
        FOREIGN KEY (analysis_id) REFERENCES analysis_snapshots (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS articles (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    story_idea_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(500) NOT NULL,
    content LONGTEXT NOT NULL,
    status VARCHAR(32) NOT NULL,
    validation_passed BOOLEAN NOT NULL DEFAULT FALSE,
    validation_result JSON NULL,
    validated_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
    reporter_guidance TEXT NULL,
    reviewed_by TEXT NULL,
    reviewed_at DATETIME(6) NULL,
    review_note TEXT NULL,
    published_at DATETIME(6) NULL,
    created_at DATETIME(6) NOT NULL,
    updated_at DATETIME(6) NOT NULL,
    PRIMARY KEY (id),
    KEY ix_articles_idea_id (story_idea_id, id),
    KEY ix_articles_publication (status, validation_passed, published_at, id),
    CONSTRAINT fk_articles_story_idea
        FOREIGN KEY (story_idea_id) REFERENCES story_ideas (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;

CREATE TABLE IF NOT EXISTS article_evidence (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    article_id BIGINT UNSIGNED NOT NULL,
    analysis_id BIGINT UNSIGNED NULL,
    source_document_id BIGINT UNSIGNED NULL,
    evidence_role VARCHAR(32) NOT NULL,
    location_label TEXT NOT NULL,
    explanation TEXT NOT NULL,
    PRIMARY KEY (id),
    KEY ix_article_evidence_article_id (article_id, id),
    CONSTRAINT fk_article_evidence_article
        FOREIGN KEY (article_id) REFERENCES articles (id),
    CONSTRAINT fk_article_evidence_analysis
        FOREIGN KEY (analysis_id) REFERENCES analysis_snapshots (id),
    CONSTRAINT fk_article_evidence_source
        FOREIGN KEY (source_document_id) REFERENCES source_documents (id)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4;
