from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="pyfback",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="期货回测系统 - Python期货量化交易回测框架",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/pyfback",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.2.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
        ],
        "enhanced": [
            "tushare>=1.2.0",
            "yfinance>=0.2.0",
            "scikit-learn>=1.3.0",
            "joblib>=1.3.0",
            "dask>=2023.1.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "pyfback=pyfback.cli:main",
        ],
    },
)