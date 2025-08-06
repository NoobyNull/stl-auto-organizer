#!/usr/bin/env python3
"""
STL Auto Organizer for Manyfold Application

This script organizes files based on their prefixes (text before the extension) into
folders matching their names. It's designed to work with 3D model collections for
the Manyfold application, which requires objects and supporting documentation to be
in the same folder with no other contents.

Key Features:
- Groups files with same prefix into folders
- Moves folders without 3D models to "Scrap" directory
- Supports dry-run mode for testing
- Runs in isolated Python virtual environment
- Preserves existing folder structures that match requirements

Author: Auto-generated for STL organization
"""

import os
import sys
import shutil
import argparse
import re
import subprocess
import venv
import json
import datetime
import hashlib
from pathlib import Path
from typing import List, Dict, Set, Tuple, Union, Optional
from collections import defaultdict

# Common 3D model file extensions (case-insensitive)
THREED_MODEL_EXTENSIONS = {
    '.stl',     # Stereolithography (most common for 3D printing)
    '.obj',     # Wavefront OBJ
    '.ply',     # Polygon File Format
    '.3mf',     # 3D Manufacturing Format
    '.amf',     # Additive Manufacturing File Format
    '.dae',     # Collada
    '.fbx',     # Autodesk FBX
    '.blend',   # Blender
    '.max',     # 3ds Max
    '.c4d',     # Cinema 4D
    '.ma',      # Maya ASCII
    '.mb',      # Maya Binary
    '.step',    # STEP
    '.stp',     # STEP
    '.iges',    # IGES
    '.igs',     # IGES
    '.x3d',     # X3D
    '.wrl',     # VRML
    '.3ds',     # 3D Studio
    '.lwo',     # LightWave
    '.off',     # Object File Format
    '.gcode',   # G-code (3D printer instructions)
}

# Files to ignore during processing
IGNORE_FILES = {
    'thumbs.db',
    'desktop.ini',
    '.ds_store',
    'datapackage.json'  # Appears to be metadata file
}

# Protected directories that should never be organized (OS/Application safety)
PROTECTED_DIRECTORIES = {
    'windows', 'system32', 'syswow64', 'program files', 'program files (x86)',
    'programdata', 'users', 'boot', 'recovery', '$recycle.bin', 'system volume information',
    'windows.old', 'perflogs', 'msocache', 'intel', 'amd', 'nvidia',
    'appdata', 'application data', 'local settings', 'cookies', 'recent',
    'sendto', 'start menu', 'templates', 'nethood', 'printhood',
    'my documents', 'favorites', 'desktop', 'tmp', 'temp',
    'bin', 'sbin', 'usr', 'var', 'etc', 'lib', 'lib64', 'opt', 'root',
    'home', 'proc', 'sys', 'dev', 'mnt', 'media', 'lost+found',
    'applications', 'library', 'system', 'volumes', 'cores',
    '.git', '.svn', '.hg', 'node_modules', '__pycache__', '.vscode', '.idea'
}

# Organization instruction file name
INSTRUCTION_FILE = '.stl_organize_instructions.json'

class FileOrganizer:
    """Main class for organizing files according to Manyfold requirements."""
    
    def __init__(self, target_directory: Union[str, Path], dry_run: bool = False, commit_mode: bool = False, trust_mode: bool = False):
        """
        Initialize the file organizer.
        
        Args:
            target_directory: Path to the directory to organize
            dry_run: If True, only show what would be done without making changes
            commit_mode: If True, try to execute from instruction file
            trust_mode: If True, skip safety prompts
        """
        self.target_directory = Path(target_directory).resolve()
        self.dry_run = dry_run
        self.commit_mode = commit_mode
        self.trust_mode = trust_mode
        self.scrap_directory = self.target_directory / "Scrap"
        self.instruction_file_path = self.target_directory / INSTRUCTION_FILE
        self.moved_files = 0
        self.created_folders = 0
        self.moved_to_scrap = 0
        self.organization_plan = None
        
        print(f"Initializing File Organizer")
        print(f"Target Directory: {self.target_directory}")
        print(f"Scrap Directory: {self.scrap_directory}")
        print(f"Dry Run Mode: {'ON' if self.dry_run else 'OFF'}")
        print(f"Commit Mode: {'ON' if self.commit_mode else 'OFF'}")
        print(f"Trust Mode: {'ON' if self.trust_mode else 'OFF'}")
        print("-" * 60)
    
    def is_3d_model_file(self, file_path: Path) -> bool:
        """
        Check if a file is a 3D model based on its extension.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if the file is a 3D model, False otherwise
        """
        return file_path.suffix.lower() in THREED_MODEL_EXTENSIONS
    
    def should_ignore_file(self, file_path: Path) -> bool:
        """
        Check if a file should be ignored during processing.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if the file should be ignored, False otherwise
        """
        return file_path.name.lower() in IGNORE_FILES
    
    def extract_prefix(self, filename: str) -> str:
        """
        Extract the prefix from a filename (text before the extension).
        
        Args:
            filename: Name of the file
            
        Returns:
            The prefix part of the filename
        """
        # Remove extension and return the prefix
        return Path(filename).stem
    
    def get_files_in_directory(self, directory: Path) -> List[Path]:
        """
        Get all files in a directory (non-recursive for top-level processing).
        
        Args:
            directory: Directory to scan
            
        Returns:
            List of file paths in the directory
        """
        files = []
        try:
            for item in directory.iterdir():
                if item.is_file() and not self.should_ignore_file(item):
                    files.append(item)
        except PermissionError:
            print(f"Warning: Permission denied accessing {directory}")
        return files
    
    def folder_has_3d_models(self, folder_path: Path) -> bool:
        """
        Check if a folder contains any 3D model files.
        
        Args:
            folder_path: Path to the folder to check
            
        Returns:
            True if the folder contains 3D models, False otherwise
        """
        try:
            for item in folder_path.rglob("*"):
                if item.is_file() and self.is_3d_model_file(item):
                    return True
        except PermissionError:
            print(f"Warning: Permission denied accessing {folder_path}")
        return False
    
    def create_folder_if_not_exists(self, folder_path: Path) -> bool:
        """
        Create a folder if it doesn't exist.
        
        Args:
            folder_path: Path to the folder to create
            
        Returns:
            True if folder was created, False if it already existed
        """
        if not folder_path.exists():
            if not self.dry_run:
                folder_path.mkdir(parents=True, exist_ok=True)
            print(f"{'[DRY RUN] ' if self.dry_run else ''}Created folder: {folder_path.name}")
            self.created_folders += 1
            return True
        return False
    
    def move_file(self, source: Path, destination: Path) -> bool:
        """
        Move a file from source to destination.
        
        Args:
            source: Source file path
            destination: Destination file path
            
        Returns:
            True if file was moved successfully, False otherwise
        """
        try:
            if not self.dry_run:
                if destination.exists():
                    print(f"Warning: Destination file already exists: {destination}")
                    return False
                shutil.move(str(source), str(destination))
            print(f"{'[DRY RUN] ' if self.dry_run else ''}Moved: {source.name} -> {destination.parent.name}/")
            self.moved_files += 1
            return True
        except Exception as e:
            print(f"Error moving file {source} to {destination}: {e}")
            return False
    
    def move_folder_to_scrap(self, folder_path: Path) -> bool:
        """
        Move a folder to the Scrap directory.
        
        Args:
            folder_path: Path to the folder to move
            
        Returns:
            True if folder was moved successfully, False otherwise
        """
        if folder_path.name == "Scrap":
            return False  # Don't move the Scrap folder itself
        
        # Create Scrap directory if it doesn't exist
        if not self.scrap_directory.exists():
            self.create_folder_if_not_exists(self.scrap_directory)
        
        destination = self.scrap_directory / folder_path.name
        
        # Handle naming conflicts in Scrap folder
        counter = 1
        original_destination = destination
        while destination.exists():
            destination = original_destination.parent / f"{original_destination.name}_{counter}"
            counter += 1
        
        try:
            if not self.dry_run:
                shutil.move(str(folder_path), str(destination))
            print(f"{'[DRY RUN] ' if self.dry_run else ''}Moved to Scrap: {folder_path.name} -> {destination.name}")
            self.moved_to_scrap += 1
            return True
        except Exception as e:
            print(f"Error moving folder {folder_path} to Scrap: {e}")
            return False
    
    def move_file_to_scrap(self, file_path: Path) -> bool:
        """
        Move a file to the Scrap directory.
        
        Args:
            file_path: Path to the file to move
            
        Returns:
            True if file was moved successfully, False otherwise
        """
        # Create Scrap directory if it doesn't exist
        if not self.scrap_directory.exists():
            self.create_folder_if_not_exists(self.scrap_directory)
        
        destination = self.scrap_directory / file_path.name
        
        # Handle naming conflicts in Scrap folder
        counter = 1
        original_destination = destination
        while destination.exists():
            stem = original_destination.stem
            suffix = original_destination.suffix
            destination = original_destination.parent / f"{stem}_{counter}{suffix}"
            counter += 1
        
        try:
            if not self.dry_run:
                shutil.move(str(file_path), str(destination))
            print(f"{'[DRY RUN] ' if self.dry_run else ''}Moved to Scrap: {file_path.name} -> {destination.name}")
            self.moved_files += 1
            return True
        except Exception as e:
            print(f"Error moving file {file_path} to Scrap: {e}")
            return False
    
    def calculate_file_hash(self, file_path: Path, chunk_size: int = 8192) -> str:
        """
        Calculate SHA-256 hash of a file's contents.
        
        Args:
            file_path: Path to the file
            chunk_size: Size of chunks to read (default 8KB)
            
        Returns:
            SHA-256 hash as hexadecimal string
        """
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(chunk_size):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            print(f"Warning: Could not calculate hash for {file_path}: {e}")
            return ""
    
    def get_3d_models_in_folder(self, folder_path: Path) -> List[Path]:
        """
        Get all 3D model files directly in a folder (not recursive).
        
        Args:
            folder_path: Path to the folder
            
        Returns:
            List of 3D model file paths
        """
        models = []
        try:
            for item in folder_path.iterdir():
                if item.is_file() and self.is_3d_model_file(item):
                    models.append(item)
        except Exception as e:
            print(f"Warning: Could not scan folder {folder_path}: {e}")
        return models
    
    def folders_have_identical_3d_models(self, folder1: Path, folder2: Path) -> bool:
        """
        Check if two folders have identical 3D model contents.
        
        Args:
            folder1: First folder path
            folder2: Second folder path
            
        Returns:
            True if folders have identical 3D models, False otherwise
        """
        models1 = self.get_3d_models_in_folder(folder1)
        models2 = self.get_3d_models_in_folder(folder2)
        
        # Must have same number of 3D models
        if len(models1) != len(models2):
            return False
        
        # Calculate hashes for all 3D models in both folders
        hashes1 = {self.calculate_file_hash(model) for model in models1}
        hashes2 = {self.calculate_file_hash(model) for model in models2}
        
        # Remove empty hashes (failed calculations) 
        hashes1.discard("")
        hashes2.discard("")
        
        # Folders are identical if they have the same set of hashes
        return hashes1 == hashes2 and len(hashes1) > 0
    
    def merge_folders_with_conflict_resolution(self, source_folder: Path, target_folder: Path) -> bool:
        """
        Merge source folder into target folder with intelligent conflict resolution.
        Supporting files: Keep larger file when names conflict.
        
        Args:
            source_folder: Folder to merge (will be removed after merge)
            target_folder: Destination folder
            
        Returns:
            True if merge was successful, False otherwise
        """
        try:
            print(f"🔗 Merging duplicate: {source_folder.name} -> {target_folder.name}")
            
            # Process all files in source folder
            for item in source_folder.iterdir():
                if item.is_file():
                    destination = target_folder / item.name
                    
                    if not destination.exists():
                        # No conflict - just move the file
                        if not self.dry_run:
                            shutil.move(str(item), str(destination))
                        print(f"  {'[DRY RUN] ' if self.dry_run else ''}Added: {item.name}")
                    else:
                        # File conflict - resolve by keeping larger file
                        source_size = item.stat().st_size
                        dest_size = destination.stat().st_size
                        
                        if source_size > dest_size:
                            # Source file is larger - replace destination
                            if not self.dry_run:
                                destination.unlink()  # Remove smaller file
                                shutil.move(str(item), str(destination))
                            print(f"  {'[DRY RUN] ' if self.dry_run else ''}Replaced: {item.name} (larger: {source_size:,} vs {dest_size:,} bytes)")
                        else:
                            # Destination is larger or equal - keep destination, remove source
                            if not self.dry_run:
                                item.unlink()
                            print(f"  {'[DRY RUN] ' if self.dry_run else ''}Kept existing: {item.name} (larger: {dest_size:,} vs {source_size:,} bytes)")
            
            # Remove empty source folder
            if not self.dry_run:
                source_folder.rmdir()
            print(f"  {'[DRY RUN] ' if self.dry_run else ''}Removed empty folder: {source_folder.name}")
            
            return True
        except Exception as e:
            print(f"Error merging folders: {e}")
            return False
    
    def detect_naming_conflicts(self, folders_to_process: List[Tuple[Path, str]]) -> Tuple[List[Tuple[Path, str]], Dict[str, List[Path]]]:
        """
        Detect naming conflicts without expensive content analysis.
        
        Args:
            folders_to_process: List of (source_folder, desired_name) tuples
            
        Returns:
            Tuple of (non_conflicting_folders, conflicting_groups)
        """
        # Group folders by desired name
        folders_by_name = defaultdict(list)
        for source_folder, desired_name in folders_to_process:
            folders_by_name[desired_name].append(source_folder)
        
        non_conflicting = []
        conflicting_groups = {}
        
        for desired_name, folder_group in folders_by_name.items():
            if len(folder_group) == 1:
                # No conflict
                non_conflicting.append((folder_group[0], desired_name))
            else:
                # Conflict detected
                conflicting_groups[desired_name] = folder_group
        
        return non_conflicting, conflicting_groups
    
    def resolve_conflicting_folders_with_content_analysis(self, conflicting_groups: Dict[str, List[Path]]) -> List[Tuple[Path, Path]]:
        """
        Resolve naming conflicts using content-based duplicate detection.
        Only called when conflicts are detected.
        
        Args:
            conflicting_groups: Dict of {desired_name: [folders_with_same_name]}
            
        Returns:
            List of (source_folder, final_destination) tuples with conflicts resolved
        """
        print("\n🔍 Resolving naming conflicts with content analysis...")
        final_destinations = []
        
        for desired_name, folder_group in conflicting_groups.items():
            print(f"⚠ Analyzing conflict: {len(folder_group)} folders want name '{desired_name}'")
            print("  🧬 Comparing 3D model content...")
            
            # Group by identical 3D model content (expensive operation)
            unique_groups = []  # List of (representative_folder, [identical_folders])
            
            for folder in folder_group:
                # Check if this folder matches any existing group
                matched_group = False
                for i, (rep_folder, identical_list) in enumerate(unique_groups):
                    if self.folders_have_identical_3d_models(folder, rep_folder):
                        identical_list.append(folder)
                        matched_group = True
                        print(f"    ✓ {folder.name} matches content of {rep_folder.name}")
                        break
                
                if not matched_group:
                    # This folder has unique content
                    unique_groups.append((folder, [folder]))
                    print(f"    📁 {folder.name} has unique content")
            
            # Assign destinations based on unique content groups
            for i, (representative_folder, identical_folders) in enumerate(unique_groups):
                if i == 0:
                    # First unique group gets the original name
                    final_destination = self.target_directory / desired_name
                else:
                    # Subsequent groups get numbered suffixes
                    final_destination = self.target_directory / f"{desired_name}_{i + 1}"
                
                if len(identical_folders) > 1:
                    print(f"  💎 Merging {len(identical_folders)} identical folders -> '{final_destination.name}'")
                    
                    # Plan to merge all identical folders into the first one
                    primary_folder = identical_folders[0]
                    final_destinations.append((primary_folder, final_destination))
                    
                    # Mark other identical folders for merging
                    for duplicate_folder in identical_folders[1:]:
                        final_destinations.append((duplicate_folder, final_destination))  # Will be merged
                else:
                    print(f"  📁 Unique folder: '{representative_folder.name}' -> '{final_destination.name}'")
                    final_destinations.append((representative_folder, final_destination))
        
        return final_destinations
    
    def resolve_folder_naming_conflicts(self, folders_to_process: List[Tuple[Path, str]]) -> List[Tuple[Path, Path]]:
        """
        Efficiently resolve naming conflicts - only use content analysis when needed.
        
        Args:
            folders_to_process: List of (source_folder, desired_name) tuples
            
        Returns:
            List of (source_folder, final_destination) tuples with conflicts resolved
        """
        if not folders_to_process:
            return []
        
        # Step 1: Quick conflict detection (no expensive operations)
        non_conflicting, conflicting_groups = self.detect_naming_conflicts(folders_to_process)
        
        final_destinations = []
        
        # Step 2: Handle non-conflicting folders (fast path)
        for source_folder, desired_name in non_conflicting:
            final_destination = self.target_directory / desired_name
            final_destinations.append((source_folder, final_destination))
        
        # Step 3: Handle conflicts with content analysis (only when needed)
        if conflicting_groups:
            print(f"\n⚠ Found {len(conflicting_groups)} naming conflicts requiring content analysis")
            conflict_resolutions = self.resolve_conflicting_folders_with_content_analysis(conflicting_groups)
            final_destinations.extend(conflict_resolutions)
        else:
            print("\n✓ No naming conflicts detected - using fast organization path")
        
        return final_destinations
    
    def organize_files_by_prefix(self) -> Dict[str, List[Path]]:
        """
        Group files in the target directory by their prefixes.
        
        Returns:
            Dictionary mapping prefixes to lists of files
        """
        print("Analyzing files by prefix...")
        files_by_prefix = defaultdict(list)
        
        # Get all files in the target directory (top-level only)
        files = self.get_files_in_directory(self.target_directory)
        
        for file_path in files:
            prefix = self.extract_prefix(file_path.name)
            files_by_prefix[prefix].append(file_path)
        
        # Report findings
        print(f"Found {len(files)} files with {len(files_by_prefix)} unique prefixes")
        
        for prefix, file_list in files_by_prefix.items():
            has_3d_model = any(self.is_3d_model_file(f) for f in file_list)
            model_indicator = "🎯" if has_3d_model else "📄"
            print(f"  {model_indicator} {prefix}: {len(file_list)} files")
        
        return files_by_prefix
    
    def find_all_folders_with_3d_models(self) -> List[Path]:
        """
        Recursively find all folders that contain 3D models, at any depth.
        
        Returns:
            List of folder paths that contain 3D models
        """
        folders_with_3d_models = []
        
        def scan_directory(directory: Path, depth: int = 0):
            try:
                for item in directory.iterdir():
                    if item.is_dir() and item.name != "Scrap":
                        # Check if this folder has 3D models
                        if self.folder_has_3d_models(item):
                            folders_with_3d_models.append(item)
                            print(f"{'  ' * depth}📁 Found 3D model folder: {item.relative_to(self.target_directory)}")
                        else:
                            # Recursively scan subdirectories
                            scan_directory(item, depth + 1)
            except PermissionError:
                print(f"Warning: Permission denied accessing {directory}")
        
        print("\nScanning for folders with 3D models at all depths...")
        scan_directory(self.target_directory)
        
        return folders_with_3d_models

    def flatten_directory_structure(self):
        """
        Flatten directory structure by moving all folders with 3D models to top level.
        """
        print("\nFlattening directory structure...")
        
        # Find all folders with 3D models at any depth
        folders_to_flatten = self.find_all_folders_with_3d_models()
        
        # Filter out folders already at top level
        folders_to_move = [f for f in folders_to_flatten 
                          if f.parent != self.target_directory]
        
        if not folders_to_move:
            print("✓ All folders with 3D models are already at top level")
            return
        
        print(f"Moving {len(folders_to_move)} nested folders to top level...")
        
        for folder_path in folders_to_move:
            # Generate a safe name for the top-level destination
            destination_name = self.generate_safe_folder_name(folder_path.name)
            destination = self.target_directory / destination_name
            
            # Handle name conflicts
            counter = 1
            original_destination = destination
            while destination.exists():
                destination = original_destination.parent / f"{original_destination.name}_{counter}"
                counter += 1
            
            try:
                if not self.dry_run:
                    shutil.move(str(folder_path), str(destination))
                print(f"{'[DRY RUN] ' if self.dry_run else ''}Flattened: {folder_path.relative_to(self.target_directory)} -> {destination.name}/")
                self.moved_files += 1
            except Exception as e:
                print(f"Error moving folder {folder_path}: {e}")

    def generate_safe_folder_name(self, original_name: str) -> str:
        """
        Generate a safe folder name by removing invalid characters.
        
        Args:
            original_name: Original folder name
            
        Returns:
            Safe folder name for filesystem
        """
        # Remove or replace problematic characters
        safe_name = original_name
        # Replace problematic characters with underscores
        problematic_chars = ['<', '>', ':', '"', '|', '?', '*', '#']
        for char in problematic_chars:
            safe_name = safe_name.replace(char, '_')
        
        # Remove leading/trailing spaces and dots
        safe_name = safe_name.strip(' .')
        
        # Ensure name isn't empty
        if not safe_name:
            safe_name = "unnamed_folder"
            
        return safe_name

    def process_remaining_empty_folders(self):
        """
        Process remaining empty folders and move them to Scrap after flattening.
        """
        print("\nCleaning up empty folders...")
        
        def find_empty_folders(directory: Path) -> List[Path]:
            empty_folders = []
            try:
                for item in directory.iterdir():
                    if item.is_dir() and item.name != "Scrap":
                        # Check if folder is empty or contains only empty subfolders
                        has_files = False
                        for subitem in item.rglob("*"):
                            if subitem.is_file():
                                has_files = True
                                break
                        
                        if not has_files:
                            empty_folders.append(item)
                        else:
                            # Recursively check subdirectories
                            empty_folders.extend(find_empty_folders(item))
            except PermissionError:
                print(f"Warning: Permission denied accessing {directory}")
            
            return empty_folders
        
        empty_folders = find_empty_folders(self.target_directory)
        
        if empty_folders:
            print(f"Found {len(empty_folders)} empty folders to clean up")
            for folder in empty_folders:
                print(f"⚠ Moving empty folder to Scrap: {folder.relative_to(self.target_directory)}")
                self.move_folder_to_scrap(folder)
        else:
            print("✓ No empty folders found")

    def process_existing_folders(self):
        """
        Process existing folder structure: flatten and clean up.
        """
        # Step 1: Flatten directory structure
        self.flatten_directory_structure()
        
        # Step 2: Clean up empty folders
        self.process_remaining_empty_folders()
    
    
    def is_protected_directory(self) -> bool:
        """
        Check if the target directory is a protected system directory.
        
        Returns:
            True if directory should not be organized, False otherwise
        """
        target_str = str(self.target_directory).lower()
        
        # Check for exact system directory matches
        system_directories = {
            'c:\\windows', 'c:\\program files', 'c:\\program files (x86)',
            'c:\\programdata', 'c:\\users\\all users', 'c:\\users\\default',
            'c:\\system volume information', 'c:\\$recycle.bin',
            'c:\\windows.old', 'c:\\perflogs', 'c:\\msocache'
        }
        
        if target_str in system_directories:
            return True
        
        # Check for direct system drives
        if os.name == 'nt':  # Windows
            if target_str in ['c:\\', 'd:\\', 'c:', 'd:']:
                return True
        else:  # Unix-like systems
            if target_str in ['/', '/usr', '/bin', '/etc', '/var', '/home', '/root']:
                return True
        
        # Check if targeting critical system subdirectories
        critical_patterns = [
            'c:\\windows\\',
            'c:\\program files\\',
            'c:\\program files (x86)\\',
            'c:\\programdata\\',
            '/usr/bin/',
            '/usr/lib/',
            '/etc/',
            '/var/',
            '/bin/',
            '/sbin/'
        ]
        
        for pattern in critical_patterns:
            if target_str.startswith(pattern):
                return True
        
        # Allow user directories but warn if they contain development folders
        dev_folders = {'.git', '.svn', '.hg', 'node_modules', '__pycache__', '.vscode', '.idea'}
        try:
            for item in self.target_directory.iterdir():
                if item.is_dir() and item.name.lower() in dev_folders:
                    print(f"⚠ Warning: Development folder detected: {item.name}")
                    print("This appears to be a development project directory.")
                    print("Proceeding with organization...")
                    break
        except PermissionError:
            pass
                
        return False
    
    def create_organization_plan(self) -> Dict:
        """
        Create a detailed organization plan without executing it.
        
        Returns:
            Dictionary containing the organization plan
        """
        plan = {
            "timestamp": datetime.datetime.now().isoformat(),
            "target_directory": str(self.target_directory),
            "actions": {
                "files_to_move": [],
                "folders_to_create": [],
                "folders_to_flatten": [],
                "folders_to_scrap": [],
                "files_to_skip": []
            },
            "summary": {
                "total_files": 0,
                "files_with_3d_models": 0,
                "folders_to_create": 0,
                "folders_to_flatten": 0,
                "folders_to_scrap": 0
            }
        }
        
        # Analyze files by prefix
        files_by_prefix = defaultdict(list)
        files = self.get_files_in_directory(self.target_directory)
        plan["summary"]["total_files"] = len(files)
        
        for file_path in files:
            prefix = self.extract_prefix(file_path.name)
            files_by_prefix[prefix].append(file_path)
        
        # Plan file movements for loose files
        for prefix, file_list in files_by_prefix.items():
            has_3d_model = any(self.is_3d_model_file(f) for f in file_list)
            
            if has_3d_model:
                plan["summary"]["files_with_3d_models"] += len(file_list)
                plan["summary"]["folders_to_create"] += 1
                plan["actions"]["folders_to_create"].append(prefix)
                
                for file_path in file_list:
                    plan["actions"]["files_to_move"].append({
                        "source": str(file_path),
                        "destination": str(self.target_directory / prefix / file_path.name),
                        "prefix": prefix
                    })
            else:
                # Mark orphaned files to be moved to Scrap
                for file_path in file_list:
                    plan["actions"]["files_to_skip"].append({
                        "file": str(file_path),
                        "reason": "No 3D model in prefix group - will be moved to Scrap",
                        "destination": "Scrap"
                    })
        
        # Plan directory flattening - find all nested folders with 3D models
        def find_folders_to_flatten(directory: Path, depth: int = 0) -> List[Dict]:
            folders_info = []
            try:
                for item in directory.iterdir():
                    if item.is_dir() and item.name != "Scrap":
                        if self.folder_has_3d_models(item):
                            # Check if this folder directly contains 3D models (not just in subfolders)
                            has_direct_3d_models = any(
                                self.is_3d_model_file(file) 
                                for file in item.iterdir() 
                                if file.is_file()
                            )
                            
                            if has_direct_3d_models:
                                # This folder directly contains 3D models - flatten it if not at top level
                                if item.parent != self.target_directory:
                                    safe_name = self.generate_safe_folder_name(item.name)
                                    folders_info.append({
                                        "source": str(item),
                                        "destination": str(self.target_directory / safe_name),
                                        "original_path": str(item.relative_to(self.target_directory))
                                    })
                            else:
                                # This folder only has 3D models in subfolders - continue scanning deeper
                                folders_info.extend(find_folders_to_flatten(item, depth + 1))
                        else:
                            # Continue scanning deeper for 3D models
                            folders_info.extend(find_folders_to_flatten(item, depth + 1))
            except PermissionError:
                pass
            return folders_info
        
        folders_to_flatten = find_folders_to_flatten(self.target_directory)
        plan["actions"]["folders_to_flatten"] = folders_to_flatten
        plan["summary"]["folders_to_flatten"] = len(folders_to_flatten)
        
        # Plan folder movements to scrap (empty folders after flattening)
        # This will be handled during execution after flattening
        
        self.organization_plan = plan
        return plan
    
    def save_instruction_file(self, plan: Dict) -> bool:
        """
        Save the organization plan to an instruction file.
        
        Args:
            plan: Organization plan dictionary
            
        Returns:
            True if file was saved successfully, False otherwise
        """
        try:
            with open(self.instruction_file_path, 'w', encoding='utf-8') as f:
                json.dump(plan, f, indent=2, ensure_ascii=False)
            
            print(f"\n📄 Organization plan saved to: {self.instruction_file_path.name}")
            print("To execute this plan, run with --commit flag")
            return True
        except Exception as e:
            print(f"Error saving instruction file: {e}")
            return False
    
    def load_instruction_file(self) -> Optional[Dict]:
        """
        Load organization plan from instruction file.
        
        Returns:
            Organization plan dictionary, or None if file doesn't exist
        """
        if not self.instruction_file_path.exists():
            return None
        
        try:
            with open(self.instruction_file_path, 'r', encoding='utf-8') as f:
                plan = json.load(f)
            return plan
        except Exception as e:
            print(f"Error loading instruction file: {e}")
            return None
    
    def execute_from_plan(self, plan: Dict) -> bool:
        """
        Execute organization based on a loaded plan.
        
        Args:
            plan: Organization plan dictionary
            
        Returns:
            True if execution completed successfully, False otherwise
        """
        print("Executing organization plan...")
        print(f"Plan created: {plan.get('timestamp', 'Unknown')}")
        print(f"Target directory: {plan.get('target_directory', 'Unknown')}")
        
        # Verify the plan is for the current directory
        if plan.get('target_directory') != str(self.target_directory):
            print("⚠ Warning: Plan was created for a different directory!")
            if not self.trust_mode:
                response = input("Continue anyway? (y/N): ").lower()
                if response != 'y':
                    print("Operation cancelled.")
                    return False
        
        actions = plan.get('actions', {})
        
        # Create folders first
        folders_to_create = actions.get('folders_to_create', [])
        for folder_name in folders_to_create:
            folder_path = self.target_directory / folder_name
            self.create_folder_if_not_exists(folder_path)
        
        # Move files
        files_to_move = actions.get('files_to_move', [])
        for file_action in files_to_move:
            source = Path(file_action['source'])
            destination = Path(file_action['destination'])
            if source.exists():
                self.move_file(source, destination)
            else:
                print(f"Warning: Source file not found: {source}")
        
        # Flatten nested folders with 3D models
        folders_to_flatten = actions.get('folders_to_flatten', [])
        if folders_to_flatten:
            print("\nFlattening directory structure...")
            for folder_action in folders_to_flatten:
                source = Path(folder_action['source'])
                destination = Path(folder_action['destination'])
                original_path = folder_action['original_path']
                
                if source.exists():
                    # Handle name conflicts
                    counter = 1
                    original_destination = destination
                    while destination.exists():
                        destination = original_destination.parent / f"{original_destination.name}_{counter}"
                        counter += 1
                    
                    try:
                        shutil.move(str(source), str(destination))
                        print(f"Flattened: {original_path} -> {destination.name}/")
                        self.moved_files += 1
                    except Exception as e:
                        print(f"Error moving folder {source}: {e}")
                else:
                    print(f"Warning: Folder to flatten not found: {source}")
        
        # Move orphaned files to scrap
        files_to_skip = actions.get('files_to_skip', [])
        for file_action in files_to_skip:
            if file_action.get('destination') == 'Scrap':
                file_path = Path(file_action['file'])
                if file_path.exists():
                    self.move_file_to_scrap(file_path)
                else:
                    print(f"Warning: Orphaned file not found: {file_path}")
        
        # Clean up empty folders after flattening
        if folders_to_flatten:
            self.process_remaining_empty_folders()
        
        # Move folders to scrap
        folders_to_scrap = actions.get('folders_to_scrap', [])
        for folder_path_str in folders_to_scrap:
            folder_path = Path(folder_path_str)
            if folder_path.exists():
                self.move_folder_to_scrap(folder_path)
            else:
                print(f"Warning: Folder not found: {folder_path}")
        
        return True
    
    def organize_files(self):
        """
        Main method to organize files according to Manyfold requirements.
        """
        # Safety check for protected directories
        if self.is_protected_directory():
            print("🚫 ERROR: This appears to be a protected system directory!")
            print("Organization is not allowed on system/application directories for safety.")
            print(f"Protected directory detected: {self.target_directory}")
            return
        
        # Handle commit mode
        if self.commit_mode:
            plan = self.load_instruction_file()
            if plan is None:
                print("❌ Commit failed: No instruction file found!")
                print(f"Expected file: {self.instruction_file_path.name}")
                print("Re-run without --commit to generate organization plan.")
                return
            
            print("📋 Found organization instruction file")
            if not self.trust_mode:
                print("\nPlan Summary:")
                summary = plan.get('summary', {})
                print(f"  Files to organize: {summary.get('files_with_3d_models', 0)}")
                print(f"  Folders to create: {summary.get('folders_to_create', 0)}")
                print(f"  Folders to move to Scrap: {summary.get('folders_to_scrap', 0)}")
                
                response = input("\nExecute this plan? (y/N): ").lower()
                if response != 'y':
                    print("Operation cancelled.")
                    return
            
            success = self.execute_from_plan(plan)
            if success:
                # Remove instruction file after successful execution
                try:
                    self.instruction_file_path.unlink()
                    print(f"✅ Instruction file removed: {self.instruction_file_path.name}")
                except Exception as e:
                    print(f"Warning: Could not remove instruction file: {e}")
            
            self.print_summary()
            return
        
        # Normal organization mode
        print("Starting file organization process...")
        
        # If dry-run mode, create and save organization plan, then simulate execution
        if self.dry_run:
            plan = self.create_organization_plan()
            self.save_instruction_file(plan)
            
            # Display and simulate what would be done
            self.simulate_organization()
            self.print_summary()
            return
        
        # Live execution mode
        if not self.trust_mode:
            print("⚠ WARNING: Live execution mode!")
            print("This will make actual changes to your files and folders.")
            response = input("Continue? (y/N): ").lower()
            if response != 'y':
                print("Operation cancelled.")
                return
        
        # Step 1: Group files by prefix and create folders
        files_by_prefix = self.organize_files_by_prefix()
        
        print("\nCreating folders and moving files...")
        for prefix, file_list in files_by_prefix.items():
            # Check if any file in this group is a 3D model
            has_3d_model = any(self.is_3d_model_file(f) for f in file_list)
            
            if has_3d_model:
                # Create folder for this prefix
                folder_path = self.target_directory / prefix
                self.create_folder_if_not_exists(folder_path)
                
                # Move all files with this prefix to the folder
                for file_path in file_list:
                    destination = folder_path / file_path.name
                    self.move_file(file_path, destination)
            else:
                # Move orphaned files (no matching 3D models) to Scrap
                print(f"⚠ Moving orphaned files to Scrap (prefix '{prefix}' has no 3D models)")
                for file_path in file_list:
                    self.move_file_to_scrap(file_path)
        
        # Step 2: Process existing folders
        self.process_existing_folders()
        
        # Step 3: Print summary
        self.print_summary()
    
    def simulate_organization(self):
        """
        Simulate the organization process for dry-run mode using the organization plan.
        """
        if not self.organization_plan:
            print("Error: No organization plan available for simulation")
            return
        
        print("Simulating organization based on plan...")
        actions = self.organization_plan.get('actions', {})
        
        # Simulate folder creation and file movements
        print("\nCreating folders and moving files...")
        folders_to_create = actions.get('folders_to_create', [])
        files_to_move = actions.get('files_to_move', [])
        
        # Group file movements by folder
        movements_by_folder = {}
        for file_action in files_to_move:
            prefix = file_action['prefix']
            if prefix not in movements_by_folder:
                movements_by_folder[prefix] = []
            movements_by_folder[prefix].append(file_action)
        
        # Simulate the creation and population of each folder
        for folder_name in folders_to_create:
            self.create_folder_if_not_exists(self.target_directory / folder_name)
            
            # Show files being moved to this folder
            if folder_name in movements_by_folder:
                for file_action in movements_by_folder[folder_name]:
                    source = Path(file_action['source'])
                    destination = Path(file_action['destination'])
                    print(f"{'[DRY RUN] ' if self.dry_run else ''}Moved: {source.name} -> {destination.parent.name}/")
                    self.moved_files += 1
        
        # Simulate orphaned files being moved to Scrap
        files_to_skip = actions.get('files_to_skip', [])
        orphaned_files = [f for f in files_to_skip if f.get('destination') == 'Scrap']
        if orphaned_files:
            print(f"\n⚠ Moving orphaned files to Scrap (no matching 3D models)")
            if not self.scrap_directory.exists():
                self.create_folder_if_not_exists(self.scrap_directory)
            
            for file_action in orphaned_files:
                file_path = Path(file_action['file'])
                print(f"{'[DRY RUN] ' if self.dry_run else ''}Moved to Scrap: {file_path.name} -> {file_path.name}")
                self.moved_files += 1
        
        # Simulate directory flattening
        folders_to_flatten = actions.get('folders_to_flatten', [])
        if folders_to_flatten:
            print(f"\nFlattening directory structure...")
            for folder_action in folders_to_flatten:
                source_path = folder_action['original_path']
                destination_path = Path(folder_action['destination'])
                print(f"{'[DRY RUN] ' if self.dry_run else ''}Flattened: {source_path} -> {destination_path.name}/")
                self.moved_files += 1

        # Simulate existing folder processing
        print("\nAnalyzing existing folders...")
        folders_to_scrap = actions.get('folders_to_scrap', [])
        
        # Show folders being kept
        folders = [item for item in self.target_directory.iterdir() 
                  if item.is_dir() and item.name != "Scrap"]
        
        for folder in folders:
            folder_path_str = str(folder)
            if folder_path_str in folders_to_scrap:
                print(f"⚠ Moving to Scrap (no 3D models): {folder.name}")
                if not self.scrap_directory.exists():
                    self.create_folder_if_not_exists(self.scrap_directory)
                print(f"{'[DRY RUN] ' if self.dry_run else ''}Moved to Scrap: {folder.name} -> {folder.name}")
                self.moved_to_scrap += 1
            else:
                print(f"✓ Keeping folder (has 3D models): {folder.name}")
    
    def print_summary(self):
        """Print a summary of the organization process."""
        print("\n" + "=" * 60)
        print("ORGANIZATION SUMMARY")
        print("=" * 60)
        print(f"Files moved: {self.moved_files}")
        print(f"Folders created: {self.created_folders}")
        print(f"Folders moved to Scrap: {self.moved_to_scrap}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE RUN'}")
        
        if self.dry_run:
            print("\n⚠ This was a dry run. No actual changes were made.")
            print(f"📄 Instruction file created: {self.instruction_file_path.name}")
            print("Run with --commit to execute the plan.")


def setup_virtual_environment():
    """
    Set up and activate a virtual environment for the script.
    This ensures the script runs in isolation from the host OS.
    """
    venv_path = Path(__file__).parent / "file_organizer_venv"
    
    if not venv_path.exists():
        print("Creating virtual environment...")
        venv.create(venv_path, with_pip=True)
    
    # Get the path to the virtual environment's Python executable
    if os.name == 'nt':  # Windows
        python_exe = venv_path / "Scripts" / "python.exe"
        pip_exe = venv_path / "Scripts" / "pip.exe"
    else:  # Unix/Linux/MacOS
        python_exe = venv_path / "bin" / "python"
        pip_exe = venv_path / "bin" / "pip"
    
    return python_exe, pip_exe


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Organize files for Manyfold application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python file_organizer.py --dry-run
  python file_organizer.py --directory "C:/Users/matty/Desktop/Test STL"
  python file_organizer.py --directory "C:/Users/matty/Desktop/Test STL" --dry-run
        """
    )
    
    parser.add_argument(
        "--directory",
        default=os.getcwd(),
        help="Target directory to organize (default: current directory)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making actual changes"
    )
    
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Execute organization plan from instruction file"
    )
    
    parser.add_argument(
        "--trust",
        action="store_true",
        help="Skip safety prompts and execute immediately"
    )
    
    args = parser.parse_args()
    
    # Dry-run is always the default unless --commit is specified
    if args.commit:
        dry_run_mode = False  # Commit mode overrides dry-run
    else:
        dry_run_mode = True   # Always default to dry-run for safety
    
    # Validate target directory
    target_dir = Path(args.directory)
    if not target_dir.exists():
        print(f"Error: Directory '{target_dir}' does not exist.")
        sys.exit(1)
    
    if not target_dir.is_dir():
        print(f"Error: '{target_dir}' is not a directory.")
        sys.exit(1)
    
    # Initialize and run the organizer
    try:
        organizer = FileOrganizer(target_dir, dry_run=dry_run_mode, commit_mode=args.commit, trust_mode=args.trust)
        organizer.organize_files()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError during organization: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run in virtual environment for isolation
    main()
