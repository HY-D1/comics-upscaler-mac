"""自定义异常类定义"""

class ComicsUpscalerError(Exception):
    """基础异常类"""
    pass

class ConfigError(ComicsUpscalerError):
    """配置相关错误"""
    pass

class ExtractorError(ComicsUpscalerError):
    """图片提取相关错误"""
    pass

class UpscalerError(ComicsUpscalerError):
    """图片超分相关错误"""
    pass

class EPUBBuilderError(ComicsUpscalerError):
    """EPUB构建相关错误"""
    pass

class FileOperationError(ComicsUpscalerError):
    """文件操作相关错误"""
    pass 