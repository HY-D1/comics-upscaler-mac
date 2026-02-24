# 🚀 M1 Pro 16GB 性能优化指南

## 硬件配置分析

| 组件 | 规格 | 优化利用 |
|------|------|----------|
| **CPU** | 10 核 (8P+2E) | 3-4 并行进程 |
| **GPU** | 16 核 | CoreML 加速 |
| **内存** | 16GB 统一内存 | 每进程约 2-3GB |
| **SSD** | 512GB | 高速临时文件读写 |

---

## ⚡ 速度优化配置

### 1. 并行进程数 (`num_processes`)

```yaml
num_processes: 3   # 推荐：3-4
```

**选择建议：**
- **3 进程** (推荐)：系统稳定，可同时进行其他任务
- **4 进程**：最大性能，但系统可能略微卡顿
- **2 进程**：适合边处理边做其他工作

### 2. 模型选择对比

| 模型 | 速度 | 质量 | 适用场景 |
|------|------|------|----------|
| `RealCUGAN_Conservative_2x.pth` | ⚡⚡⚡ 最快 | ⭐⭐⭐ 优秀 | **推荐日常使用** |
| `RealCUGAN_Conservative_4x.pth` | ⚡ 慢 4x | ⭐⭐⭐⭐ 更好 | 追求极致质量 |
| `RealCUGAN_Pro_2x.pth` | ⚡⚡ 中等 | ⭐⭐⭐⭐ 更好 | 平衡选择 |

### 3. 目标长边尺寸

```yaml
target_long_edge: 2400   # 推荐
```

| 设备 | 建议尺寸 | 说明 |
|------|----------|------|
| iPad Mini/Air | 2000 | 平衡质量与文件大小 |
| iPad Pro 11" | 2388 | 原生分辨率 |
| iPad Pro 12.9" | 2400-2732 | 原生分辨率 |
| Kindle Scribe | 2880 | 最大支持尺寸 |
| iPhone | 1600 | 足够清晰 |

---

## 🔥 全力运行命令

### 单本快速处理（当前运行）
```bash
cd /Users/harrydai/Downloads/镖人/ComicsUpscaler

# 确保配置已优化
# num_processes: 3, scale: 2, target_long_edge: 2400

# 后台运行，详细日志
nohup python -m comics_upscaler.main > upscale_fullspeed.log 2>&1 &

# 查看实时进度
tail -f upscale_fullspeed.log
```

### 监控性能
```bash
# 查看 CPU/GPU 占用
htop

# 查看内存使用
vm_stat 1

# 查看 Final2x 进程
ps aux | grep Final2x
```

---

## ⏱️ 预计处理时间

### M1 Pro 16GB + 3 并行进程

| 操作 | 每页耗时 | 200 页漫画耗时 |
|------|----------|----------------|
| **2x 超分** | 2-3 秒 | 6-10 分钟 |
| **4x 超分** | 8-12 秒 | 25-40 分钟 |
| EPUB 重建 | - | 30 秒 |
| **总计 (2x)** | - | **约 8 分钟/本** |
| **总计 (4x)** | - | **约 35 分钟/本** |

### 11 本漫画总时间估算
- **2x 模式**: 11 × 8 分钟 = **约 1.5 小时**
- **4x 模式**: 11 × 35 分钟 = **约 6.5 小时**

---

## 🌡️ 散热与性能维持

### M1 Pro 温度管理
- **正常温度**: 50-70°C
- **高负载**: 80-90°C（正常，有温控保护）
- **降频阈值**: 约 95°C

### 维持峰值性能建议
1. **插电使用**：电池模式下性能会降低
2. **良好通风**：确保散热孔畅通
3. **关闭高功耗应用**：如视频播放、游戏
4. **勿扰模式**：减少后台任务

---

## 💾 存储空间检查

### 临时文件占用估算

| 项目 | 大小 | 备注 |
|------|------|------|
| 原始 EPUB | ~100MB/本 | 输入文件 |
| 解压图片 | ~500MB/本 | 临时文件 |
| 超分输出 (2x) | ~1.5GB/本 | 临时文件 |
| 最终 EPUB (2x) | ~200MB/本 | 输出文件 |
| **单本峰值占用** | **~2.1GB** | 处理中 |

### 清理命令
```bash
# 清理临时文件（处理完成后执行）
rm -rf /Users/harrydai/Downloads/镖人/temp/*
rm -rf /Users/harrydai/Downloads/镖人/ComicsUpscaler/projects/*

# 查看磁盘空间
df -h
```

---

## 📊 当前配置状态

运行以下命令检查配置：

```bash
cd /Users/harrydai/Downloads/镖人/ComicsUpscaler
cat comics_upscaler/config/settings.yaml
```

### 推荐配置速查

```yaml
upscale:
  model_name: "RealCUGAN_Conservative_2x.pth"  # 快速高质量
  scale: 2                                      # 2x 放大
  target_long_edge: 2400                        # iPad Pro 优化
  num_processes: 3                              # 3 并行进程
  output_format: "JPEG"
  output_quality: 95
```

---

## 🎯 进阶优化

### 1. 夜间批量处理脚本
```bash
#!/bin/bash
# save as: batch_upscale.sh

cd /Users/harrydai/Downloads/镖人/ComicsUpscaler

# 降低系统功耗管理，提升性能
sudo pmset -a disablesleep 1

# 运行处理
python -m comics_upscaler.main

# 恢复睡眠
sudo pmset -a disablesleep 0

# 完成后提醒
osascript -e 'display notification "超分完成" with title "ComicsUpscaler"'
```

### 2. 分段处理（如果内存不足）
如果处理大文件时内存不足，可以：
1. 减少 `num_processes` 到 2
2. 降低 `target_long_edge` 到 2000
3. 分批处理漫画（不要一次性扫描整个目录）

---

## ✅ 优化检查清单

- [ ] 已连接电源适配器
- [ ] num_processes 设置为 3 或 4
- [ ] 选择 2x 模型以获得最快速度
- [ ] target_long_edge 按需设置
- [ ] 关闭其他高负载应用
- [ ] 确保磁盘剩余空间 > 20GB
- [ ] 在终端使用 `nohup` 后台运行
