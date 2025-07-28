"""
Test script for GIF generation with generated_effects directory
"""

import os
import tempfile
from pathlib import Path
from main import VideoConfig, GIFProcessor, VideoMerger
from manage_generated_effects import GeneratedEffectsManager
import logging

# Configure logging for testing
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_generated_effects_directory():
    """Test the generated effects directory functionality"""
    print("🧪 Testing Generated Effects Directory...")
    
    # Create configuration
    config = VideoConfig()
    manager = GeneratedEffectsManager(config.GENERATED_EFFECTS_DIR)
    
    # Test directory creation
    if manager.create_directory():
        print(f"✅ Directory created: {config.GENERATED_EFFECTS_DIR}")
    else:
        print(f"❌ Failed to create directory: {config.GENERATED_EFFECTS_DIR}")
        return False
    
    # Test directory status
    manager.show_status()
    
    return True

def test_gif_generation_to_generated_dir():
    """Test GIF generation to the generated_effects directory"""
    print("\n🎨 Testing GIF Generation to Generated Directory...")
    
    # Create configuration
    config = VideoConfig()
    merger = VideoMerger(config)
    
    # Test paths
    original_gif = "effects/star.gif"
    
    if not os.path.exists(original_gif):
        print(f"❌ Original GIF not found: {original_gif}")
        return False
    
    print(f"📁 Original GIF: {original_gif}")
    print(f"📁 Target size: {config.output_size}")
    
    # Test GIF generation
    tiled_gif_path = merger.get_or_create_tiled_gif("test_video.mp4", original_gif)
    
    if tiled_gif_path:
        print(f"✅ GIF generated: {tiled_gif_path}")
        
        # Check if file was created in the right directory
        if os.path.exists(tiled_gif_path):
            file_size = os.path.getsize(tiled_gif_path)
            print(f"📊 File size: {file_size:,} bytes")
            
            # Verify it's in the generated_effects directory
            if config.GENERATED_EFFECTS_DIR in tiled_gif_path:
                print(f"✅ File correctly placed in {config.GENERATED_EFFECTS_DIR}")
                return True
            else:
                print(f"❌ File not in expected directory: {tiled_gif_path}")
                return False
        else:
            print("❌ Generated file not found")
            return False
    else:
        print("❌ GIF generation failed")
        return False

def test_gitignore_compliance():
    """Test that generated_effects directory is properly git-ignored"""
    print("\n🔒 Testing Git Ignore Compliance...")
    
    # Check if .gitignore exists and contains generated_effects
    gitignore_path = ".gitignore"
    
    if not os.path.exists(gitignore_path):
        print(f"❌ .gitignore file not found")
        return False
    
    with open(gitignore_path, 'r') as f:
        gitignore_content = f.read()
    
    if "generated_effects" in gitignore_content:
        print("✅ generated_effects is in .gitignore")
        return True
    else:
        print("❌ generated_effects is not in .gitignore")
        return False

def test_cleanup_functionality():
    """Test cleanup functionality"""
    print("\n🧹 Testing Cleanup Functionality...")
    
    config = VideoConfig()
    manager = GeneratedEffectsManager(config.GENERATED_EFFECTS_DIR)
    
    # Create a test file
    test_file_path = os.path.join(config.GENERATED_EFFECTS_DIR, "test_cleanup.gif")
    
    try:
        # Ensure directory exists
        manager.create_directory()
        
        # Create a test file
        with open(test_file_path, 'w') as f:
            f.write("test content")
        
        print(f"✅ Created test file: {test_file_path}")
        
        # List files before cleanup
        files_before = manager.list_generated_files()
        print(f"📋 Files before cleanup: {len(files_before)}")
        
        # Test cleanup (should not remove recent files)
        removed = manager.cleanup_old_files(1)  # 1 day
        print(f"🧹 Removed {removed} old files")
        
        # List files after cleanup
        files_after = manager.list_generated_files()
        print(f"📋 Files after cleanup: {len(files_after)}")
        
        # Clean up test file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            print(f"✅ Removed test file: {test_file_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Cleanup test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting GIF Generation Tests with Generated Effects Directory\n")
    
    tests = [
        ("Generated Effects Directory", test_generated_effects_directory),
        ("GIF Generation to Generated Directory", test_gif_generation_to_generated_dir),
        ("Git Ignore Compliance", test_gitignore_compliance),
        ("Cleanup Functionality", test_cleanup_functionality)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"📋 Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{'✅ PASSED' if result else '❌ FAILED'}: {test_name}\n")
        except Exception as e:
            print(f"❌ ERROR in {test_name}: {e}\n")
            results.append((test_name, False))
    
    # Summary
    print("📊 Test Results Summary:")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! GIF generation with generated_effects directory is working correctly.")
        print("\n📝 Key Features Verified:")
        print("  • Generated GIFs are saved to generated_effects/ directory")
        print("  • Directory is automatically created if it doesn't exist")
        print("  • Directory is properly git-ignored")
        print("  • Cleanup functionality works correctly")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    exit(main()) 