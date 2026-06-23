from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="agrisage",
    version="1.0.0",
    description="SDK Python officiel pour l'API AgriSage — conseil phytosanitaire Maroc",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="AgriSage",
    author_email="api@agrisage.ma",
    url="https://github.com/agrisage/sdk-python",
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.8",
    install_requires=[],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Agriculture",
    ],
    keywords=["agrisage", "phytosanitaire", "maroc", "onssa", "api", "agriculture"],
    project_urls={
        "Documentation": "https://docs.agrisage.ma",
        "Bug Reports":   "https://github.com/agrisage/sdk-python/issues",
        "Source":        "https://github.com/agrisage/sdk-python",
    },
)
