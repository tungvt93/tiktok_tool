# TikTok Video Processing Tool - GUI Version

Giao diện đồ họa hiện đại cho ứng dụng xử lý video TikTok với các tính năng nâng cao.

## Tính năng chính

### 1. Panel bên trái - Chọn video
- Hiển thị danh sách tất cả video trong folder `dongphuc`
- Checkbox "Select All" để chọn tất cả video
- Checkbox riêng lẻ cho từng video
- Nút "Refresh Videos" để cập nhật danh sách

### 2. Panel giữa - Cấu hình Effects
- **Opening Effects**: Chọn hiệu ứng mở đầu
  - None (không có hiệu ứng)
  - Slide Right to Left
  - Slide Left to Right  
  - Slide Top to Bottom
  - Slide Bottom to Top
  - Circle Expand
  - Circle Contract
  - Circle Rotate CW
  - Circle Rotate CCW
  - Fade In
  - Tùy chọn Random Effect
- **GIF Effects**: Chọn hiệu ứng GIF overlay
  - Hiển thị tất cả file GIF trong folder `effects`
  - Chọn GIF cụ thể hoặc Random GIF
- **Duration**: Điều chỉnh thời gian hiệu ứng (giây)
- **Preview Effects**: Xem trước cấu hình hiệu ứng

### 3. Panel bên phải - Rendering Queue & Progress
- **Control Buttons**: Start, Stop, Pause/Resume
- **Progress Bars**: 
  - Overall Progress (tiến độ tổng thể)
  - Current Video Progress (tiến độ video hiện tại)
- **Rendering Queue**: Danh sách video đang render với trạng thái
- **Log**: Hiển thị log chi tiết quá trình xử lý

## Cài đặt

### Yêu cầu hệ thống
- Python 3.7+
- FFmpeg (đã cài đặt và có trong PATH)
- Các thư viện Python cần thiết

### Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### Cấu trúc thư mục
```
tiktok_tool/
├── dongphuc/          # Video input
├── video_chia_2/      # Background videos  
├── effects/           # GIF effects
├── output/            # Video output
├── gui_app.py         # GUI application
├── main.py            # Core processing logic
└── requirements.txt   # Dependencies
```

## Sử dụng

### Khởi chạy GUI
```bash
python gui_app.py
```

### Hướng dẫn sử dụng

1. **Chọn video**: 
   - Sử dụng panel bên trái để chọn video cần xử lý
   - Có thể chọn tất cả hoặc từng video riêng lẻ

2. **Cấu hình effects**:
   - Chọn opening effect từ danh sách hoặc bật random
   - Chọn GIF effect từ folder effects hoặc bật random
   - Điều chỉnh thời gian hiệu ứng
   - Sử dụng "Preview Effects" để xem trước

3. **Bắt đầu render**:
   - Nhấn "Start Rendering" để bắt đầu
   - Theo dõi tiến độ qua progress bars
   - Sử dụng Stop/Pause để điều khiển quá trình
   - Xem log để theo dõi chi tiết

### Tính năng nâng cao

- **Multi-threading**: Xử lý đa luồng để không block GUI
- **Real-time Progress**: Cập nhật tiến độ thời gian thực
- **Error Handling**: Xử lý lỗi và hiển thị thông báo
- **Modern UI**: Giao diện tối với màu sắc hiện đại
- **Logging**: Ghi log chi tiết quá trình xử lý

## Troubleshooting

### Lỗi thường gặp

1. **FFmpeg not found**:
   - Đảm bảo FFmpeg đã được cài đặt và có trong PATH
   - Kiểm tra bằng lệnh: `ffmpeg -version`

2. **Missing folders**:
   - Tạo các folder cần thiết: `dongphuc`, `video_chia_2`, `effects`, `output`

3. **Permission errors**:
   - Đảm bảo có quyền ghi vào folder output
   - Chạy với quyền admin nếu cần

4. **Memory issues**:
   - Giảm số lượng video xử lý đồng thời
   - Đóng các ứng dụng khác để giải phóng RAM

### Performance Tips

- Sử dụng SSD để tăng tốc độ đọc/ghi
- Đóng các ứng dụng không cần thiết
- Giảm độ phân giải video nếu cần
- Sử dụng preset "ultrafast" trong FFmpeg

## Tùy chỉnh

### Thay đổi cấu hình
Chỉnh sửa file `main.py` để thay đổi:
- Output dimensions
- Frame rate
- Quality settings
- Speed multiplier

### Thêm effects mới
1. Thêm effect type vào `EffectType` enum
2. Implement logic xử lý trong `OpeningEffectProcessor`
3. Cập nhật GUI để hiển thị effect mới

## Hỗ trợ

Nếu gặp vấn đề, vui lòng:
1. Kiểm tra log trong GUI
2. Đảm bảo cấu trúc thư mục đúng
3. Kiểm tra FFmpeg installation
4. Xem troubleshooting section

## License

MIT License - Xem file LICENSE để biết thêm chi tiết. 