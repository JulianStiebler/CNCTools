import os
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from typing import Optional

from pygments import highlight
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.formatters import get_formatter_by_name

from .config import config, WindowOptions, PygmentOptions, EditorOptions, GameOptions
from .vfs import VirtualFile, VirtualFileSystem

dir_path = os.path.dirname(os.path.realpath(__file__))

class FileTreeView(ttk.Treeview):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.tag_configure('file', foreground='black')
        self.tag_configure('folder', foreground='navy')
        self.tag_configure('big', foreground='darkgreen')
        self.tag_configure('ini', foreground='blue')
        self.tag_configure('txt', foreground='black')
        self.tag_configure('wnd', foreground='purple')
        self.tag_configure('w3d', foreground='brown')
        self.tag_configure('tga', foreground='orange')
        
        # Add column headings
        self.configure(columns=("path",))
        self.column("#0", width=250, stretch=tk.YES)
        self.column("path", width=0, stretch=tk.NO)  # Hidden column for path
        
        # Configure double-click to expand/collapse folders and open files
        self.bind("<Double-1>", self.on_double_click)
        
    def on_double_click(self, event):
        """Handle double click on tree item"""
        item = self.identify_row(event.y)
        if not item:
            return
            
        tags = self.item(item, "tags")
        if "folder" in tags or "big" in tags:
            # Toggle expand/collapse
            if self.item(item, "open"):
                self.item(item, open=False)
            else:
                self.item(item, open=True)
        
    def build_tree(self, structure, parent=""):
        """Recursively build tree from structure dictionary"""
        # Clear existing items if building from root
        if parent == "":
            for item in self.get_children():
                self.delete(item)
        
        for name, data in sorted(structure.items(), key=lambda x: (x[1]['type'] != 'folder', x[0])):
            item_type = data['type']
            tags = [item_type]
            
            if item_type == 'file':
                # Add file extension tag for styling
                ext = data.get('ext', '').lstrip('.')
                if ext:
                    tags.append(ext)
                    
            # Insert the item
            item_id = self.insert(
                parent, "end", text=name, 
                values=(data.get('path', ''),), 
                tags=tags,
                open=False
            )
            
            # Recursively add children if any
            if 'children' in data:
                self.build_tree(data['children'], item_id)

class CodeEditor(ScrolledText):
    def __init__(self, master, **kwargs):
        super().__init__(master, wrap='none', undo=True, **kwargs)
        
        # Default font and size
        font_size = config.cget(EditorOptions.FONT_SIZE)
        self.configure(font=("Courier New", font_size))
        
        # Current file being edited
        self.current_file: Optional[VirtualFile] = None
        
        # Setup key bindings
        self.bind('<Control-s>', lambda e: self.save_current())
        
        # Last auto-save time
        self.last_autosave = time.time()
        
        # Line numbers
        self.show_line_numbers = config.cget(EditorOptions.SHOW_LINE_NUMBERS)
        if self.show_line_numbers:
            self._setup_line_numbers()
    
    def _setup_line_numbers(self):
        self.line_numbers = tk.Text(
            self.master, width=4, pady=2, 
            takefocus=0, bd=0, bg='#f0f0f0',
            highlightthickness=0, fg='gray'
        )
        self.line_numbers.pack(side=tk.LEFT, fill=tk.Y)
        
        # Configure font to match editor
        self.line_numbers.configure(font=self.cget("font"))
        
        # Prevent editing line numbers
        self.line_numbers.configure(state="disabled")
        
        # Update line numbers when scrolling or editing
        self.bind('<KeyRelease>', self._update_line_numbers)
        self.bind('<ButtonRelease>', self._update_line_numbers)
        self.bind('<Configure>', self._update_line_numbers)
        
    def _update_line_numbers(self, event=None):
        if not hasattr(self, 'line_numbers'):
            return
            
        self.line_numbers.configure(state="normal")
        self.line_numbers.delete("1.0", "end")
        
        # Get number of lines
        num_lines = int(self.index('end-1c').split('.')[0])
        
        # Generate line numbers text
        line_numbers_text = '\n'.join(str(i) for i in range(1, num_lines + 1))
        self.line_numbers.insert("1.0", line_numbers_text)
        
        # Align line numbers right
        for i in range(1, num_lines + 1):
            self.line_numbers.tag_add("right", f"{i}.0", f"{i}.end")
            self.line_numbers.tag_configure("right", justify='right')
        
        # Match editor's scroll position
        top_index = self.index("@0,0")
        top_line = int(top_index.split('.')[0])
        self.line_numbers.yview_moveto(float(top_line) / num_lines)
        
        self.line_numbers.configure(state="disabled")
    
    def open_file(self, vfile: VirtualFile):
        """Open a virtual file in the editor"""
        # Check for unsaved changes
        if self.current_file and self.current_file.is_modified:
            if messagebox.askyesno("Unsaved Changes", 
                                "There are unsaved changes. Save before opening a new file?"):
                self.save_current()
        
        self.current_file = vfile
        
        # Get file content
        try:
            content = vfile.get_text_content()
        except Exception as e:
            messagebox.showerror("Error Opening File", f"Could not open {vfile.name}: {str(e)}")
            return False
        
        # Clear editor and insert content
        self.delete("1.0", "end")
        self.insert("1.0", content)
        
        # Apply syntax highlighting
        self.highlight_syntax()
        
        # Update line numbers
        if self.show_line_numbers:
            self._update_line_numbers()
            
        # Reset undo/redo stack
        self.edit_reset()
        
        return True
    
    def highlight_syntax(self):
        """Apply syntax highlighting to current content"""
        if not self.current_file:
            return
            
        # Get appropriate lexer
        try:
            lexer = get_lexer_for_filename(self.current_file.name)
        except Exception:
            # Fallback to text lexer
            lexer = TextLexer()
        
        # Get style from config
        style = config.cget(PygmentOptions.STYLE)
        
        # Get current text
        text = self.get("1.0", "end")
        
        # Apply highlighting
        formatter = get_formatter_by_name('html', 
                                        style=style,
                                        full=False)
        _ = highlight(text, lexer, formatter)
        
        # Parse HTML and apply to Text widget
        # This requires converting the HTML to text with appropriate Tkinter tags
        # For simplicity in this example, we're just setting the text
        # A full implementation would parse the HTML and apply tags
        
        # Just for demonstration - real implementation would apply tags for colors
        self.delete("1.0", "end")
        self.insert("1.0", text)
    
    def check_autosave(self):
        """Check if autosave is due and perform save if needed"""
        if not self.current_file:
            return
            
        autosave_interval = config.cget(EditorOptions.AUTO_SAVE_INTERVAL)
        if autosave_interval <= 0:
            return
            
        now = time.time()
        if now - self.last_autosave > autosave_interval:
            self.save_current(autosave=True)
            self.last_autosave = now
    
    def save_current(self, autosave=False):
        """Save the current file"""
        if not self.current_file:
            return False
            
        try:
            # Get content from editor
            content = self.get("1.0", "end-1c")  # Exclude final newline
            
            # Save to virtual file
            self.current_file.save(content)
            
            # If not autosave, commit changes
            if not autosave:
                self.current_file.commit()
                
            return True
        except Exception as e:
            if not autosave:  # Don't show errors for autosave
                messagebox.showerror("Save Error", f"Failed to save {self.current_file.name}: {str(e)}")
            return False

class CNCToolsIDE(tk.Tk):
    def __init__(self):
        super().__init__()

        self.vfs = VirtualFileSystem()
        
        # Configure window
        self.title("CNCTools IDE")
        window_size = config.cget(WindowOptions.WINDOW_SIZE)
        self.geometry(f"{window_size[0]}x{window_size[1]}")
        
        # Set up main layout
        self.setup_layout()
        
        # Configure menu
        self.setup_menu()
        
        # Autosave timer
        self.after(1000, self.check_autosave)
        
        # Check for last opened folder
        last_folder = config.cget(GameOptions.LAST_GAME_FOLDER)
        if last_folder and os.path.exists(last_folder):
            self.load_game_directory(last_folder)
    
    def setup_layout(self):
        # Main paned window (sidebar | editor)
        self.paned_window = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Sidebar frame
        self.sidebar_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.sidebar_frame, weight=1)
        
        # Search frame in sidebar
        self.search_frame = ttk.Frame(self.sidebar_frame)
        self.search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Search entry and button
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_entry.bind('<Return>', self.perform_search)
        
        self.search_button = ttk.Button(self.search_frame, text="Search", 
                                       command=self.perform_search)
        self.search_button.pack(side=tk.RIGHT)
        
        # File tree
        self.file_tree = FileTreeView(self.sidebar_frame, selectmode="browse")
        self.file_tree.pack(fill=tk.BOTH, expand=True)
        self.file_tree.bind("<<TreeviewSelect>>", self.on_file_selected)
        
        # Editor frame
        self.editor_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.editor_frame, weight=4)
        
        # Code editor
        self.code_editor = CodeEditor(self.editor_frame)
        self.code_editor.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_bar = ttk.Label(self, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Set pane weights according to config
        ratios = config.cget(WindowOptions.MAIN_PANE_RATIOS)
        if len(ratios) >= 2:
            total = sum(ratios)
            screen_width = self.winfo_screenwidth()
            self.paned_window.sashpos(0, int(screen_width * ratios[0] / total))

    def setup_menu(self):
        menubar = tk.Menu(self)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Game Folder", command=self.open_game_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self.code_editor.save_current)
        file_menu.add_command(label="Save All", command=self.save_all)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Recent folders submenu
        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Folders", menu=self.recent_menu)
        self.update_recent_menu()
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", command=lambda: self.code_editor.event_generate("<<Undo>>"))
        edit_menu.add_command(label="Redo", command=lambda: self.code_editor.event_generate("<<Redo>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", command=lambda: self.code_editor.event_generate("<<Cut>>"))
        edit_menu.add_command(label="Copy", command=lambda: self.code_editor.event_generate("<<Copy>>"))
        edit_menu.add_command(label="Paste", command=lambda: self.code_editor.event_generate("<<Paste>>"))
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        # Set the menu
        self.config(menu=menubar)
    
    def update_recent_menu(self):
        """Update the list of recent folders in the menu"""
        # Clear current items
        self.recent_menu.delete(0, tk.END)
        
        # Add recent folders
        recent_folders = config.cget(GameOptions.RECENT_FOLDERS)
        if not recent_folders:
            self.recent_menu.add_command(label="(No recent folders)", state=tk.DISABLED)
        else:
            for folder in recent_folders:
                if os.path.exists(folder):
                    self.recent_menu.add_command(
                        label=folder,
                        command=lambda f=folder: self.load_game_directory(f)
                    )
    
    def open_game_folder(self):
        """Open a game folder dialog"""
        folder = filedialog.askdirectory(
            title="Select Command & Conquer Game Folder",
            initialdir=config.cget(GameOptions.LAST_GAME_FOLDER) or "/"
        )
        
        if folder:
            self.load_game_directory(folder)
    
    def load_game_directory(self, folder_path):
        """Load a game directory into the IDE"""
        self.status_bar.config(text=f"Loading {folder_path}...")
        self.update_idletasks()
        
        try:
            # Load the virtual filesystem
            self.vfs.load_game_directory(folder_path)
            
            # Build file tree
            structure = self.vfs.get_file_structure()
            self.file_tree.build_tree(structure)
            
            # Update recent folders
            self.update_recent_menu()
            
            self.status_bar.config(text=f"Loaded {folder_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load game directory: {str(e)}")
            self.status_bar.config(text="Ready")
    
    def on_file_selected(self, event):
        """Handle file selection in tree view"""
        selection = self.file_tree.selection()
        if not selection:
            return
            
        item = selection[0]
        item_type = self.file_tree.item(item, "tags")[0]
        
        if item_type == "file":
            # Get virtual path
            virtual_path = self.file_tree.item(item, "values")[0]
            
            # Get file from VFS
            vfile = self.vfs.get_file(virtual_path)
            if vfile:
                # Open in editor
                if self.code_editor.open_file(vfile):
                    self.status_bar.config(text=f"Opened {vfile.path}")
    
    def save_all(self):
        """Save all modified files"""
        # First save current file in editor if any
        if self.code_editor.current_file:
            self.code_editor.save_current()
        
        # Then save any other modified files
        count = self.vfs.save_all_modified()
        self.status_bar.config(text=f"Saved {count} files")
    
    def check_autosave(self):
        """Check for autosave"""
        self.code_editor.check_autosave()
        self.after(1000, self.check_autosave)  # Schedule next check

    def perform_search(self, event=None):
        """Search for files matching the search term"""
        search_term = self.search_var.get().strip().lower()
        if not search_term:
            return
        
        # Clear search results
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        if not self.vfs.loaded:
            self.file_tree.insert("", "end", text="No game loaded", tags=["folder"])
            return
        
        # Create search results structure
        results = {"Search Results": {"type": "folder", "path": "", "children": {}}}
        result_count = 0
        
        # Search through all files
        for virtual_path, file in self.vfs.files.items():
            if search_term in file.name.lower():
                # Get extension
                ext = os.path.splitext(file.name)[1].lower()
                
                # Add to results
                results["Search Results"]["children"][file.name] = {
                    "type": "file",
                    "path": virtual_path,
                    "ext": ext
                }
                result_count += 1
        
        # Display results
        self.file_tree.build_tree(results)
        
        # Expand search results
        for item in self.file_tree.get_children():
            self.file_tree.item(item, open=True)
        
        self.status_bar.config(text=f"Found {result_count} matching files")

def run_ide():
    """Run the CNCTools IDE"""
    app = CNCToolsIDE()
    app.mainloop()

if __name__ == "__main__":
    run_ide()