import os
import subprocess
from glob import glob
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
import tempfile

def run_ffmpeg(cmd, silent=False):
    if not silent:
        print("▶️ Running:", ' '.join(cmd))
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL if silent else None)

def get_video_duration(path):
    """Cache video duration để tránh gọi ffprobe nhiều lần"""
    if not hasattr(get_video_duration, 'cache'):
        get_video_duration.cache = {}
    
    if path in get_video_duration.cache:
        return get_video_duration.cache[path]
    
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
         "default=noprint_wrappers=1:nokey=1", path],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    duration = float(result.stdout.strip())
    get_video_duration.cache[path] = duration
    return duration

def create_background_loop(bg_video, target_duration, temp_dir):
    """Tạo video nền loop với thời lượng mong muốn"""
    bg_duration = get_video_duration(bg_video)
    loop_count = int(target_duration // bg_duration) + 2  # +2 để đảm bảo đủ
    
    # Sử dụng filter loop thay vì concat nhiều input
    loop_filter = f"loop=loop={loop_count}:size=1:start=0"
    temp_bg_loop = os.path.join(temp_dir, "bg_loop.mp4")
    
    run_ffmpeg([
        "ffmpeg", "-y", "-i", bg_video,
        "-filter:v", loop_filter,
        "-t", str(target_duration),
        "-c:v", "libx264", "-preset", "ultrafast",
        "-an", temp_bg_loop
    ], silent=True)
    
    return temp_bg_loop

def render_single_optimized(main_video, bg_video, index):
    video_name = os.path.splitext(os.path.basename(main_video))[0]
    output_file = f"output/{video_name}.mp4"

    # ⛔ Nếu file đã tồn tại → bỏ qua
    if os.path.exists(output_file):
        print(f"⏩ Bỏ qua: {output_file} đã tồn tại.")
        return

    # Tạo temp directory cho mỗi process
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_main = os.path.join(temp_dir, "main_speed.mp4")
        temp_bg_loop = os.path.join(temp_dir, "bg_loop.mp4")
        
        # Bước 1: Tăng tốc video chính và lấy duration
        run_ffmpeg([
            "ffmpeg", "-y", "-i", main_video, 
            "-filter_complex", "[0:v]setpts=PTS/1.3[v];[0:a]atempo=1.3[a]",
            "-map", "[v]", "-map", "[a]", 
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac", "-threads", "0",
            temp_main
        ], silent=True)
        
        main_duration = get_video_duration(temp_main)
        
        # Bước 2: Tạo background loop
        temp_bg_loop = create_background_loop(bg_video, main_duration, temp_dir)
        
        # Bước 3: Render cuối cùng - tất cả trong 1 lần gọi ffmpeg
        run_ffmpeg([
            "ffmpeg", "-y",
            "-i", temp_main,
            "-i", temp_bg_loop,
            "-filter_complex",
            "[0:v]scale=540:1080[left]; [1:v]scale=540:1080[right]; [left][right]hstack=inputs=2[v]",
            "-map", "[v]", "-map", "0:a",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-c:a", "aac",
            "-shortest",
            "-threads", "0",
            output_file
        ])

    print(f"✅ Render xong: {output_file}")

def preprocess_backgrounds(background_videos):
    """Tiền xử lý background videos để cache duration"""
    print("🔄 Đang cache thông tin background videos...")
    for bg_video in background_videos:
        get_video_duration(bg_video)
    print(f"✅ Đã cache {len(background_videos)} background videos")

def render_all_optimized():
    os.makedirs("output", exist_ok=True)
    download_videos = sorted(glob("dongphuc/*.mp4"))
    background_videos = sorted(glob("video_chia_2/*.mp4"))

    if not download_videos or not background_videos:
        print("❌ Thiếu video trong dongphuc/ hoặc video_chia_2/")
        return

    # Tiền xử lý để cache duration
    preprocess_backgrounds(background_videos)
    
    # Sử dụng max_workers dựa trên CPU cores
    max_workers = min(os.cpu_count(), len(download_videos))
    print(f"🚀 Sử dụng {max_workers} processes để render")
    
    # Submit tất cả tasks và đợi hoàn thành
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for idx, main_video in enumerate(download_videos):
            bg_video = random.choice(background_videos)
            print(f"📋 Queue: {os.path.basename(main_video)} + {os.path.basename(bg_video)}")
            future = executor.submit(render_single_optimized, main_video, bg_video, idx)
            futures.append(future)
        
        # Đợi tất cả hoàn thành
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"❌ Lỗi: {e}")

def cleanup_temp_files():
    """Dọn dẹp temp files cũ nếu có"""
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
    render_all_optimized() 