"""
Utility script to manage generated effects directory
"""

import os
import shutil
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeneratedEffectsManager:
    """Manages the generated effects directory"""

    def __init__(self, generated_dir: str = "generated_effects"):
        self.generated_dir = generated_dir

    def create_directory(self):
        """Create the generated effects directory if it doesn't exist"""
        try:
            os.makedirs(self.generated_dir, exist_ok=True)
            logger.info(f"Created/verified directory: {self.generated_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {self.generated_dir}: {e}")
            return False

    def list_generated_files(self):
        """List all files in the generated effects directory"""
        if not os.path.exists(self.generated_dir):
            logger.info(f"Directory {self.generated_dir} does not exist")
            return []

        files = []
        for file_path in Path(self.generated_dir).glob("*"):
            if file_path.is_file():
                files.append({
                    'name': file_path.name,
                    'size': file_path.stat().st_size,
                    'path': str(file_path)
                })

        return files

    def cleanup_old_files(self, days_old: int = 7):
        """Clean up files older than specified days"""
        import time
        from datetime import datetime, timedelta

        if not os.path.exists(self.generated_dir):
            logger.info(f"Directory {self.generated_dir} does not exist")
            return 0

        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        removed_count = 0

        for file_path in Path(self.generated_dir).glob("*"):
            if file_path.is_file():
                if file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        logger.info(f"Removed old file: {file_path.name}")
                        removed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to remove {file_path.name}: {e}")

        logger.info(f"Cleaned up {removed_count} old files")
        return removed_count

    def get_directory_size(self):
        """Get total size of generated effects directory"""
        if not os.path.exists(self.generated_dir):
            return 0

        total_size = 0
        for file_path in Path(self.generated_dir).rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size

        return total_size

    def format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0B"

        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1

        return f"{size_bytes:.1f}{size_names[i]}"

    def show_status(self):
        """Show status of generated effects directory"""
        print(f"\n📁 Generated Effects Directory Status")
        print("=" * 50)

        if not os.path.exists(self.generated_dir):
            print(f"❌ Directory does not exist: {self.generated_dir}")
            return

        files = self.list_generated_files()
        total_size = self.get_directory_size()

        print(f"📍 Location: {os.path.abspath(self.generated_dir)}")
        print(f"📊 Total files: {len(files)}")
        print(f"💾 Total size: {self.format_size(total_size)}")

        if files:
            print(f"\n📋 Files:")
            for file_info in files:
                print(f"  • {file_info['name']} ({self.format_size(file_info['size'])})")
        else:
            print(f"\n📋 No files found")

        print(f"\nℹ️  This directory is ignored by git (.gitignore)")

def main():
    """Main function for command line usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Manage generated effects directory")
    parser.add_argument("--list", action="store_true", help="List generated files")
    parser.add_argument("--cleanup", type=int, metavar="DAYS", help="Clean up files older than DAYS")
    parser.add_argument("--status", action="store_true", help="Show directory status")
    parser.add_argument("--create", action="store_true", help="Create directory if it doesn't exist")

    args = parser.parse_args()

    manager = GeneratedEffectsManager()

    if args.create:
        manager.create_directory()

    if args.status:
        manager.show_status()

    if args.list:
        files = manager.list_generated_files()
        if files:
            print(f"\n📋 Files in {manager.generated_dir}:")
            for file_info in files:
                print(f"  • {file_info['name']} ({manager.format_size(file_info['size'])})")
        else:
            print(f"\n📋 No files found in {manager.generated_dir}")

    if args.cleanup is not None:
        removed = manager.cleanup_old_files(args.cleanup)
        print(f"🧹 Removed {removed} files older than {args.cleanup} days")

    # If no arguments provided, show status
    if not any([args.list, args.cleanup, args.status, args.create]):
        manager.show_status()

if __name__ == "__main__":
    main()
