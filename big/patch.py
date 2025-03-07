from dataclasses import dataclass

@dataclass
class ModParameter:
    """
    Data class representing a modifiable parameter in a BIG archive.
    
    Attributes:
        big_file (str): The BIG archive file name (e.g., "INIZH.big").
        inner_file (str): The relative path of the file within the BIG archive 
                          (e.g., "Data/INI/Default/GameData.ini").
        parameter_name (str): The name of the parameter in the INI file (e.g., "MaxCameraHeight").
        default_value (str): The default value of the parameter.
        current_value (str): The new value to patch into the file.
        description (str): A description of what this parameter controls.
    """
    big_file: str
    inner_file: str
    parameter_name: str
    default_value: str
    target_value: str
    description: str = ""

@dataclass
class TargetParameters:
    CAMERA_HEIGHT_MAX = ModParameter(
        big_file="INIZH.big",
        inner_file=r"Data\INI\GameData.ini",
        parameter_name="MaxCameraHeight",
        default_value="1000.0",
        target_value="600.0",
        description="Maximum camera height in the game."
    )