import sys
sys.stdout = sys.stderr
sys.path.append('/var/www/robot/')
from robot import app as application
