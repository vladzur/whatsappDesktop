"""WhatsApp Desk — Aplicación de escritorio GNOME para WhatsApp Web."""

import os
import re
from setuptools import setup, find_packages


def _package_version():
    """Lee __version__ del paquete sin importarlo (evita cargar GI/GTK)."""
    path = os.path.join(os.path.dirname(__file__), "whatsapp_desk", "__init__.py")
    with open(path, encoding="utf-8") as f:
        match = re.search(r'^__version__ = "([^"]+)"', f.read(), re.MULTILINE)
    return match.group(1) if match else "0.0.0"


setup(
    name="whatsapp-desk",
    version=os.environ.get("WHATSAPP_DESK_VERSION", _package_version()),
    description="GNOME desktop application for WhatsApp Web",
    author="Vladzur",
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "whatsapp-desk=whatsapp_desk.application:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: GTK",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Topic :: Communications :: Chat",
    ],
)
