"""WhatsApp Desk — Aplicación de escritorio GNOME para WhatsApp Web."""

import os
from setuptools import setup, find_packages

setup(
    name="whatsapp-desk",
    version=os.environ.get("WHATSAPP_DESK_VERSION", "1.0.0"),
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
