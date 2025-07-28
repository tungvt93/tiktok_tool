import os
from PIL import Image, ImageOps
import numpy as np

def create_tiled_gif(input_gif_path, output_gif_path, target_size=(1080, 1080)):
    """
    Tạo ảnh GIF lớn hơn bằng cách mirror và tile ảnh GIF ban đầu
    Phiên bản hoàn hảo với xử lý disposal method và transparency đúng cách
    
    Args:
        input_gif_path: Đường dẫn đến ảnh GIF ban đầu
        output_gif_path: Đường dẫn lưu ảnh GIF mới
        target_size: Kích thước mong muốn (width, height)
    """
    
    # Mở ảnh GIF ban đầu
    original_gif = Image.open(input_gif_path)
    
    # Lấy thông tin về ảnh
    print(f"Ảnh GIF ban đầu: {original_gif.size}")
    print(f"Kích thước mục tiêu: {target_size}")
    
    # Lấy thông tin transparency và background
    transparency_color = original_gif.info.get('transparency', None)
    background_color = original_gif.info.get('background', None)
    print(f"Màu transparency: {transparency_color}")
    print(f"Màu background: {background_color}")
    
    # Tạo danh sách các frame mới
    new_frames = []
    durations = []
    disposal_methods = []
    
    try:
        # Xử lý từng frame trong GIF
        frame_index = 0
        while True:
            # Đọc frame hiện tại
            original_gif.seek(frame_index)
            frame = original_gif.copy()
            
            # Lấy thông tin frame
            frame_duration = original_gif.info.get('duration', 100)
            disposal_method = original_gif.info.get('disposal', 2)  # 2 = clear background
            
            durations.append(frame_duration)
            disposal_methods.append(disposal_method)
            
            print(f"Frame {frame_index}: duration={frame_duration}, disposal={disposal_method}")
            
            # Lấy kích thước frame ban đầu
            frame_width, frame_height = frame.size
            
            # Tính số lần cần tile để đạt kích thước mục tiêu
            tiles_x = target_size[0] // frame_width + (1 if target_size[0] % frame_width != 0 else 0)
            tiles_y = target_size[1] // frame_height + (1 if target_size[1] % frame_height != 0 else 0)
            
            # Tạo ảnh mới với kích thước mục tiêu - LUÔN transparent
            new_frame = Image.new('RGBA', target_size, (0, 0, 0, 0))
            
            # Tile và mirror frame
            for y in range(tiles_y):
                for x in range(tiles_x):
                    # Tạo mirror cho frame
                    tile_frame = frame.copy()
                    
                    # Mirror logic - pattern đẹp hơn
                    if x % 2 == 1:  # Mirror theo chiều ngang
                        tile_frame = ImageOps.mirror(tile_frame)
                    
                    if y % 2 == 1:  # Mirror theo chiều dọc
                        tile_frame = ImageOps.flip(tile_frame)
                    
                    # Chuyển đổi sang RGBA và xử lý transparency
                    if tile_frame.mode != 'RGBA':
                        tile_frame = tile_frame.convert('RGBA')
                    
                    # Xử lý transparency
                    if transparency_color is not None and frame.mode == 'P':
                        # Lấy palette từ frame gốc
                        palette = frame.palette.palette
                        if transparency_color * 3 + 2 < len(palette):
                            trans_r = palette[transparency_color * 3]
                            trans_g = palette[transparency_color * 3 + 1]
                            trans_b = palette[transparency_color * 3 + 2]
                            
                            # Tạo mask cho các pixel có màu transparency
                            tile_data = np.array(tile_frame)
                            mask = (tile_data[:, :, 0] == trans_r) & \
                                   (tile_data[:, :, 1] == trans_g) & \
                                   (tile_data[:, :, 2] == trans_b)
                            
                            # Áp dụng transparency
                            tile_data[:, :, 3] = np.where(mask, 0, 255)
                            tile_frame = Image.fromarray(tile_data)
                    
                    # Tính vị trí để paste
                    paste_x = x * frame_width
                    paste_y = y * frame_height
                    
                    # Paste frame vào vị trí tương ứng
                    new_frame.paste(tile_frame, (paste_x, paste_y), tile_frame)
            
            # Thêm frame mới vào danh sách
            new_frames.append(new_frame)
            
            frame_index += 1
            
    except EOFError:
        # Đã đọc hết các frame
        pass
    
    # Lưu ảnh GIF mới với disposal method đúng
    if new_frames:
        print(f"Tạo thành công {len(new_frames)} frames")
        
        # Chuẩn bị thông tin lưu
        save_kwargs = {
            'save_all': True,
            'append_images': new_frames[1:],
            'duration': durations,
            'loop': 0,
            'optimize': True,
            'transparency': 0,  # Set transparency cho GIF
            'disposal': disposal_methods  # Set disposal method cho từng frame
        }
        
        # Lưu ảnh GIF mới
        new_frames[0].save(output_gif_path, **save_kwargs)
        
        print(f"Đã lưu ảnh GIF mới tại: {output_gif_path}")
        print(f"Kích thước mới: {new_frames[0].size}")
        print(f"Disposal methods: {disposal_methods}")
    else:
        print("Không thể tạo frames mới")

def main():
    # Đường dẫn file
    input_gif = "effects/star.gif"
    output_gif = "output/star_tiled_1080x1080.gif"
    
    # Tạo thư mục output nếu chưa có
    os.makedirs("output", exist_ok=True)
    
    # Kiểm tra file đầu vào
    if not os.path.exists(input_gif):
        print(f"Không tìm thấy file: {input_gif}")
        return
    
    # Tạo ảnh GIF mới
    create_tiled_gif(input_gif, output_gif, target_size=(1080, 1080))

if __name__ == "__main__":
    main()
