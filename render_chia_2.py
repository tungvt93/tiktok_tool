import os
import subprocess
from glob import glob
import random
from concurrent.futures import ProcessPoolExecutor

def run_ffmpeg(cmd):
    print("▶️ Running:", ' '.join(cmd))
    subprocess.run(cmd, check=True)

def get_video_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
         "default=noprint_wrappers=1:nokey=1", path],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return float(result.stdout.decode().strip())

def render_single(main_video, bg_video, index):
    video_name = os.path.splitext(os.path.basename(main_video))[0]
    output_file = f"output/{video_name}.mp4"

    # ⛔ Nếu file đã tồn tại → bỏ qua
    if os.path.exists(output_file):
        print(f"⏩ Bỏ qua: {output_file} đã tồn tại.")
        return

    temp1 = f"temp_main_{index}.mp4"
    temp2 = f"temp_bg_loop_{index}.mp4"
    temp3 = f"temp_bg_cut_{index}.mp4"

    # Tăng tốc video chính
    run_ffmpeg([
        "ffmpeg", "-y", "-i", main_video, "-filter_complex",
        "[0:v]setpts=PTS/1.3[v];[0:a]atempo=1.3[a]",
        "-map", "[v]", "-map", "[a]", "-threads", "1", temp1
    ])

    # Tính thời lượng cần thiết
    main_duration = get_video_duration(temp1)
    bg_duration = get_video_duration(bg_video)
    loop_count = int(main_duration // bg_duration) + 1

    inputs = []
    for _ in range(loop_count):
        inputs.extend(["-i", bg_video])

    # Nối video nền
    concat_filter = f"concat=n={loop_count}:v=1:a=0[outv]"
    run_ffmpeg([
        "ffmpeg", "-y", *inputs,
        "-filter_complex", concat_filter,
        "-map", "[outv]", "-an", temp2
    ])

    # Cắt nền bằng thời lượng chính
    run_ffmpeg([
        "ffmpeg", "-y", "-i", temp2, "-t", str(main_duration), "-c", "copy", temp3
    ])

    # Ghép video chính + nền bằng CPU
    run_ffmpeg([
        "ffmpeg", "-y",
        "-i", temp1,
        "-i", temp3,
        "-filter_complex",
        "[0:v]scale=540:1080[left]; [1:v]scale=540:1080[right]; [left][right]hstack=inputs=2[v]",
        "-map", "[v]", "-map", "0:a",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "aac",
        "-shortest", output_file
    ])

    print(f"✅ Render xong: {output_file}")

def render_all():
    os.makedirs("output", exist_ok=True)
    download_videos = sorted(glob("dongphuc/*.mp4"))
    background_videos = sorted(glob("video_chia_2/*.mp4"))

    if not download_videos or not background_videos:
        print("❌ Thiếu video trong downloads/ hoặc video_chia_2/")
        return

    with ProcessPoolExecutor() as executor:
        for idx, main_video in enumerate(download_videos):
            bg_video = random.choice(background_videos)
            print(f"\n🎬 Rendering {os.path.basename(main_video)} with background {os.path.basename(bg_video)}...")
            executor.submit(render_single, main_video, bg_video, idx)

if __name__ == "__main__":
    render_all()
