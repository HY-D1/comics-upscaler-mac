"""数据模型定义"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any
from PIL import Image

@dataclass
class ImageInfo:
    """图片信息"""
    page_num: int
    width: int
    height: int
    data: bytes
    success: bool
    error: Optional[str] = None

@dataclass
class ProcessingResult:
    """处理结果"""
    success: bool
    message: str
    error: Optional[Exception] = None

@dataclass
class EPUBMetadata:
    """EPUB元数据"""
    title: Optional[str] = None
    creator: Optional[str] = None
    language: str = 'zh'
    identifier: Optional[str] = None
    modified: Optional[str] = None
    additional_metadata: Dict[str, Any] = None

@dataclass
class EPUBChapter:
    """EPUB章节"""
    title: str
    content: str
    file_name: str
    properties: Optional[Dict[str, Any]] = None

@dataclass
class ProcessedImage:
    """处理后的图片"""
    original_path: Path
    processed_path: Path
    page_number: int
    width: int
    height: int
    format: str
    is_cover: bool = False

@dataclass
class BatchProcessingStats:
    """批处理统计"""
    total_files: int
    processed_files: int
    failed_files: int
    total_images: int
    processed_images: int
    failed_images: int
    start_time: float
    end_time: Optional[float] = None 