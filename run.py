import sys
import os

# Add current dir to path
sys.path.append(os.getcwd())

from fcli.main import app

if __name__ == "__main__":
    app()
