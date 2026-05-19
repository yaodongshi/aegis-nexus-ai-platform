"""
Database initialization for Phase 0 Milestone 0A
RAG Foundation with PostgreSQL backend
"""

import logging
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import Session

_logger = logging.getLogger(__name__)


def init_knowledge_tables(database_url: str):
    """
    初始化知识库表
    
    表结构:
    - knowledge_base: 主表，存储所有知识条目
    - source_documents: 追踪导入的文档
    - import_jobs: 批量导入任务
    """
    
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        # 启用 pgvector 扩展 (需要提前安装)
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            _logger.info("✅ pgvector 扩展已启用")
        except Exception as e:
            _logger.warning(f"⚠️  pgvector 扩展加载失败 (可选): {e}")
        
        # 知识库主表
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            project_id VARCHAR(255) NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            
            -- 内容
            title VARCHAR(512) NOT NULL,
            content TEXT NOT NULL,
            
            -- 向量化
            embedding vector(384),
            embedding_model VARCHAR(100) DEFAULT 'all-MiniLM-L6-v2',
            
            -- 来源追踪
            source_type VARCHAR(50),  -- git:commit, api:upload, crawler:github, etc.
            source_reference VARCHAR(500),
            
            -- 质量和标签
            quality_score FLOAT DEFAULT 0.5,
            tags JSONB DEFAULT '[]',
            
            -- 元数据
            metadata JSONB DEFAULT '{}',
            status VARCHAR(20) DEFAULT 'active',  -- active, archived, deleted
            
            -- 时间戳
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            INDEX idx_project_id (project_id),
            INDEX idx_quality_score (quality_score),
            INDEX idx_source_type (source_type),
            INDEX idx_created_at (created_at),
            INDEX idx_status (status)
        )
        """))
        
        # 源文档追踪表
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS source_documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id VARCHAR(255) NOT NULL,
            project_id VARCHAR(255) NOT NULL,
            
            -- 文件信息
            filename VARCHAR(512) NOT NULL,
            file_format VARCHAR(20),  -- pdf, docx, md, json, etc.
            file_size_bytes INT,
            
            -- 摄入信息
            ingestion_method VARCHAR(50),  -- api_upload, github_import, batch_import
            chunks_created INT DEFAULT 0,
            chunks_deduplicated INT DEFAULT 0,
            quality_scores FLOAT8[] DEFAULT ARRAY[]::FLOAT8[],
            
            -- 状态
            status VARCHAR(20) DEFAULT 'processing',  -- processing, complete, failed
            error_message TEXT,
            
            -- 时间戳
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
        """))
        
        # 批量导入任务表
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS batch_import_jobs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id VARCHAR(255) NOT NULL,
            project_id VARCHAR(255) NOT NULL,
            
            -- 导入信息
            job_name VARCHAR(255),
            import_source VARCHAR(50),  -- csv_url, github, local
            source_uri VARCHAR(1000),
            
            -- 统计
            total_rows INT DEFAULT 0,
            successful_imports INT DEFAULT 0,
            failed_imports INT DEFAULT 0,
            skipped_duplicates INT DEFAULT 0,
            
            -- 状态
            status VARCHAR(20) DEFAULT 'queued',  -- queued, processing, complete, failed
            progress_percent INT DEFAULT 0,
            error_message TEXT,
            
            -- 时间戳
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP
        )
        """))
        
        # 虚拟密钥表 (Phase 0B 需要)
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS virtual_keys (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id VARCHAR(255) NOT NULL,
            project_id VARCHAR(255),
            
            -- 密钥信息
            key_name VARCHAR(255) NOT NULL,
            key_hash VARCHAR(255) UNIQUE NOT NULL,
            
            -- 权限
            scopes JSONB DEFAULT '["read:knowledge"]',
            
            -- 元数据
            metadata JSONB DEFAULT '{}',
            last_used_at TIMESTAMP,
            
            -- 状态
            status VARCHAR(20) DEFAULT 'active',  -- active, revoked
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
        """))
        
        conn.commit()
        _logger.info("✅ 所有数据库表已初始化")


if __name__ == "__main__":
    import os
    
    logging.basicConfig(level=logging.INFO)
    
    # 从环境变量读取数据库 URL
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost/team_ai_platform"
    )
    
    init_knowledge_tables(db_url)
    print("✅ 数据库初始化完成")
