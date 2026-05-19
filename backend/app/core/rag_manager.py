"""
RAG Manager - Phase 0 Core Implementation
Handles embeddings, deduplication, quality scoring, and Qdrant integration
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
import uuid

import numpy as np

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams
except ImportError:  # pragma: no cover - handled at runtime when feature is used
    QdrantClient = None  # type: ignore[assignment]
    PointStruct = VectorParams = Distance = None  # type: ignore[assignment]

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - optional in lightweight test env
    SentenceTransformer = None  # type: ignore[assignment]

_logger = logging.getLogger(__name__)


class _HashEmbedder:
    """Lightweight fallback embedder for environments without sentence-transformers."""

    def __init__(self, dim: int):
        self.dim = dim

    def _encode_one(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        if not text:
            return vec
        for i, ch in enumerate(text.encode("utf-8")):
            vec[(i * 131 + ch) % self.dim] += (ch % 13) / 13.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def encode(self, texts, batch_size: int = 32):
        if isinstance(texts, str):
            return self._encode_one(texts)
        return np.stack([self._encode_one(text) for text in texts], axis=0)


class RAGManager:
    """
    RAG 管理器 - 处理所有向量化、搜索、去重和质量评分

    Phase 0 Milestone 0A 核心组件
    """

    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    EMBEDDING_DIM = 384
    CHUNK_SIZE = 512
    CHUNK_OVERLAP = 50
    DEDUP_THRESHOLD = 0.95
    
    def __init__(
        self,
        qdrant_url: str = "http://localhost:6333",
        collection_name: str = "knowledge_base",
    ):
        """初始化 RAG Manager"""
        if QdrantClient is None:
            raise RuntimeError("qdrant-client is required for RAGManager")

        self.qdrant_client = QdrantClient(url=qdrant_url)
        self.collection_name = collection_name
        if SentenceTransformer is None:
            _logger.warning("sentence-transformers not installed, using hash embedder fallback")
            self.embedder = _HashEmbedder(self.EMBEDDING_DIM)
        else:
            self.embedder = SentenceTransformer(self.EMBEDDING_MODEL)
        
        # 初始化 Qdrant collection
        self._init_collection()
        
        _logger.info(f"RAGManager 初始化完成 - Qdrant: {qdrant_url}, Collection: {collection_name}")
    
    def _init_collection(self):
        """初始化 Qdrant 集合"""
        try:
            # 检查集合是否存在
            collections = self.qdrant_client.get_collections().collections
            if not any(c.name == self.collection_name for c in collections):
                # 创建新集合
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.EMBEDDING_DIM,
                        distance=Distance.COSINE
                    )
                )
                _logger.info(f"✅ 创建了新的 Qdrant 集合: {self.collection_name}")
            else:
                _logger.info(f"✅ Qdrant 集合已存在: {self.collection_name}")
        except Exception as e:
            _logger.error(f"❌ 初始化 Qdrant 集合失败: {e}")
            raise
    
    def chunk_text(self, text: str) -> list[str]:
        """
        将文本分割成 chunks
        使用简单的固定大小分割，可升级为更智能的分割
        """
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0
        
        for word in words:
            current_chunk.append(word)
            current_size += len(word) + 1
            
            if current_size >= self.CHUNK_SIZE:
                chunk_text = " ".join(current_chunk)
                chunks.append(chunk_text)
                
                # 添加 overlap
                overlap_count = int(len(current_chunk) * 0.1)  # 10% overlap
                current_chunk = current_chunk[-overlap_count:] if overlap_count > 0 else []
                current_size = sum(len(w) + 1 for w in current_chunk)
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return [c.strip() for c in chunks if c.strip()]
    
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """生成向量嵌入"""
        return self.embedder.encode(texts, batch_size=32)
    
    def calculate_quality_score(
        self,
        content: str,
        source_type: str,
        community_validation: int = 0,
        is_user_upload: bool = False,
    ) -> float:
        """
        计算知识条目的质量分数 (0-1)
        
        权重:
          - 来源可靠性: 40%
          - 新鲜度: 20%
          - 社区验证: 20%
          - 特异性: 10%
          - 用户上传: 10%
        """
        source_scores = {
            "git:commit": 0.85,        # Git commits 高质量
            "git:pr": 0.80,            # Pull requests
            "git:issue": 0.70,         # Issues (可能有说法)
            "api:upload": 0.80,        # 用户上传
            "crawler:github": 0.75,    # GitHub 爬虫
            "import:batch": 0.80,      # 批量导入
        }
        
        base_score = source_scores.get(source_type, 0.60)
        
        # 新鲜度 (假设今天创建)
        recency_score = 1.0
        
        # 社区验证
        validation_score = min(1.0, 0.5 + community_validation * 0.1)
        
        # 特异性 (基于内容长度)
        specificity_score = min(1.0, len(content) / 5000)
        
        # 用户上传加分
        upload_bonus = 0.1 if is_user_upload else 0.0
        
        # 加权计算
        quality = (
            base_score * 0.4 +
            recency_score * 0.2 +
            validation_score * 0.2 +
            specificity_score * 0.1 +
            upload_bonus * 0.1
        )
        
        return min(1.0, max(0.0, quality))
    
    def check_duplication(
        self,
        embedding: list[float],
        threshold: float = DEDUP_THRESHOLD,
    ) -> Optional[str]:
        """
        检查是否为重复内容
        
        返回: 如果是重复，返回原始的 point ID；否则返回 None
        """
        try:
            # 在 Qdrant 中搜索相似的向量
            results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=1,
                score_threshold=threshold,
            )
            
            if results:
                _logger.debug(f"🔍 发现潜在重复 (相似度: {results[0].score})")
                return str(results[0].id)
            
            return None
        except Exception as e:
            _logger.warning(f"去重检查失败: {e}")
            return None
    
    def ingest_knowledge(
        self,
        content: str,
        title: str,
        source_type: str,
        source_reference: Optional[str] = None,
        author: Optional[str] = None,
        tags: Optional[list[str]] = None,
        project_id: Optional[str] = None,
    ) -> dict:
        """
        摄入知识条目
        
        流程:
        1. 分割成 chunks
        2. 生成嵌入
        3. 检查重复
        4. 计算质量分数
        5. 存储到 Qdrant
        
        返回: {chunks_created, chunks_skipped, duplicates, quality_scores}
        """
        _logger.info(f"📥 开始摄入知识: {title} (来源: {source_type})")
        
        # 1. 分割
        chunks = self.chunk_text(content)
        _logger.debug(f"   分割成 {len(chunks)} 个 chunks")
        
        # 2. 生成嵌入
        embeddings = self.embed_texts(chunks)
        _logger.debug(f"   生成了 {len(embeddings)} 个向量")
        
        # 3. 质量评分
        quality_score = self.calculate_quality_score(
            content=content,
            source_type=source_type,
            is_user_upload=(source_type == "api:upload"),
        )
        
        # 4. 存储
        chunk_ids = []
        duplicates = 0
        quality_scores = []
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            # 检查重复
            dup_id = self.check_duplication(embedding.tolist())
            if dup_id:
                duplicates += 1
                _logger.debug(f"   跳过重复 chunk {i}: {dup_id}")
                continue
            
            # 生成唯一 ID
            point_id = int(uuid.uuid4().int % 2**31)
            
            # 创建 point
            point = PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload={
                    "title": title,
                    "content": chunk,
                    "source_type": source_type,
                    "source_reference": source_reference or "",
                    "author": author or "unknown",
                    "tags": tags or [],
                    "project_id": project_id or "default",
                    "quality_score": quality_score,
                    "chunk_index": i,
                    "created_at": datetime.utcnow().isoformat(),
                }
            )
            
            # 上传到 Qdrant
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            chunk_ids.append(str(point_id))
            quality_scores.append(quality_score)
        
        created = len(chunk_ids)
        _logger.info(
            f"✅ 摄入完成: {created} chunks 创建, {duplicates} 重复跳过, "
            f"平均质量: {np.mean(quality_scores):.2f}"
        )
        
        return {
            "chunks_created": created,
            "chunks_skipped": duplicates,
            "duplicates": duplicates,
            "chunk_ids": chunk_ids,
            "quality_scores": quality_scores,
            "avg_quality": float(np.mean(quality_scores)) if quality_scores else 0.0,
            "status": "success",
        }
    
    def search(
        self,
        query: str,
        limit: int = 10,
        min_quality: float = 0.5,
    ) -> list[dict]:
        """
        语义搜索知识库
        """
        _logger.debug(f"🔍 搜索: {query}")
        
        # 向量化查询
        query_embedding = self.embedder.encode(query)
        
        # 在 Qdrant 中搜索
        results = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding.tolist(),
            limit=limit,
        )
        
        # 过滤并返回
        hits = []
        for result in results:
            if result.payload.get("quality_score", 0) >= min_quality:
                hits.append({
                    "id": str(result.id),
                    "title": result.payload.get("title", ""),
                    "content": result.payload.get("content", ""),
                    "similarity": result.score,
                    "quality_score": result.payload.get("quality_score", 0),
                    "tags": result.payload.get("tags", []),
                    "source_type": result.payload.get("source_type", ""),
                    "created_at": result.payload.get("created_at", ""),
                })
        
        _logger.debug(f"   找到 {len(hits)} 个相关结果")
        return hits
    
    def get_collection_stats(self) -> dict:
        """获取集合统计信息"""
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            return {
                "collection_name": self.collection_name,
                "vector_count": collection_info.points_count,
                "embedding_dim": self.EMBEDDING_DIM,
                "distance_metric": "cosine",
                "status": "operational",
            }
        except Exception as e:
            _logger.error(f"获取集合统计失败: {e}")
            return {"status": "error", "error": str(e)}
