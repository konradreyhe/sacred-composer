"""Sacred Composer — Pattern-based deterministic music composition."""

from setuptools import setup, find_packages

setup(
    name="sacred-composer",
    version="1.0.0",
    description="Deterministic music composition from mathematical and natural patterns",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Konrad Reyhe",
    url="https://github.com/KonradReyhe/MUSIK",
    packages=find_packages(include=["sacred_composer", "sacred_composer.*", "composer", "composer.*"]),
    python_requires=">=3.10",
    install_requires=[
        "midiutil",
        "numpy",
    ],
    extras_require={
        "api": ["fastapi", "uvicorn[standard]"],
        "audio": ["pyfluidsynth"],
        "notation": ["music21"],
        "optimize": ["optuna"],
        "discord": ["discord.py"],
        "dev": ["pytest"],
    },
    entry_points={
        "console_scripts": [
            "sacred-compose=sacred_composer.builder:_cli_entry",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Sound/Audio :: MIDI",
        "Topic :: Scientific/Engineering :: Mathematics",
    ],
)
