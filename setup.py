"""Setup script for the Hairstyle Analyzer package."""

from setuptools import setup, find_packages

setup(
    name="hairstyle_analyzer",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        line.strip() for line in open("requirements.txt") if not line.startswith("#")
    ],
    python_requires=">=3.9",
    description="AI-powered hairstyle image analysis and title generation system",
    author="Claude AI",
    author_email="example@example.com",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
