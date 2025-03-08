from typing import Union
from enum import Enum, EnumMeta
from os import makedirs
from os.path import exists as pathexists
import json

ConfigEnum = Union[Enum, EnumMeta]

class WindowOptions(Enum):
    MAIN_PANE_RATIOS = [0.2, 0.8]  # Left sidebar vs main editor ratio
    WINDOW_SIZE = (1200, 800)      # Default window size
    
class PygmentOptions(Enum):
    STYLE = "default"
    STYLE_OVERRIDES = {}
    GENERAL_OVERRIDES = {}
    
class EditorOptions(Enum):
    AUTO_SAVE_INTERVAL = 30        # Seconds between auto-saves
    FONT_SIZE = 12
    SHOW_LINE_NUMBERS = True
    TAB_SIZE = 4
    
class GameOptions(Enum):
    LAST_GAME_FOLDER = ""          # Last opened game folder
    RECENT_FOLDERS = []            # List of recently opened folders
    
class GeneralOptions(Enum):
    TEMP_DIR = "temp"              # For temporary file extractions
    BACKUP_DIR = "backups"         # For backing up original BIG files
    
config_enums = [WindowOptions, PygmentOptions, EditorOptions, GameOptions, GeneralOptions]


class CNCToolsConfig:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(CNCToolsConfig, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self,                       # Instance reference
        save_folder="data",         # Folder where the configuration file will be saved
        config_file="config.json",  # Name of the configuration file (JSON format)
        save_override=None,         # Callback function to be executed astead ours
        load_override=None          # Callback function to be executed astead ours
    ):
        if self._initialized:
            return
        
        self._initialized = True
        self.config_enums = config_enums
        self.save_folder = save_folder
        self.config_file = f"{save_folder}/{config_file}"
        if not pathexists(save_folder):
            makedirs(save_folder, exist_ok=True)

        self.save_override = save_override
        self.load_override = load_override

        self.options = {} # Will store loaded and dynamically set options, nested dictionary
        self.options_load() # Load configuration at initialization


    def cget(self, config_key: ConfigEnum):
        if not isinstance(config_key, Enum):
            raise TypeError("Expected a ConfigEnum member for key")

        category_name = config_key.__class__.__name__.replace("Options", "").lower() # Extract category from Enum class name
        key_name = config_key.name.lower() # Extract key name from Enum member name

        return self.options.get(category_name, {}).get(key_name, config_key.value) # Options override Enum defaults


    def cset(self, config_key: ConfigEnum, value, save=False):
        if not isinstance(config_key, Enum):
            raise TypeError("Expected a ConfigEnum member for key")

        category_name = config_key.__class__.__name__.replace("Options", "").lower()
        key_name = config_key.name.lower()

        if category_name not in self.options:
            self.options[category_name] = {} # Create category dict if it doesn't exist yet
        self.options[category_name][key_name] = value # Set the option value
        if save:
            self.options_save() # Save config to file if save=True

    def get(self, key, default=None):
        return self.options.get(key, default)

    def set(self, key, value, save=False):
        self.options[key] = value
        if save:
            self.options_save() # Save config to file if save=True

    def options_load(self):
        loaded_config_data = None # Initialize to None to track if callback provided data

        if callable(self.load_override):
            loaded_config_data = self.load_override() # Use custom load callback if provided
            if isinstance(loaded_config_data, dict): # Check if callback returned a dictionary
                self.options = loaded_config_data # Use dictionary from callback directly as options
                return # Exit function after using callback, skipping file load

        # If load_callback was not used, or didn't return a dict, proceed with file loading:
        loaded_config_data = {} # Initialize for file loading path
        try:
            with open(self.config_file, "r") as f:
                loaded_config_data = json.load(f) # Load from JSON file
            if not isinstance(loaded_config_data, dict): # Basic check for valid JSON root
                print("Warning: Config file root is not a dictionary. Ignoring file data.")
                loaded_config_data = {} # Treat as empty if invalid root
        except (IOError, json.JSONDecodeError) as e:
            print(f"Config load error: {e}")
            loaded_config_data = {} # Treat as empty on load errors

        merged_options = {} # Dictionary to store merged configuration

        for category_enum_class in self.config_enums: # Iterate through the list of passed-in Enum classes
            category_name_lower = category_enum_class.__name__.replace("Options", "").lower() # Derive category name
            merged_category = {} # Dictionary to store merged options for the current category

            if category_name_lower in loaded_config_data and isinstance(loaded_config_data[category_name_lower], dict):
                merged_category.update(loaded_config_data[category_name_lower]) # Load category data from file if available and is a dict

            for enum_member in category_enum_class: # Iterate through members of the current Enum class
                default_value = enum_member.value # Get default value from Enum member
                if isinstance(default_value, dict): # Handle dictionary default values specifically
                    merged_category_option = merged_category.get(enum_member.name.lower(), {}) # Start with empty dict if no loaded data
                    merged_category_option.update(default_value) # Merge default dict into loaded data (or empty dict)
                    merged_category[enum_member.name.lower()] = merged_category_option # Assign merged dict back to category option
                elif enum_member.name.lower() not in merged_category: # For non-dict defaults, apply default only if not loaded
                    merged_category[enum_member.name.lower()] = default_value # Apply Enum default if not found in loaded data

            merged_options[category_name_lower] = merged_category # Add merged category options to main options dict

        self.options = merged_options # Update self.options with the merged configuration


    def options_save(self):
        if callable(self.save_override):
            override_result = self.save_override(self.options)
            if override_result is not None:
                # Override handled saving – skip default file write.
                return

        # Proceed with default file saving if override wasn't used.
        config_to_save = self.options
        try:
            with open(self.config_file, "w") as f:
                json.dump(config_to_save, f, indent=4)
        except IOError as e:
            print(f"Config save error: {e}")
            
config = CNCToolsConfig()