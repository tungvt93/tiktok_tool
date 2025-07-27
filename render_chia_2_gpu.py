import os
import subprocess
from glob import glob
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
import tempfile
import json
from pathlib import Path

def check_gpu_support():
    """Kiểm tra GPU support cho encoding"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"], 
            capture_output=True, text=True
        )
        encoders = result.stdout
        return {
            'nvenc': 'h264_nvenc' in encoders,
            'qsv': 'h264_qsv' in encoders,
            'videotoolbox': 'h264_videotoolbox' in encoders
        }
    except:
        return {'nvenc': False, 'qsv': False, 'videotoolbox': False}

def get_best_encoder():
    """Chọn encoder tốt nhất có sẵn"""
    gpu_support = check_gpu_support()
    
    if gpu_support['nvenc']:
        return 'h264_nvenc', '-preset', 'p1'  # NVIDIA GPU
    elif gpu_support['qsv']:
        return 'h264_qsv', '-preset', 'veryfast'  # Intel GPU
    elif gpu_support['videotoolbox']:
        return 'h264_videotoolbox', '-allow_sw', '1'  # Apple Silicon
    else:
        return 'libx264', '-preset', 'ultrafast'  # CPU fallback

def run_ffmpeg(cmd, silent=False):
    if not silent:
        print("▶️ Running:", ' '.join(cmd))
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL if silent else None)

def get_video_duration(path):
    """Cache video duration với persistent cache"""
    cache_file = "duration_cache.json"
    
    # Load cache từ file
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cache = json.load(f)
    else:
        cache = {}
    
    if path in cache:
        return cache[path]
    
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
         "default=noprint_wrappers=1:nokey=1", path],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    duration = float(result.stdout.strip())
    
    # Save to cache
    cache[path] = duration
    with open(cache_file, 'w') as f:
        json.dump(cache, f)
    
    return duration

def create_background_loop_optimized(bg_video, target_duration, temp_dir, encoder, encoder_args):
    """Tạo background loop với tối ưu hóa"""
    bg_duration = get_video_duration(bg_video)
    
    # Sử dụng filter loop với tối ưu hóa
    temp_bg_loop = os.path.join(temp_dir, "bg_loop.mp4")
    
    # Tạo loop với filter hiệu quả hơn
    run_ffmpeg([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", bg_video,
        "-t", str(target_duration),
        "-c:v", encoder, *encoder_args,
        "-an", "-avoid_negative_ts", "make_zero",
        temp_bg_loop
    ], silent=True)
    
    return temp_bg_loop

def render_single_gpu_optimized(main_video, bg_video, index):
    video_name = os.path.splitext(os.path.basename(main_video))[0]
    output_file = f"output/{video_name}.mp4"

    if os.path.exists(output_file):
        print(f"⏩ Bỏ qua: {output_file} đã tồn tại.")
        return

    # Chọn encoder tốt nhất
    encoder, *encoder_args = get_best_encoder()
    print(f"🎯 Sử dụng encoder: {encoder}")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_main = os.path.join(temp_dir, "main_speed.mp4")
        temp_bg_loop = os.path.join(temp_dir, "bg_loop.mp4")
        
        # Bước 1: Tăng tốc video chính với encoder tối ưu
        run_ffmpeg([
            "ffmpeg", "-y", "-i", main_video, 
            "-filter_complex", "[0:v]setpts=PTS/1.3[v];[0:a]atempo=1.3[a]",
            "-map", "[v]", "-map", "[a]", 
            "-c:v", encoder, *encoder_args,
            "-c:a", "aac", "-threads", "0",
            temp_main
        ], silent=True)
        
        main_duration = get_video_duration(temp_main)
        
        # Bước 2: Tạo background loop tối ưu
        temp_bg_loop = create_background_loop_optimized(
            bg_video, main_duration, temp_dir, encoder, encoder_args
        )
        
        # Bước 3: Render cuối cùng với tối ưu hóa cao
        run_ffmpeg([
            "ffmpeg", "-y",
            "-i", temp_main,
            "-i", temp_bg_loop,
            "-filter_complex",
            "[0:v]scale=540:1080:flags=lanczos[left]; "
            "[1:v]scale=540:1080:flags=lanczos[right]; "
            "[left][right]hstack=inputs=2[v]",
            "-map", "[v]", "-map", "0:a",
            "-c:v", encoder, *encoder_args,
            "-crf", "20" if encoder == 'libx264' else "23",  # Chất lượng cao hơn cho GPU
            "-c:a", "aac", "-b:a", "128k",
            "-shortest", "-threads", "0",
            output_file
        ])

    print(f"✅ Render xong: {output_file}")

def preprocess_backgrounds(background_videos):
    """Tiền xử lý với progress bar"""
    print("🔄 Đang cache thông tin background videos...")
    total = len(background_videos)
    for i, bg_video in enumerate(background_videos, 1):
        get_video_duration(bg_video)
        print(f"\r📊 Progress: {i}/{total} ({i/total*100:.1f}%)", end="")
    print(f"\n✅ Đã cache {total} background videos")

def render_all_gpu_optimized():
    os.makedirs("output", exist_ok=True)
    download_videos = sorted(glob("dongphuc/*.mp4"))
    background_videos = sorted(glob("video_chia_2/*.mp4"))

    if not download_videos or not background_videos:
        print("❌ Thiếu video trong dongphuc/ hoặc video_chia_2/")
        return

    # Kiểm tra GPU support
    gpu_support = check_gpu_support()
    print("🔍 GPU Support:", gpu_support)
    
    # Tiền xử lý
    preprocess_backgrounds(background_videos)
    
    # Tối ưu số workers dựa trên CPU và GPU
    cpu_count = os.cpu_count()
    if any(gpu_support.values()):
        max_workers = min(cpu_count, len(download_videos), 4)  # Giới hạn cho GPU
    else:
        max_workers = min(cpu_count, len(download_videos))
    
    print(f"🚀 Sử dụng {max_workers} processes để render")
    
    # Submit tasks với progress tracking
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for idx, main_video in enumerate(download_videos):
            bg_video = random.choice(background_videos)
            print(f"📋 Queue {idx+1}/{len(download_videos)}: {os.path.basename(main_video)}")
            future = executor.submit(render_single_gpu_optimized, main_video, bg_video, idx)
            futures.append(future)
        
        # Track progress
        completed = 0
        for future in as_completed(futures):
            try:
                future.result()
                completed += 1
                print(f"🎉 Progress: {completed}/{len(futures)} ({completed/len(futures)*100:.1f}%)")
            except Exception as e:
                print(f"❌ Lỗi: {e}")

def cleanup_temp_files():
    """Dọn dẹp temp files và cache"""
    temp_patterns = ["temp_main_*.mp4", "temp_bg_loop_*.mp4", "temp_bg_cut_*.mp4"]
    for pattern in temp_patterns:
        for temp_file in glob(pattern):
            try:
                os.remove(temp_file)
                print(f"🗑️ Đã xóa: {temp_file}")
            except:
                pass

if __name__ == "__main__":
    cleanup_temp_files()
    render_all_gpu_optimized() 