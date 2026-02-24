[![English](https://img.shields.io/badge/English-en-blue.svg)](#en) [![中文](https://img.shields.io/badge/中文-zh-red.svg)](#zh)

> 🍴 **Fork 声明**: 本项目基于 [VvvvvGH/ComicsUpscaler](https://github.com/VvvvvGH/ComicsUpscaler) 修改，主要添加了 **macOS 支持** 和修复了图片文件名匹配问题。

---

<a id="zh"></a>
# Comics Upscaler (macOS 版)

Comics Upscaler 是一个专门用于优化电子书（EPUB）图片质量的工具。它能够自动提取电子书中的图片，使用AI超分辨率技术提升图片质量，并重新打包成适合电子墨水屏阅读的电子书。

**本分支新增**: Apple Silicon (M1/M2/M3) 和 Intel Mac 支持

## ✨ 特性

- 🚀 支持EPUB格式的电子书处理
- 🖼️ 使用先进的AI超分辨率技术提升图片质量
- 📱 自动优化图片尺寸，适配电子墨水屏
- 📚 保留原始电子书的元数据和目录结构
- 🛠️ 支持批量处理多个文件
- ⚡ 多进程并行处理，提升处理速度
- 🧹 自动清理临时文件
- 🍎 **新增**: 原生 macOS 支持 (Apple Silicon & Intel)

## 🔧 系统要求

### macOS
- macOS 10.15+ (推荐 macOS 12+)
- Python 3.8-3.12
- 内存：建议8GB以上
- 存储空间：建议预留处理文件大小10倍以上的空间
- Apple Silicon Mac: 支持 MPS 加速
- Intel Mac: CPU 处理

### Windows (原版支持)
- Windows 10/11 64位
- NVIDIA显卡（推荐）：支持CUDA加速
- AMD显卡：仅支持在Linux系统下通过ROCm使用

### 通用依赖
- [Final2x-core](https://github.com/Tohrusky/Final2x-core/releases)（用于图片超分辨率处理）

## 📦 安装

### macOS 安装步骤

1. 克隆仓库：
```bash
git clone https://github.com/HY-D1/comics-upscaler-mac.git
cd comics-upscaler-mac
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 下载并配置 Final2x-core：
```bash
# 创建 Final2X 目录
mkdir -p Final2X

# 下载 macOS ARM64 版本（Apple Silicon）
cd Final2X
curl -L -o Final2x-core-macos-arm64.7z "https://github.com/EutropicAI/Final2x-core/releases/download/2024-12-14/Final2x-core-macos-arm64.7z"

# 解压（需要安装 p7zip）
brew install p7zip
7z x Final2x-core-macos-arm64.7z

# 给可执行文件添加权限
chmod +x Final2x-core
```

4. 修改配置文件：
```bash
# 编辑配置文件，设置输入目录
vim comics_upscaler/config/settings.yaml
```

5. 运行程序：
```bash
python3 -m comics_upscaler.main
```

## ⚙️ 配置

在 `config/settings.yaml` 中配置以下参数：

```yaml
# 临时目录
temp_dir: "temp"

# 目录设置
directories:
  # 输入目录路径（修改为你的EPUB文件目录）
  input: "/Users/yourname/Documents/Comics"
  # 输出目录后缀（将添加到输入目录后）
  output_suffix: "_upscale"

# 超分辨率设置
upscale:
  # 使用的模型名称
  model_name: "RealCUGAN_Conservative_2x.pth"
  # 放大倍数 (2x/3x/4x)
  scale: 2
  # 目标长边尺寸（适配电子墨水屏/平板）
  target_long_edge: 1600
  # 并行处理的进程数（Apple Silicon 建议 1-2）
  num_processes: 1
  # 输出图片格式
  output_format: "JPEG"
  # 输出图片质量 (1-100)
  output_quality: 95

# EPUB设置
epub:
  # 是否调整到原始大小
  resize_to_original: false
  # 是否创建新的EPUB
  create_new: false
  # 是否创建适配电子墨水屏的EPUB
  create_eink: true 
```

### 超分辨率模型说明

- **RealCUGAN-pro**: 适合漫画、插画等内容，对线条和细节的保持较好
- **RealCUGAN_Conservative**: 保守模式，减少过度锐化
- **RealESRGAN**: 适合真实照片，对噪点的处理较好
- **SwinIR**: 新一代通用超分辨率模型，效果优秀但处理速度较慢
- **EDSR**: 经典模型，速度和效果均衡

## 🚀 使用方法

1. 将需要处理的 EPUB 漫画文件放入配置文件中指定的 `input` 目录

2. 运行程序：
```bash
python3 -m comics_upscaler.main
```

3. 处理后的文件将保存在 `{input}_upscale` 目录中

### macOS 性能调优

- `num_processes`: Apple Silicon Mac 建议设置为 1-2（视内存而定）
- `scale`: 2x 放大速度最快，4x 质量最高但处理时间更长
- `target_long_edge`: 1600 适合 iPad/平板，2400 适合高分辨率屏幕

## 📝 注意事项

- 处理过程中会占用较多磁盘空间，请确保有足够的存储空间
- 图片处理时间取决于图片数量、尺寸和电脑性能
- 建议在处理大量文件前先测试单本漫画

## 📄 致谢

- 原项目: [VvvvvGH/ComicsUpscaler](https://github.com/VvvvvGH/ComicsUpscaler)
- 超分辨率引擎: [Final2x-core](https://github.com/Tohrusky/Final2x-core) by Tohrusky
- AI 模型: [RealCUGAN](https://github.com/bilibili/ailab/tree/main/Real-CUGAN), [RealESRGAN](https://github.com/xinntao/Real-ESRGAN)

## 📜 License

MIT License (与原版相同)

---

<a id="en"></a>
# Comics Upscaler (macOS Version)

Comics Upscaler is a specialized tool for enhancing image quality in electronic books (EPUB). It automatically extracts images from e-books, uses AI super-resolution technology to improve image quality, and repackages them into e-books suitable for e-ink screen reading.

**This fork adds**: Native macOS support for Apple Silicon (M1/M2/M3) and Intel Macs.

## Credits

- Original project: [VvvvvGH/ComicsUpscaler](https://github.com/VvvvvGH/ComicsUpscaler)
- Super-resolution engine: [Final2x-core](https://github.com/Tohrusky/Final2x-core) by Tohrusky
