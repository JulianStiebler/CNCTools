import os
from typing import Dict, Optional, Union

from ..shared import BigArchive
from ..config import config, GameOptions, GeneralOptions

class VirtualFile:
    def __init__(self, path: str, big_archive: Optional[BigArchive] = None, file_info=None):
        self.path = path
        self.name = os.path.basename(path)
        self.big_archive = big_archive
        self.file_info = file_info
        self.is_modified = False
        self._content_cache = None
        
    @property 
    def extension(self):
        return os.path.splitext(self.name)[1].lower()
        
    def get_content(self) -> bytes:
        """Read file content from BIG archive or physical file"""
        if self._content_cache is not None:
            return self._content_cache
            
        if self.big_archive:
            # Extract file from BIG archive
            self._content_cache = self.big_archive.extract_file(
                self.path, 
                output_file=None,  # Don't write to disk
                return_data=True
            )
        else:
            # Regular file
            with open(self.path, 'rb') as f:
                self._content_cache = f.read()
                
        return self._content_cache
        
    def get_text_content(self) -> str:
        """Get content as text, attempting to decode using common encodings"""
        data = self.get_content()
        
        # Try common encodings
        encodings = ['utf-8', 'latin-1', 'cp1252']
        for encoding in encodings:
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
                
        # Fallback to latin-1 which can decode any byte sequence
        return data.decode('latin-1')
        
    def save(self, content: Union[str, bytes]):
        """Save content to cache, marking file as modified"""
        if isinstance(content, str):
            self._content_cache = content.encode('utf-8')
        else:
            self._content_cache = content
            
        self.is_modified = True
        
    def commit(self):
        """Commit changes back to BIG archive or physical file"""
        if not self.is_modified or self._content_cache is None:
            return False
            
        if self.big_archive:
            # Extract to temp directory first
            temp_dir = config.cget(GeneralOptions.TEMP_DIR)
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
                
            # Create subdirectories if needed
            rel_path = self.path
            if rel_path.startswith('/'):
                rel_path = rel_path[1:]
                
            temp_file = os.path.join(temp_dir, rel_path)
            os.makedirs(os.path.dirname(temp_file), exist_ok=True)
            
            # Write file
            with open(temp_file, 'wb') as f:
                f.write(self._content_cache)
                
            # Repack BIG archive
            # TODO: Implement selective repacking instead of full repack
            self.big_archive.rebuild_with_modified_file(rel_path, temp_file)
        else:
            # Regular file, just write it
            with open(self.path, 'wb') as f:
                f.write(self._content_cache)
                
        self.is_modified = False
        return True

class VirtualFileSystem:
    def __init__(self):
        self.big_archives: Dict[str, BigArchive] = {}
        self.files: Dict[str, VirtualFile] = {}
        self.root_path: Optional[str] = None
        self.loaded = False
        
    def load_game_directory(self, path: str):
        """Load a game directory, scanning for BIG files and building virtual file system"""
        if not path or not os.path.exists(path):
            raise ValueError(f"Invalid game directory: {path}")
            
        self.root_path = path
        self.files = {}
        self.big_archives = {}
        self.loaded = False
        
        print(f"Loading game directory: {path}")
        
        # Create temp directory if needed
        temp_dir = config.cget(GeneralOptions.TEMP_DIR)
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
            
        # Use a memory structure instead of writing to file
        metadata = {}
        
        # Scan for BIG files
        for root, _, files in os.walk(path):
            for file in files:
                if file.lower().endswith('.big'):
                    big_file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(big_file_path, path)
                    print(f"Processing BIG archive: {rel_path}")
                    
                    try:
                        archive = BigArchive(big_file_path)
                        self.big_archives[big_file_path] = archive
                        
                        # Get file list from archive
                        file_list = archive.list_contents()
                        
                        # Store metadata for this BIG file
                        metadata[big_file_path] = {
                            "name": file,
                            "path": big_file_path,
                            "size": os.path.getsize(big_file_path),
                            "files": []
                        }
                        
                        # Process each file in the archive
                        for file_info in file_list:
                            file_path = file_info.get('name', '')
                            virtual_path = f"{big_file_path}:{file_path}"
                            
                            # Add to metadata
                            metadata[big_file_path]["files"].append({
                                "name": file_path,
                                "offset": file_info.get('offset', 0),
                                "size": file_info.get('size', 0)
                            })
                            
                            # Add to virtual filesystem
                            self.files[virtual_path] = VirtualFile(
                                file_path, 
                                archive,
                                file_info
                            )
                    except Exception as e:
                        print(f"Error processing {big_file_path}: {e}")
                        
        # Also scan for regular files we might want to edit
        self._scan_regular_files(path)
        
        # Save last opened folder
        config.cset(GameOptions.LAST_GAME_FOLDER, path, save=True)
        
        # Update recent folders
        recent = config.cget(GameOptions.RECENT_FOLDERS)
        if not isinstance(recent, list):
            recent = []
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        recent = recent[:5]  # Keep only 5 most recent
        config.cset(GameOptions.RECENT_FOLDERS, recent, save=True)
        
        self.loaded = True
        print(f"Loaded {len(self.files)} files from {len(self.big_archives)} BIG archives")
        return True
        
    def _scan_regular_files(self, path: str):
        """Scan for regular files (non-BIG) in the game directory"""
        extensions_of_interest = ['.ini', '.txt', '.cfg', '.xml']
        
        for root, _, files in os.walk(path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in extensions_of_interest):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, path)
                    virtual_path = f"regular:{rel_path}"
                    self.files[virtual_path] = VirtualFile(file_path)
    
    def get_file_structure(self):
        """
        Build a hierarchical file structure for display in the file tree.
        
        Returns:
            dict: A nested dictionary representing files and directories
        """
        if not self.loaded:
            return {"No Game Loaded": {"type": "folder", "path": "", "children": {}}}
        
        structure = {}
        
        # First add the BIG archives at root level
        for big_path, archive in sorted(self.big_archives.items()):
            big_name = os.path.basename(big_path)
            
            structure[big_name] = {
                "type": "big",
                "path": big_path,
                "children": {}
            }
        
        # Now add all files inside BIGs to their respective archives
        for virtual_path, file in self.files.items():
            if not file.big_archive:
                continue
                
            # Split the path to get BIG file and inner path
            big_path = file.big_archive.filepath
            big_name = os.path.basename(big_path)
            
            # Skip if this BIG isn't in our structure (shouldn't happen)
            if big_name not in structure:
                continue
                
            # Get the inner path and normalize separators
            inner_path = file.path.replace('\\', '/')
            path_parts = inner_path.split('/')
            
            # Navigate/build the tree structure
            current = structure[big_name]["children"]
            
            # Build folder structure for all but the last part (filename)
            for i, part in enumerate(path_parts[:-1]):
                if not part:  # Skip empty parts
                    continue
                    
                if part not in current:
                    current[part] = {
                        "type": "folder",
                        "path": '/'.join(path_parts[:i+1]),
                        "children": {}
                    }
                current = current[part]["children"]
            
            # Add the file at the final level
            filename = path_parts[-1]
            if filename:  # Only if filename isn't empty
                ext = os.path.splitext(filename)[1].lower()
                current[filename] = {
                    "type": "file",
                    "path": virtual_path,
                    "ext": ext
                }
    
    def get_file(self, virtual_path):
        """Get a virtual file by path"""
        return self.files.get(virtual_path)
    
    def save_all_modified(self):
        """Save all modified files"""
        count = 0
        for file in self.files.values():
            if file.is_modified:
                try:
                    file.commit()
                    count += 1
                except Exception as e:
                    print(f"Error saving {file.path}: {str(e)}")
        return count

# Create a global filesystem instance
vfs = VirtualFileSystem()