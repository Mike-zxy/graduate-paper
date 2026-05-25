"""
Utility functions for file operations.
"""
import os
from typing import List, Union


def walkFile(dir_path):
    """
    Recursively walk through all files in a directory.

    Args:
        dir_path (str): Directory path to walk through

    Returns:
        list: List of all file paths in the directory (relative or absolute based on input)
    """
    files = []

    if not os.path.exists(dir_path):
        print(f"Warning: Directory '{dir_path}' does not exist")
        return files

    try:
        for root, dirs, filenames in os.walk(dir_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                files.append(file_path)
    except PermissionError as e:
        print(f"Permission error accessing '{dir_path}': {e}")

    return files


def load_file(file_path):
    """
    Load and return the content of a file.

    Args:
        file_path (str): Path to the file

    Returns:
        str: File content as string, or None if file cannot be read

    Raises:
        FileNotFoundError: If file does not exist
        IOError: If file cannot be read
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found")
        raise
    except IOError as e:
        print(f"Error reading file '{file_path}': {e}")
        raise


def save_file(out_dir: str, stem: str, content: Union[str, List[str]]):
    """
    Save content to `<out_dir>/<stem>-output.json`.

    `content` is typically a list of chat turns (strings) or a single string.
    """
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{stem}-output.json")
    import json

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    return out_path


def add_file(record_path: str, file_path: str):
    """
    Append a file path to a record file (one per line), creating parent dirs if needed.
    """
    parent = os.path.dirname(record_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(record_path, "a", encoding="utf-8") as f:
        f.write(file_path)
        if not file_path.endswith("\n"):
            f.write("\n")
