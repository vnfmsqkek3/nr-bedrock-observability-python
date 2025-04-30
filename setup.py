from setuptools import setup, find_packages

setup(
    name="nr-bedrock-observability",
    version="1.1.1",
    description="New Relic observability for AWS Bedrock",
    author="New Relic",
    author_email="opensource@newrelic.com",
    url="https://github.com/newrelic/nr-bedrock-observability-python",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "newrelic>=8.0.0",
        "boto3>=1.28.0",
        "botocore>=1.31.0"
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "twine>=4.0.0",
            "build>=1.0.0",
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
    keywords=["aws", "bedrock", "observability", "monitoring", "llm", "newrelic", "telemetry"],
) 