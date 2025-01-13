"""配置管理模块"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import yaml

from ..exceptions.custom_exceptions import ConfigError

@dataclass
class UpscaleConfig:
    """超分配置"""
    model_name: str
    scale: int
    target_long_edge: int = 1872
    num_processes: int = 4
    output_format: str = "JPEG"
    output_quality: int = 95

@dataclass
class EPUBConfig:
    """EPUB配置"""
    resize_to_original: bool = False
    create_new: bool = False
    create_eink: bool = True

@dataclass
class DirectoriesConfig:
    """目录配置"""
    input: str
    output_suffix: str = "_upscale"

@dataclass
class AppConfig:
    """应用配置"""
    temp_dir: Path
    directories: DirectoriesConfig
    upscale: UpscaleConfig
    epub: EPUBConfig
    
    @classmethod
    def from_yaml(cls, config_path: Path) -> 'AppConfig':
        """从YAML文件加载配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                
            directories_config = DirectoriesConfig(
                input=config_data['directories']['input'],
                output_suffix=config_data['directories'].get('output_suffix', '_upscale')
            )
            
            upscale_config = UpscaleConfig(
                model_name=config_data['upscale']['model_name'],
                scale=config_data['upscale']['scale'],
                target_long_edge=config_data['upscale'].get('target_long_edge', 1872),
                num_processes=config_data['upscale'].get('num_processes', 4),
                output_format=config_data['upscale'].get('output_format', 'JPEG'),
                output_quality=config_data['upscale'].get('output_quality', 95)
            )
            
            epub_config = EPUBConfig(
                resize_to_original=config_data['epub'].get('resize_to_original', False),
                create_new=config_data['epub'].get('create_new', False),
                create_eink=config_data['epub'].get('create_eink', True)
            )
            
            return cls(
                temp_dir=Path(config_data['temp_dir']),
                directories=directories_config,
                upscale=upscale_config,
                epub=epub_config
            )
        except Exception as e:
            raise ConfigError(f"加载配置文件失败: {str(e)}")

class ConfigManager:
    """配置管理器"""
    _instance = None
    _config: Optional[AppConfig] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def config(self) -> AppConfig:
        """获取配置"""
        if self._config is None:
            raise ConfigError("配置未初始化")
        return self._config
    
    def init_config(self, config_path: Path) -> None:
        """初始化配置"""
        self._config = AppConfig.from_yaml(config_path) 