"""
Allows the package to be run as a script.

Example:
    python -m nzrapi --help
"""

from nzrapi.cli import app

if __name__ == "__main__":
    app()
