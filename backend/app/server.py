from .main import create_app
from .crash_lab import install_crash_handler

app = create_app()
install_crash_handler()
