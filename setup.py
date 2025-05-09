from setuptools import setup, find_packages

def read_version():
    with open("src/nr_bedrock_observability/__init__.py", "r") as f:
        for line in f:
            if line.startswith("__version__"):
                # __version__ = "0.1.0" -> 0.1.0
                return line.split("=")[1].strip().strip('"')
    return "0.0.0"

setup(
    name="nr-bedrock-observability",
    version="1.5.0",
    description="New Relic observability for AWS Bedrock",
    author="New Relic",
    author_email="info@newrelic.com",
    url="https://github.com/newrelic/nr-bedrock-observability-python",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "boto3>=1.26.0",
        "newrelic>=8.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.3.1",
            "pytest-cov>=4.1.0",
            "black>=23.3.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
        ],
        "streamlit": [
            "streamlit>=1.22.0",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Monitoring",
    ],
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    keywords=["aws", "bedrock", "observability", "monitoring", "llm", "newrelic", "telemetry", "streamlit"],
    entry_points={
        "console_scripts": [],
    },
) 