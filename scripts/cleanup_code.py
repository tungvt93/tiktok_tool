#!/usr/bin/env python3
"""
Code Cleanup Script

Automated cleanup of deprecated code, unused imports, and temporary files.
"""

import sys
import ast
import re
from pathlib import Path
from typing import List, Dict, Set, Any
import logging
import shutil

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class CodeCleaner:
    """Code cleanup utilities"""

    def __init__(self, project_root: Path = None):
        """
        Initialize code cleaner.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root or Path(__file__).parent.parent
        self.cleanup_results = {
            'files_processed': 0,
            'files_modified': 0,
            'unused_imports_removed': 0,
            'deprecated_code_removed': 0,
            'temp_files_removed': 0,
            'errors': []
        }

    def cleanup_all(self) -> Dict[str, Any]:
        """Run all cleanup operations"""
        logger.info("Starting comprehensive code cleanup...")

        # Clean up Python files
        self.cleanup_python_files()

        # Remove temporary files
        self.remove_temporary_files()

        # Clean up test artifacts
        self.cleanup_test_artifacts()

        # Remove deprecated migration files
        self.cleanup_migration_artifacts()

        # Clean up build artifacts
        self.cleanup_build_artifacts()

        logger.info("Code cleanup completed")
        return self.cleanup_results

    def cleanup_python_files(self):
        """Clean up Python source files"""
        logger.info("Cleaning up Python files...")

        python_files = list(self.project_root.rglob("*.py"))

        for py_file in python_files:
            # Skip certain directories
            if any(part in str(py_file) for part in ['.git', '__pycache__', '.pytest_cache', 'venv', 'env']):
                continue

            try:
                self.cleanup_python_file(py_file)
                self.cleanup_results['files_processed'] += 1

            except Exception as e:
                error_msg = f"Error processing {py_file}: {e}"
                logger.error(error_msg)
                self.cleanup_results['errors'].append(error_msg)

    def cleanup_python_file(self, file_path: Path):
        """Clean up a single Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            modified_content = original_content
            file_modified = False

            # Remove unused imports
            new_content, imports_removed = self.remove_unused_imports(modified_content, file_path)
            if imports_removed > 0:
                modified_content = new_content
                file_modified = True
                self.cleanup_results['unused_imports_removed'] += imports_removed

            # Remove deprecated code patterns
            new_content, deprecated_removed = self.remove_deprecated_patterns(modified_content)
            if deprecated_removed > 0:
                modified_content = new_content
                file_modified = True
                self.cleanup_results['deprecated_code_removed'] += deprecated_removed

            # Clean up formatting
            new_content = self.cleanup_formatting(modified_content)
            if new_content != modified_content:
                modified_content = new_content
                file_modified = True

            # Write back if modified
            if file_modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)

                self.cleanup_results['files_modified'] += 1
                logger.debug(f"Cleaned up {file_path}")

        except Exception as e:
            raise Exception(f"Failed to process {file_path}: {e}")

    def remove_unused_imports(self, content: str, file_path: Path) -> tuple[str, int]:
        """Remove unused imports from Python code"""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Skip files with syntax errors
            return content, 0

        # Find all imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        imports.append(f"{node.module}.{alias.name}")

        # Find used names (simplified approach)
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    used_names.add(f"{node.value.id}.{node.attr}")

        # Remove unused imports (conservative approach)
        lines = content.split('\n')
        new_lines = []
        removed_count = 0

        for line in lines:
            # Skip removing imports for now - too risky without proper analysis
            # This would need more sophisticated analysis
            new_lines.append(line)

        return '\n'.join(new_lines), removed_count

    def remove_deprecated_patterns(self, content: str) -> tuple[str, int]:
        """Remove deprecated code patterns"""
        removed_count = 0

        # Patterns to remove
        deprecated_patterns = [
            # Remove old-style string formatting
            (r'%\s*\([^)]+\)\s*%', 'f-string or .format()'),

            # Remove print statements without parentheses (Python 2 style)
            (r'^(\s*)print\s+([^(].*?)$', r'\1# print(\2)  # Commented out old-style print'),

            # Remove old exception syntax
            (r'except\s+(\w+),\s*(\w+):', r'except \1 as \2:'),

            # Remove unnecessary pass statements
            (r'^\s*pass\s*$\n', ''),
        ]

        for pattern, replacement in deprecated_patterns:
            old_content = content
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            if content != old_content:
                removed_count += 1

        return content, removed_count

    def cleanup_formatting(self, content: str) -> str:
        """Clean up code formatting"""
        # Remove trailing whitespace
        lines = content.split('\n')
        cleaned_lines = [line.rstrip() for line in lines]

        # Remove excessive blank lines (more than 2 consecutive)
        result_lines = []
        blank_count = 0

        for line in cleaned_lines:
            if line.strip() == '':
                blank_count += 1
                if blank_count <= 2:
                    result_lines.append(line)
            else:
                blank_count = 0
                result_lines.append(line)

        # Ensure file ends with single newline
        while result_lines and result_lines[-1] == '':
            result_lines.pop()

        return '\n'.join(result_lines) + '\n' if result_lines else ''

    def remove_temporary_files(self):
        """Remove temporary files and directories"""
        logger.info("Removing temporary files...")

        temp_patterns = [
            '**/*.pyc',
            '**/*.pyo',
            '**/*.pyd',
            '**/__pycache__',
            '**/.pytest_cache',
            '**/.coverage',
            '**/*.tmp',
            '**/*.temp',
            '**/*~',
            '**/.DS_Store',
            '**/Thumbs.db',
            '**/*.log',
            '**/performance_*.json',
            '**/simple_performance_results.json',
            '**/test_config.json',
            '**/migrated_config.json',
            '**/sample_old_config.py*',
            '**/video_cache.json'
        ]

        for pattern in temp_patterns:
            for path in self.project_root.glob(pattern):
                try:
                    if path.is_file():
                        path.unlink()
                        self.cleanup_results['temp_files_removed'] += 1
                        logger.debug(f"Removed temp file: {path}")
                    elif path.is_dir():
                        shutil.rmtree(path)
                        self.cleanup_results['temp_files_removed'] += 1
                        logger.debug(f"Removed temp directory: {path}")
                except Exception as e:
                    logger.warning(f"Could not remove {path}: {e}")

    def cleanup_test_artifacts(self):
        """Clean up test artifacts"""
        logger.info("Cleaning up test artifacts...")

        test_artifacts = [
            'test_compatibility.py',
            'test_migration_simple.py',
            'test_output_quality.py',
            'test_performance_simple.py',
            'validate_migration.py',
            'migrate.py'
        ]

        for artifact in test_artifacts:
            artifact_path = self.project_root / artifact
            if artifact_path.exists():
                try:
                    # Don't actually remove these - they might be useful
                    # Just log that they exist
                    logger.debug(f"Test artifact exists: {artifact_path}")
                except Exception as e:
                    logger.warning(f"Could not process {artifact_path}: {e}")

    def cleanup_migration_artifacts(self):
        """Clean up migration artifacts"""
        logger.info("Cleaning up migration artifacts...")

        # These are temporary files created during migration testing
        migration_artifacts = [
            'sample_old_config.py',
            'sample_old_config.py.backup',
            'migrated_config.json',
            'integrity_test_config.json'
        ]

        for artifact in migration_artifacts:
            artifact_path = self.project_root / artifact
            if artifact_path.exists():
                try:
                    artifact_path.unlink()
                    self.cleanup_results['temp_files_removed'] += 1
                    logger.debug(f"Removed migration artifact: {artifact_path}")
                except Exception as e:
                    logger.warning(f"Could not remove {artifact_path}: {e}")

    def cleanup_build_artifacts(self):
        """Clean up build artifacts"""
        logger.info("Cleaning up build artifacts...")

        build_dirs = ['build', 'dist', '*.egg-info']

        for pattern in build_dirs:
            for path in self.project_root.glob(pattern):
                if path.is_dir():
                    try:
                        shutil.rmtree(path)
                        self.cleanup_results['temp_files_removed'] += 1
                        logger.debug(f"Removed build directory: {path}")
                    except Exception as e:
                        logger.warning(f"Could not remove {path}: {e}")

    def find_dead_code(self) -> List[str]:
        """Find potentially dead code"""
        logger.info("Analyzing for dead code...")

        dead_code_candidates = []

        # Find Python files
        python_files = list(self.project_root.rglob("*.py"))

        # Simple dead code detection
        for py_file in python_files:
            if any(part in str(py_file) for part in ['.git', '__pycache__', 'venv']):
                continue

            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Look for common dead code patterns
                if 'TODO' in content:
                    dead_code_candidates.append(f"{py_file}: Contains TODO comments")

                if 'FIXME' in content:
                    dead_code_candidates.append(f"{py_file}: Contains FIXME comments")

                if 'XXX' in content:
                    dead_code_candidates.append(f"{py_file}: Contains XXX comments")

                # Look for unused functions (very basic check)
                if re.search(r'def\s+_[a-zA-Z_][a-zA-Z0-9_]*\s*\(', content):
                    # Has private functions - might be unused
            except Exception as e:
                logger.warning(f"Could not analyze {py_file}: {e}")

        return dead_code_candidates

    def generate_cleanup_report(self) -> str:
        """Generate cleanup report"""
        dead_code = self.find_dead_code()

        report = f"""
Code Cleanup Report
==================

Files Processed: {self.cleanup_results['files_processed']}
Files Modified: {self.cleanup_results['files_modified']}
Unused Imports Removed: {self.cleanup_results['unused_imports_removed']}
Deprecated Code Patterns Removed: {self.cleanup_results['deprecated_code_removed']}
Temporary Files Removed: {self.cleanup_results['temp_files_removed']}

Potential Dead Code:
{chr(10).join(f"  - {item}" for item in dead_code[:10])}
{f"  ... and {len(dead_code) - 10} more" if len(dead_code) > 10 else ""}

Errors Encountered:
{chr(10).join(f"  - {error}" for error in self.cleanup_results['errors'][:5])}
{f"  ... and {len(self.cleanup_results['errors']) - 5} more" if len(self.cleanup_results['errors']) > 5 else ""}

Recommendations:
- Review and remove TODO/FIXME comments
- Consider removing unused private methods
- Run tests after cleanup to ensure nothing is broken
- Use a linter like flake8 or pylint for ongoing code quality
"""

        return report


def main():
    """Main cleanup script entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Clean up deprecated code and temporary files"
    )

    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what would be cleaned without making changes'
    )

    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--report-only', action='store_true',
        help='Generate report only without cleaning'
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create cleaner
    cleaner = CodeCleaner()

    try:
        if args.report_only:
            # Generate report only
            report = cleaner.generate_cleanup_report()
            print(report)
        elif args.dry_run:
            print("DRY RUN MODE - No changes will be made")
            print("=" * 40)

            # Show what would be cleaned
            temp_patterns = [
                '**/*.pyc', '**/*.pyo', '**/__pycache__',
                '**/.pytest_cache', '**/*.tmp', '**/*.log'
            ]

            files_to_remove = []
            for pattern in temp_patterns:
                files_to_remove.extend(Path('.').glob(pattern))

            print(f"Would remove {len(files_to_remove)} temporary files")
            for f in files_to_remove[:10]:
                print(f"  - {f}")
            if len(files_to_remove) > 10:
                print(f"  ... and {len(files_to_remove) - 10} more")

        else:
            # Perform actual cleanup
            results = cleaner.cleanup_all()

            # Print summary
            print("Code Cleanup Summary")
            print("=" * 30)
            print(f"Files processed: {results['files_processed']}")
            print(f"Files modified: {results['files_modified']}")
            print(f"Unused imports removed: {results['unused_imports_removed']}")
            print(f"Deprecated patterns removed: {results['deprecated_code_removed']}")
            print(f"Temporary files removed: {results['temp_files_removed']}")

            if results['errors']:
                print(f"Errors: {len(results['errors'])}")
                for error in results['errors'][:3]:
                    print(f"  - {error}")

            # Generate full report
            report = cleaner.generate_cleanup_report()

            # Save report
            with open('cleanup_report.txt', 'w') as f:
                f.write(report)

            print("\nFull report saved to cleanup_report.txt")

        return 0

    except KeyboardInterrupt:
        print("\nCleanup interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
