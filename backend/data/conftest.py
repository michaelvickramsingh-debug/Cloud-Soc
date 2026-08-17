import sys, os
backend_dir = os.path.abspath(os.path.dirname("/Users/micvic/code/CloudSoc/Cloud-Soc/Cloud-Soc/backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)