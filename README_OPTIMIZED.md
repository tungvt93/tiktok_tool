# Optimized Video Processing Tool

A high-performance, maintainable video processing tool for merging videos with background loops and effects.

## Features

- **High Performance**: Parallel processing with optimal CPU utilization
- **Memory Efficient**: Smart caching and temporary file management
- **Maintainable**: Clean, modular code structure with proper separation of concerns
- **Configurable**: Easy-to-modify settings via configuration classes
- **Error Handling**: Comprehensive error handling and logging
- **Type Safety**: Full type hints for better code reliability

## Architecture

### Core Classes

1. **VideoProcessor**: Handles video metadata and FFmpeg operations
2. **GIFProcessor**: Manages GIF processing and tiling
3. **VideoRenderer**: Handles video rendering operations
4. **VideoMerger**: Main orchestrator class

### Key Improvements

#### Performance Optimizations
- **LRU Cache**: Efficient caching for video metadata
- **Parallel Processing**: Optimal use of CPU cores
- **Memory Management**: Proper cleanup of temporary files
- **Reduced I/O**: Minimized disk operations

#### Code Quality
- **Single Responsibility**: Each class has a specific purpose
- **Dependency Injection**: Easy to test and modify
- **Configuration Management**: Centralized settings
- **Error Handling**: Graceful failure handling
- **Logging**: Comprehensive logging for debugging

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure FFmpeg is installed and available in PATH

## Usage

### Basic Usage

```python
from merged_video_optimized import VideoMerger
from config import DEFAULT_VIDEO_CONFIG

# Use default configuration
merger = VideoMerger()
merger.render_all_videos(add_effects=True)
```

### Custom Configuration

```python
from merged_video_optimized import VideoMerger
from config import VideoConfig

# Custom configuration
config = VideoConfig(
    OUTPUT_WIDTH=1920,
    OUTPUT_HEIGHT=1080,
    SPEED_MULTIPLIER=1.5,
    CRF_VALUE=18  # Higher quality
)

merger = VideoMerger(config)
merger.render_all_videos(add_effects=True)
```

### Production vs Fast Mode

```python
from config import PRODUCTION_VIDEO_CONFIG, FAST_VIDEO_CONFIG

# High quality, slower processing
merger = VideoMerger(PRODUCTION_VIDEO_CONFIG)

# Lower quality, faster processing
merger = VideoMerger(FAST_VIDEO_CONFIG)
```

## Configuration Options

### VideoConfig

| Parameter | Default | Description |
|-----------|---------|-------------|
| `OUTPUT_WIDTH` | 1080 | Output video width |
| `OUTPUT_HEIGHT` | 1080 | Output video height |
| `SPEED_MULTIPLIER` | 1.3 | Video speed multiplier |
| `FRAME_RATE` | 10 | GIF frame rate |
| `CRF_VALUE` | 23 | Video quality (lower = better) |
| `INPUT_DIR` | "dongphuc" | Input video directory |
| `BACKGROUND_DIR` | "video_chia_2" | Background video directory |
| `OUTPUT_DIR` | "output" | Output directory |
| `EFFECTS_DIR` | "effects" | Effects directory |

### FFmpegConfig

| Parameter | Default | Description |
|-----------|---------|-------------|
| `PRESET` | "ultrafast" | FFmpeg preset |
| `CODEC_VIDEO` | "libx264" | Video codec |
| `CODEC_AUDIO` | "aac" | Audio codec |
| `THREADS` | "0" | Thread count (0 = auto) |

## Directory Structure

```
project/
├── dongphuc/          # Input videos
├── video_chia_2/      # Background videos
├── effects/           # GIF effects
├── output/            # Processed videos
├── config.py          # Configuration
├── merged_video_optimized.py  # Main script
├── requirements.txt   # Dependencies
└── README_OPTIMIZED.md
```

## Performance Tips

1. **Use SSD**: Faster I/O operations
2. **Adjust CRF**: Lower values for better quality, higher for speed
3. **Monitor Memory**: Large videos may require more RAM
4. **CPU Cores**: More cores = faster parallel processing

## Error Handling

The tool includes comprehensive error handling:

- **File Not Found**: Graceful handling of missing files
- **FFmpeg Errors**: Detailed error messages and logging
- **Memory Issues**: Automatic cleanup of temporary files
- **Process Interruption**: Clean shutdown on Ctrl+C

## Logging

The tool uses Python's logging module with different levels:

- **INFO**: General progress information
- **WARNING**: Non-critical issues
- **ERROR**: Critical errors that may affect processing

## Migration from Original

To migrate from the original script:

1. Replace `merged-video.py` with `merged_video_optimized.py`
2. Use the new configuration system
3. Update any custom scripts to use the new API

## Troubleshooting

### Common Issues

1. **FFmpeg not found**: Ensure FFmpeg is installed and in PATH
2. **Memory errors**: Reduce parallel workers or video quality
3. **Slow processing**: Check disk I/O and CPU usage
4. **Missing files**: Verify input directories and file patterns

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

When contributing:

1. Follow the existing code structure
2. Add type hints to new functions
3. Include error handling
4. Update documentation
5. Add tests if possible

## License

This project is open source and available under the MIT License. 