import os
import re
import struct
from typing import List, Dict, Any, Optional
from .patch import ModParameter
import json

INSIGHTFOLDER = "insights"

class BigArchive:
    """
    Class for working with BIG archive files commonly used in EA games.
    
    A BIG archive has a 16-byte header followed by file entries and file data:
    - MagicHeader (4 bytes): E.g., "BIGF" or "BIG4"
    - ArchiveSize (4 bytes): Total size of the archive
    - NumFiles    (4 bytes): Number of files in the archive
    - HeaderSize  (4 bytes): Offset to the first file's data
    
    Each file entry consists of:
    - FileOffset (4 bytes, big-endian)
    - FileLength (4 bytes, big-endian)
    - FilePath   (null-terminated string)
    """
    
    def __init__(self, filepath: Optional[str] = None):
        """
        Initialize a BigArchive object, optionally loading from a file.
        
        Args:
            filepath: Path to the BIG archive file (optional)
        """
        self.filepath = filepath
        self.header = {
            "magic": "",
            "archive_size": 0,
            "num_files": 0,
            "header_size": 0
        }
        self.entries = []
        
        if filepath and os.path.exists(filepath):
            self.parse()
    
    def parse(self) -> Dict[str, Any]:
        """
        Parse the BIG archive file and populate header and entries.
        
        Returns:
            Dict containing the archive information
        
        Raises:
            ValueError: If the file is too short or invalid
        """
        if not self.filepath or not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Archive file not found: {self.filepath}")
            
        self.entries = []
        with open(self.filepath, 'rb') as f:
            # Read the 16-byte header
            header_data = f.read(16)
            if len(header_data) < 16:
                raise ValueError("File too short to contain a valid header.")
                
            magic, archive_size, num_files, header_size = struct.unpack('>IIII', header_data)
            magic_str = magic.to_bytes(4, 'big').decode('ascii', errors='replace')
            
            # Store header information
            self.header = {
                "magic": magic_str,
                "archive_size": archive_size,
                "num_files": num_files,
                "header_size": header_size
            }
            
            # Read each file entry
            for _ in range(num_files):
                entry_data = f.read(8)
                if len(entry_data) < 8:
                    break
                    
                file_offset, file_length = struct.unpack('>II', entry_data)
                
                # Read the null-terminated file path
                file_path_bytes = bytearray()
                while True:
                    char = f.read(1)
                    if not char or char == b'\x00':
                        break
                    file_path_bytes.extend(char)
                    
                try:
                    file_path = file_path_bytes.decode('utf-8', errors='replace')
                except Exception:
                    file_path = str(file_path_bytes)
                    
                self.entries.append({
                    "file_offset": file_offset,
                    "file_length": file_length,
                    "file_path": file_path
                })
        
        return {
            **self.header,
            "entries": self.entries
        }
    
    def list_contents(self) -> None:
        """
        Print the contents of the BIG archive to the console.
        """
        if not self.entries:
            if self.filepath:
                self.parse()
            else:
                print("No archive loaded.")
                return
                
        print(f"Magic Header: {self.header['magic']}")
        print(f"Archive Size: {self.header['archive_size']}")
        print(f"Number of Files: {self.header['num_files']}")
        print(f"Header Size: {self.header['header_size']}\n")
        
        for i, entry in enumerate(self.entries):
            print(f"Entry {i+1}:")
            print(f"  File Path: {entry['file_path']}")
            print(f"  Offset   : {entry['file_offset']}")
            print(f"  File Size: {entry['file_length']}\n")
    
    def extract(self, out_dir: Optional[str] = None) -> str:
        """
        Extract all files from the BIG archive to the specified directory.
        
        Args:
            out_dir: Output directory (optional, defaults to archive basename)
            
        Returns:
            Path to the output directory
        """
        if not self.filepath:
            raise ValueError("No archive file loaded.")
            
        if not self.entries:
            self.parse()
            
        if out_dir is None:
            base_name = os.path.splitext(os.path.basename(self.filepath))[0]
            out_dir = base_name.lower()

        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        # Write metadata file
        meta_file_path = os.path.join(out_dir, "__META.bigheader")
        with open(meta_file_path, 'w') as meta_file:
            meta_file.write(f"{self.header['magic']}\n")
            meta_file.write(f"{self.header['archive_size']}\n")
            meta_file.write(f"{self.header['num_files']}\n")
            meta_file.write(f"{self.header['header_size']}\n")

        # Extract all files
        with open(self.filepath, 'rb') as f:
            for entry in self.entries:
                file_offset = entry["file_offset"]
                file_length = entry["file_length"]
                file_path = entry["file_path"]
                output_path = os.path.join(out_dir, file_path)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                f.seek(file_offset)
                data = f.read(file_length)
                with open(output_path, 'wb') as out_file:
                    out_file.write(data)
                print(f"Extracted: {output_path} (Size: {file_length} bytes)")
                
        return out_dir
    
    def patch_parameters(self, mod_params: List[ModParameter]) -> Optional[str]:
        """
        Patch parameters in the BIG archive based on ModParameter objects.
        
        Args:
            mod_params: List of ModParameter objects with patch details
            
        Returns:
            Path to the patched file or None if no patching was done
        """
        if not mod_params:
            print("No mod parameters provided.")
            return None
            
        if not self.filepath:
            raise ValueError("No archive file loaded.")
            
        if not self.entries:
            self.parse()
            
        # Group mod parameters by the inner file
        params_by_inner_file = {}
        for param in mod_params:
            norm_inner = self.normalize_path(param.inner_file)
            params_by_inner_file.setdefault(norm_inner, []).append(param)
        
        print(f"Patching BIG archive: {self.filepath}")
        
        # Read the entire BIG archive into memory
        with open(self.filepath, 'rb') as f:
            archive_data = bytearray(f.read())
        
        # Process each inner file
        for inner_file_norm, params in params_by_inner_file.items():
            # Locate the file entry by matching normalized file paths
            matching_entries = [
                e for e in self.entries if self.normalize_path(e['file_path']) == inner_file_norm
            ]
            if not matching_entries:
                print(f"File '{inner_file_norm}' not found in archive.")
                continue
            
            entry = matching_entries[0]
            offset = entry['file_offset']
            length = entry['file_length']
            
            # Extract file content
            file_data = archive_data[offset:offset+length]
            try:
                file_text = file_data.decode('utf-8')
            except UnicodeDecodeError:
                file_text = file_data.decode('cp1252', errors='replace')
            
            original_length = len(file_text)
            patched_text = file_text
            
            # Apply each mod parameter
            for param in params:
                try:
                    patched_text = self._patch_ini_content(patched_text, param.parameter_name, param.target_value)
                    print(f"Patched parameter '{param.parameter_name}' in '{param.inner_file}' to '{param.target_value}'.")
                except ValueError as ve:
                    print(ve)
            
            # Ensure that the patched content length remains unchanged
            if len(patched_text) != original_length:
                print(f"Warning: Patched content length for '{inner_file_norm}' changed from {original_length} to {len(patched_text)} bytes. Skipping patch for this file.")
                continue
            
            # Encode patched content
            new_file_data = patched_text.encode('utf-8')
            if len(new_file_data) != length:
                print(f"Warning: Encoded patched data length mismatch for '{inner_file_norm}'. Skipping patch for this file.")
                continue
            
            # Replace the file content in the archive
            archive_data[offset:offset+length] = new_file_data
        
        backup_filename = self.filepath + ".OLD"
        try:
            # Rename original file to .OLD
            os.rename(self.filepath, backup_filename)
            # Write patched content to original filename
            with open(self.filepath, 'wb') as f:
                f.write(archive_data)
            print(f"Original file backed up to: {backup_filename}")
            print(f"Patched BIG archive written to: {self.filepath}")
            return self.filepath
        except OSError as e:
            print(f"Error while backing up/writing files: {e}")
            # Try to restore original file if something went wrong
            if os.path.exists(backup_filename):
                try:
                    os.rename(backup_filename, self.filepath)
                except OSError:
                    pass
            return None
    
    @classmethod
    def bundle(cls, folder_path: str, output_file: str) -> 'BigArchive':
        """
        Bundle a folder into a BIG archive file.
        
        Args:
            folder_path: Path to the folder to bundle
            output_file: Path where the BIG archive will be written
            
        Returns:
            A new BigArchive instance loaded from the created file
            
        Raises:
            FileNotFoundError: If the __META.bigheader file is missing
        """
        meta_file_path = os.path.join(folder_path, "__META.bigheader")
        if not os.path.exists(meta_file_path):
            raise FileNotFoundError("__META.bigheader file is missing. Cannot reconstruct the BIG archive.")

        with open(meta_file_path, 'r') as meta_file:
            magic = meta_file.readline().strip().encode('ascii')
            archive_size = int(meta_file.readline().strip())
            num_files = int(meta_file.readline().strip())
            header_size = int(meta_file.readline().strip())

        with open(output_file, 'wb') as big_file:
            big_file.write(magic)
            big_file.write(struct.pack('>III', archive_size, num_files, header_size))

            file_entries = []
            current_offset = header_size

            # Collect all files (excluding metadata file)
            for root, _, files in os.walk(folder_path):
                for file in files:
                    if file == "__META.bigheader":
                        continue
                    file_path = os.path.relpath(os.path.join(root, file), folder_path)
                    with open(os.path.join(root, file), 'rb') as f:
                        file_data = f.read()
                    file_length = len(file_data)
                    file_entries.append((current_offset, file_length, file_path, file_data))
                    current_offset += file_length

            # Write file entries to header
            for offset, length, path, _ in file_entries:
                big_file.write(struct.pack('>II', offset, length))
                big_file.write(path.encode('utf-8') + b'\x00')

            # Write file data
            for _, _, _, data in file_entries:
                big_file.write(data)

        print(f"Bundled archive written to {output_file}")
        return cls(output_file)
    
    @staticmethod
    def _patch_ini_content(content: str, parameter_name: str, new_value: str) -> str:
        """
        Patch a parameter in an INI file content.
        
        Args:
            content: The original INI file content
            parameter_name: The parameter to update
            new_value: The new value to insert
            
        Returns:
            The patched INI file content
            
        Raises:
            ValueError: If the parameter is not found in the content
        """
        pattern = re.compile(r'(^\s*' + re.escape(parameter_name) + r'\s*=\s*)(\S+)(.*)$', re.MULTILINE)
        
        def repl(match):
            prefix = match.group(1)
            old_value = match.group(2)
            suffix = match.group(3)
            # Adjust new_value to match the length of the old value
            if len(new_value) < len(old_value):
                new_val_fixed = new_value + ' ' * (len(old_value) - len(new_value))
            elif len(new_value) > len(old_value):
                new_val_fixed = new_value[:len(old_value)]
            else:
                new_val_fixed = new_value
            return prefix + new_val_fixed + suffix
        
        new_content, count = pattern.subn(repl, content, count=1)
        if count == 0:
            raise ValueError(f"Parameter '{parameter_name}' not found in content.")
        return new_content
    
    @staticmethod
    def normalize_path(path: str) -> str:
        """
        Normalize file paths for consistent comparison.
        
        Converts backslashes to forward slashes, lowercases, and strips extra whitespace.
        
        Args:
            path (str): The file path to normalize.
        
        Returns:
            str: The normalized file path.
        """
        return path.replace("\\", "/").lower().strip()
    
    
    def scan_and_collect_metadata(root_dir: str, output_file: str):
        metadata = {}

        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                if filename.lower().endswith('.big'):
                    big_path = os.path.join(dirpath, filename)
                    try:
                        archive = BigArchive(big_path)
                        sorted_entries = {}

                        for entry in archive.entries:
                            file_path = entry['file_path']
                            file_offset = entry['file_offset']
                            ext = os.path.splitext(file_path)[1].lower() or 'other'
                            
                            if ext not in sorted_entries:
                                sorted_entries[ext] = {}

                            sorted_entries[ext][file_path] = file_offset
                        
                        metadata[filename] = sorted_entries
                        print(f"Scanned {filename} with {len(archive.entries)} entries.")
                    except Exception as e:
                        print(f"Failed to parse {filename}: {e}")

        with open(output_file, 'w') as f:
            json.dump(metadata, f, indent=4)

        print(f"Metadata written to {output_file}")