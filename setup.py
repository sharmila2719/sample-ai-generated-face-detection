"""Package setup — allows `pip install -e .` for local development."""

from setuptools import find_packages, setup

setup(
    name="sample-ai-generated-face-detection",
    version="1.0.0",
    packages=find_packages(exclude=["tests*", "infrastructure*"]),
    python_requires=">=3.12",
    install_requires=[
        "boto3>=1.35.0",
        "pillow>=10.4.0",
    ],
)
