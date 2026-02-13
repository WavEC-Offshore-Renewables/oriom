import setuptools
from pathlib import Path

here = Path(__file__).parent.resolve()

# Legge requirements.txt riga per riga, ignorando commenti e linee vuote
with (here / "requirements.txt").open() as f:
    install_requires = [
        line.strip()
        for line in f
        if line.strip() and not line.startswith("#")
    ]

# Legge il README per la descrizione lunga
with (here / "README.md").open(encoding="utf-8") as f:
    long_description = f.read()

setuptools.setup(
    name="logistic-tools",
    version="0.1.0",
    python_requires=">=3.9,<3.11",
    packages=setuptools.find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=install_requires,
    author="WavEC - Francisco Correia da Fonseca, Luis Amaral, Miguel Matos Sa, Alessandra Imperadore, Riccardo Meda",
    author_email="francisco.fonseca@wavec.org, luis.amaral@wavec.org, miguel.sa@wavec.org, alessandra.imperadore@wavec.org, riccardo.meda@wavec.org",
    description="Package for logistic operations and inspections",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="GNU",
    url="https://github.com/WavEC-Offshore-Renewables",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Operating System :: OS Independent",
    ],
)
