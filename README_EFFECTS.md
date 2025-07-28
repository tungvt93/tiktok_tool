# TikTok Video Processing Tool - Opening Effects

## Tổng quan

Tool này đã được nâng cấp với các hiệu ứng mở đầu video mới, cho phép bạn tạo các video TikTok với hiệu ứng chuyển cảnh ấn tượng ngay từ đầu.

## Các hiệu ứng có sẵn

### 1. Hiệu ứng Slide (Trượt)
- **Slide từ phải sang trái**: Video xuất hiện từ bên phải và trượt sang trái
- **Slide từ trái sang phải**: Video xuất hiện từ bên trái và trượt sang phải  
- **Slide từ trên xuống**: Video xuất hiện từ trên và trượt xuống dưới
- **Slide từ dưới lên**: Video xuất hiện từ dưới và trượt lên trên

### 2. Hiệu ứng Circle (Hình tròn)
- **Circle Expand**: Hình tròn mở rộng từ tâm để hiển thị video
- **Circle Contract**: Hình tròn thu nhỏ về tâm để hiển thị video
- **Circle Rotate CW**: Hình tròn quay theo chiều kim đồng hồ để hiển thị video
- **Circle Rotate CCW**: Hình tròn quay ngược chiều kim đồng hồ để hiển thị video

### 3. Hiệu ứng Fade
- **Fade In**: Video hiển thị dần dần từ màn hình đen

## Cách sử dụng

### Chạy tool
```bash
python main.py
```

### Lựa chọn hiệu ứng
Khi chạy tool, bạn sẽ thấy menu như sau:

```
=== TIKTOK VIDEO PROCESSING TOOL ===
Available opening effects:
0. None (no effect)
1. Slide from right to left
2. Slide from left to right
3. Slide from top to bottom
4. Slide from bottom to top
5. Circle expand from center
6. Circle contract to center
7. Circle rotate clockwise
8. Circle rotate counter-clockwise
9. Fade in

Select opening effect (0-9):
```

### Cấu hình thời gian hiệu ứng
Sau khi chọn hiệu ứng, bạn có thể cấu hình thời gian hiệu ứng:

```
Enter effect duration in seconds (default 2.0):
```

### Lựa chọn GIF overlay
Bạn cũng có thể chọn có sử dụng hiệu ứng GIF overlay hay không:

```
Add GIF overlay effects? (y/n, default y):
```

## Cấu trúc thư mục

```
tiktok_tool/
├── dongphuc/          # Video đầu vào
├── video_chia_2/      # Video background
├── effects/           # GIF effects
├── generated_effects/ # GIF effects được tạo tự động
├── output/           # Video đầu ra
└── main.py           # File chính
```

## Yêu cầu hệ thống

- Python 3.7+
- FFmpeg (phải được cài đặt và có trong PATH)
- Các thư viện Python: PIL, numpy

## Cài đặt dependencies

```bash
pip install Pillow numpy
```

## Lưu ý kỹ thuật

### Hiệu suất
- Các hiệu ứng được xử lý bằng FFmpeg filters để đảm bảo hiệu suất tốt
- Video được xử lý song song để tăng tốc độ

### Chất lượng video
- Sử dụng preset "ultrafast" để tối ưu tốc độ xử lý
- CRF value mặc định là 23 (cân bằng giữa chất lượng và kích thước file)

### Tùy chỉnh
Bạn có thể tùy chỉnh các thông số trong class `VideoConfig`:

```python
@dataclass
class VideoConfig:
    OUTPUT_WIDTH: int = 1080
    OUTPUT_HEIGHT: int = 1080
    OPENING_DURATION: float = 2.0
    # ... các thông số khác
```

## Ví dụ sử dụng

### Ví dụ 1: Hiệu ứng slide từ phải sang trái
1. Chạy `python main.py`
2. Chọn option `1`
3. Nhập thời gian hiệu ứng `2.0`
4. Chọn `y` cho GIF overlay
5. Đợi quá trình xử lý hoàn tất

### Ví dụ 2: Hiệu ứng circle expand
1. Chạy `python main.py`
2. Chọn option `5`
3. Nhập thời gian hiệu ứng `3.0`
4. Chọn `n` cho GIF overlay
5. Đợi quá trình xử lý hoàn tất

## Xử lý lỗi

### Lỗi FFmpeg
Nếu gặp lỗi FFmpeg, hãy đảm bảo:
- FFmpeg đã được cài đặt đúng cách
- FFmpeg có trong PATH của hệ thống
- Có đủ quyền truy cập vào các thư mục

### Lỗi memory
Nếu gặp lỗi memory khi xử lý video lớn:
- Giảm số lượng process song song
- Giảm chất lượng video (tăng CRF value)
- Xử lý từng video một thay vì song song

## Hỗ trợ

Nếu gặp vấn đề, hãy kiểm tra:
1. Log output để xem lỗi chi tiết
2. Đảm bảo các file video đầu vào hợp lệ
3. Kiểm tra quyền truy cập thư mục
4. Đảm bảo FFmpeg hoạt động bình thường 