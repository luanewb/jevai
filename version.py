"""
Version tracking module for Jev AI Binance Trading Bot.
Strict adherence to version increment rule on every feature/fix.
"""

__version__ = "1.0.3"

def get_version() -> str:
    return __version__

def bump_version(part: str = "patch") -> str:
    """
    Increments version (patch: 1.0.0 -> 1.0.1, minor: 1.0.0 -> 1.1.0, major: 1.0.0 -> 2.0.0)
    and updates version.py file in place.
    """
    import re
    from pathlib import Path

    version_file = Path(__file__).resolve()
    content = version_file.read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    current = m.group(1) if m else "1.0.0"
    parts = list(map(int, current.split(".")))
    
    if part == "major":
        parts[0] += 1
        parts[1] = 0
        parts[2] = 0
    elif part == "minor":
        parts[1] += 1
        parts[2] = 0
    else:  # patch
        parts[2] += 1

    new_version = f"{parts[0]}.{parts[1]}.{parts[2]}"
    
    version_file = Path(__file__).resolve()
    content = version_file.read_text(encoding="utf-8")
    updated = re.sub(r'__version__\s*=\s*"[^"]+"', f'__version__ = "1.0.1"', content)
    version_file.write_text(updated, encoding="utf-8")
    
    return new_version

if __name__ == "__main__":
    print(f"Current version: {get_version()}")
