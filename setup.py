import setuptools
from pathlib import Path

here = Path(__file__).parent.resolve()

# Read requirements.txt line by line, ignoring comments and empty lines
with (here / "requirements.txt").open() as f:
    install_requires = [
        line.strip()
        for line in f
        if line.strip() and not line.startswith("#")
    ]

# Reading the README for the long description
with (here / "README.md").open(encoding="utf-8") as f:
    long_description = f.read()

setuptools.setup(
    name="oriom",
    version="0.1.0",
    python_requires=">=3.9,<3.11",
    packages=setuptools.find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=install_requires,
    author="WavEC - Francisco Correia da Fonseca, Luis Amaral, Riccardo Meda, Alessandra Imperadore, Miguel Matos e Sa",
    author_email="francisco.fonseca@wavec.org, luis.amaral@wavec.org, riccardo.meda@wavec.org",
    description="Open-code tool developed by WavEC to simulate the scheduling and costs of the installation and O&M operations in offshore renewable energy farms, including fixed-bottom offshore wind, floating wind, wave energy and offshore floating solar.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="PolyForm-Shield-1.0.0",
    url="https://github.com/WavEC-Offshore-Renewables/oriom",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
