#!/usr/bin/env python3
"""
Run video processing with config file
"""

import json
import os
from main import VideoConfig, EffectType, VideoMerger

def load_config():
    """Load configuration from config.json"""
    try:
        with open('config.json', 'r') as f:
            config_data = json.load(f)
        return config_data
    except FileNotFoundError:
        print("config.json not found, using defaults")
        return {
            "opening_effect": 6,
            "effect_duration": 2.0,
            "add_gif_effects": True
        }

def main():
    """Run with config file"""
    # Load config
    config_data = load_config()
    
    # Effect mapping
    effect_map = {
        0: EffectType.NONE,
        1: EffectType.SLIDE_RIGHT_TO_LEFT,
        2: EffectType.SLIDE_LEFT_TO_RIGHT,
        3: EffectType.SLIDE_TOP_TO_BOTTOM,
        4: EffectType.SLIDE_BOTTOM_TO_TOP,
        5: EffectType.CIRCLE_EXPAND,
        6: EffectType.CIRCLE_CONTRACT,
        7: EffectType.CIRCLE_ROTATE_CW,
        8: EffectType.CIRCLE_ROTATE_CCW,
        9: EffectType.FADE_IN
    }
    
    # Create config
    config = VideoConfig()
    config.OPENING_EFFECT = effect_map.get(config_data["opening_effect"], EffectType.NONE)
    config.OPENING_DURATION = config_data["effect_duration"]
    add_gif_effects = config_data["add_gif_effects"]
    
    print("=== TIKTOK VIDEO PROCESSING TOOL ===")
    print(f"Selected effect: {config.OPENING_EFFECT.value}")
    print(f"Effect duration: {config.OPENING_DURATION} seconds")
    print(f"GIF effects: {'Yes' if add_gif_effects else 'No'}")
    
    # Check directories
    if not os.path.exists(config.INPUT_DIR):
        print(f"Error: Input directory '{config.INPUT_DIR}' not found!")
        return 1
    
    if not os.path.exists(config.BACKGROUND_DIR):
        print(f"Error: Background directory '{config.BACKGROUND_DIR}' not found!")
        return 1
    
    # Process videos
    merger = VideoMerger(config)
    merger.cleanup_temp_files()
    
    print("\nStarting video processing...")
    success = merger.render_all_videos(add_effects=add_gif_effects)
    
    if success:
        print("\n✅ All videos processed successfully!")
    else:
        print("\n❌ Some videos failed to process")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 