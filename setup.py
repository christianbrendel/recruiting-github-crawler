import setuptools

__version__ = None
exec(open("github_crawler/_version.py").read())

with open("README.md", "r", encoding="UTF-8") as fh:
    long_description = fh.read()

install_requires = ["PyGithub", "pandas", "loguru", "tqdm"]

setuptools.setup(
    name="github-crawler",
    version=__version__,
    author="Christian Brendel",
    author_email="brendel.chris@gmail.com",
    description="GitHub Crawler",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7.8",
    install_requires=install_requires,
    include_package_data=True,
)
