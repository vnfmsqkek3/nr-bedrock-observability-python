from setuptools import setup, find_packages

def read_version():
    with open("src/nr_bedrock_observability/__init__.py", "r") as f:
        for line in f:
            if line.startswith("__version__"):
                # __version__ = "0.1.0" -> 0.1.0
                return line.split("=")[1].strip().strip('"')
    return "0.0.0"

setup(
    name="nr-bedrock-observability-python",
    version="2.2.0",
    description="AWS Bedrock monitoring library for New Relic with complete automation",
    author="YourName",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/nr-bedrock-observability-python",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "boto3>=1.28.0",
        "newrelic>=8.0.0",
        "streamlit>=1.28.0"
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    keywords=["aws", "bedrock", "observability", "monitoring", "llm", "newrelic", "telemetry", "streamlit"],
    entry_points={
        "console_scripts": [],
    },
) 