import sys
import os

# Add the parent directory (backend root) to the python path 
# so the 'app' module can be imported correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
