NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

from .nodes import SaveStringToTextNode, SaveImageToFolderNode, LoadTextFilesNode

NODE_CLASS_MAPPINGS["SaveStringToTextNode"] = SaveStringToTextNode
NODE_DISPLAY_NAME_MAPPINGS["SaveStringToTextNode"] = "Save String to Text File"

NODE_CLASS_MAPPINGS["SaveImageToFolderNode"] = SaveImageToFolderNode
NODE_DISPLAY_NAME_MAPPINGS["SaveImageToFolderNode"] = "Save Image to Folder"

NODE_CLASS_MAPPINGS["LoadTextFilesNode"] = LoadTextFilesNode
NODE_DISPLAY_NAME_MAPPINGS["LoadTextFilesNode"] = "Load Text Files from Folder"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]