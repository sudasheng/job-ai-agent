-- ============================================================
-- Job AI Agent - 数据库初始化脚本
-- 数据库: MySQL 8.0+
-- 使用: mysql -u root -p < migrations/init.sql
-- ============================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS job_ai_agent
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE job_ai_agent;

-- ============================================================
-- 用户表
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id CHAR(36) NOT NULL COMMENT 'UUID 主键',
    username VARCHAR(64) NOT NULL COMMENT '用户名',
    email VARCHAR(128) NOT NULL COMMENT '邮箱',
    hashed_password VARCHAR(256) NOT NULL COMMENT '密码哈希',
    nickname VARCHAR(64) DEFAULT NULL COMMENT '昵称',
    avatar_url VARCHAR(512) DEFAULT NULL COMMENT '头像 URL',
    is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否激活',
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否超级管理员',
    bio TEXT DEFAULT NULL COMMENT '个人简介',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_username (username),
    UNIQUE KEY uk_email (email),
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- ============================================================
-- 岗位信息表
-- ============================================================
CREATE TABLE IF NOT EXISTS jobs (
    id CHAR(36) NOT NULL COMMENT 'UUID 主键',
    source VARCHAR(32) NOT NULL DEFAULT 'boss_zhipin' COMMENT '数据来源',
    source_id VARCHAR(128) DEFAULT NULL COMMENT '来源平台 ID',
    source_url VARCHAR(512) DEFAULT NULL COMMENT '来源 URL',
    title VARCHAR(256) NOT NULL COMMENT '岗位名称',
    company_name VARCHAR(256) NOT NULL COMMENT '公司名称',
    city VARCHAR(64) DEFAULT NULL COMMENT '工作城市',
    district VARCHAR(64) DEFAULT NULL COMMENT '区域',
    salary_min INT DEFAULT NULL COMMENT '最低薪资(K)',
    salary_max INT DEFAULT NULL COMMENT '最高薪资(K)',
    salary_desc VARCHAR(128) DEFAULT NULL COMMENT '薪资描述原文',
    experience VARCHAR(64) DEFAULT NULL COMMENT '经验要求',
    education VARCHAR(64) DEFAULT NULL COMMENT '学历要求',
    job_description TEXT DEFAULT NULL COMMENT '岗位描述',
    job_requirements TEXT DEFAULT NULL COMMENT '岗位要求',
    tags TEXT DEFAULT NULL COMMENT '标签 JSON 数组',
    company_industry VARCHAR(128) DEFAULT NULL COMMENT '公司行业',
    company_scale VARCHAR(64) DEFAULT NULL COMMENT '公司规模',
    company_logo VARCHAR(512) DEFAULT NULL COMMENT '公司 Logo URL',
    hr_name VARCHAR(64) DEFAULT NULL COMMENT 'HR/招聘者名称',
    hr_title VARCHAR(128) DEFAULT NULL COMMENT 'HR 职位',
    status VARCHAR(16) NOT NULL DEFAULT 'active' COMMENT '状态',
    published_at TIMESTAMP NULL DEFAULT NULL COMMENT '发布日期',
    scraped_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '抓取时间',
    is_vectorized BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否已向量化',
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否已删除',
    deleted_at TIMESTAMP NULL DEFAULT NULL COMMENT '删除时间',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_source_id (source_id),
    INDEX idx_source (source),
    INDEX idx_title (title),
    INDEX idx_company_name (company_name),
    INDEX idx_city (city),
    INDEX idx_status (status),
    INDEX idx_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='岗位信息表';

-- ============================================================
-- 面试会话表
-- ============================================================
CREATE TABLE IF NOT EXISTS interview_sessions (
    id CHAR(36) NOT NULL COMMENT 'UUID 主键',
    user_id CHAR(36) NOT NULL COMMENT '用户 ID',
    title VARCHAR(256) NOT NULL COMMENT '面试标题',
    direction VARCHAR(128) NOT NULL COMMENT '面试方向',
    job_id CHAR(36) DEFAULT NULL COMMENT '关联岗位 ID',
    status VARCHAR(16) NOT NULL DEFAULT 'in_progress' COMMENT '状态',
    total_questions INT NOT NULL DEFAULT 0 COMMENT '总问题数',
    answered_questions INT NOT NULL DEFAULT 0 COMMENT '已回答数',
    avg_score FLOAT DEFAULT NULL COMMENT '平均得分',
    started_at TIMESTAMP NULL DEFAULT NULL COMMENT '开始时间',
    completed_at TIMESTAMP NULL DEFAULT NULL COMMENT '完成时间',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    INDEX idx_user_id (user_id),
    INDEX idx_direction (direction),
    INDEX idx_status (status),
    CONSTRAINT fk_session_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_session_job FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='面试会话表';

-- ============================================================
-- 面试问题表
-- ============================================================
CREATE TABLE IF NOT EXISTS interview_questions (
    id CHAR(36) NOT NULL COMMENT 'UUID 主键',
    session_id CHAR(36) NOT NULL COMMENT '面试会话 ID',
    sequence INT NOT NULL COMMENT '问题序号',
    question_text TEXT NOT NULL COMMENT '问题文本',
    question_type VARCHAR(32) NOT NULL DEFAULT 'technical' COMMENT '问题类型',
    reference_answer TEXT DEFAULT NULL COMMENT '参考答案',
    knowledge_source VARCHAR(512) DEFAULT NULL COMMENT '知识来源',
    user_answer TEXT DEFAULT NULL COMMENT '用户回答',
    score FLOAT DEFAULT NULL COMMENT '评分',
    score_comment TEXT DEFAULT NULL COMMENT '评分备注',
    answered_at TIMESTAMP NULL DEFAULT NULL COMMENT '回答时间',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    INDEX idx_session_id (session_id),
    INDEX idx_sequence (sequence),
    CONSTRAINT fk_question_session FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='面试问题表';

-- ============================================================
-- 聊天记录表
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_records (
    id CHAR(36) NOT NULL COMMENT 'UUID 主键',
    user_id CHAR(36) NOT NULL COMMENT '用户 ID',
    role VARCHAR(16) NOT NULL COMMENT '角色',
    content TEXT NOT NULL COMMENT '消息内容',
    context_type VARCHAR(32) DEFAULT NULL COMMENT '上下文类型',
    context_id CHAR(36) DEFAULT NULL COMMENT '关联上下文 ID',
    token_count INT DEFAULT NULL COMMENT 'Token 消耗量',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    INDEX idx_user_id (user_id),
    INDEX idx_context_type (context_type),
    INDEX idx_context_id (context_id),
    INDEX idx_created_at (created_at),
    CONSTRAINT fk_chat_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天记录表';