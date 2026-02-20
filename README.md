# ORIOM - Offshore Renewables Installation and O&M

![PyPI - Python Version](https://img.shields.io/badge/python-3.9%20%7C%203.10-blue)
[![PolyForm-Shield 1.0.0](https://img.shields.io/badge/Licence-PolyForm--Shield%201.0.0-green)](https://polyformproject.org/licences/shield/1.0.0/)

ORIOM (Offshore Renewables Installation and O&M) is an open-code Python-based modelling tool developed by **WavEC Offshore Renewables** to simulate and assess **installation** and **operations & maintenance (O&M)** logistics and costs for offshore renewable energy projects, including (but not limited to) **fixed-bottom offshore wind, floating wind, wave energy, and floating solar**.

ORIOM supports scenario-based simulation of:
- **Scheduling** and operational sequencing
- **Marine spread** definition and vessel utilisation (including vessel logs)
- **Port logistics**, mobilisation, and demobilisation assumptions
- **Cost build-up** and aggregated project KPIs

ORIOM has been developed and used over multiple years in WavEC R&D projects and consulting activities and is published primarily to improve **transparency, peer review, and reproducibility** of published analyses.

## Contents
- [Citation](#citation)
- [Licence](#licence)
- [Key features](#key-features)
- [Contributing](#contributing)
- [Installation](#installation)
- [Usage](#usage)
- [Testing](#testing)
- [Contact](#contact)

---

## Citation

If you use ORIOM in academic work, reports, or benchmarking studies, please cite it as:

> WavEC Offshore Renewables, *ORIOM — Offshore Renewables Installation and O&M*, 2026.
> (Please include repository URL and the version/tag used.)

---

## Licence

ORIOM is made available under the **PolyForm Shield License 1.0.0** (see `LICENCE`).

### Summary
- You may **use, modify, and redistribute** ORIOM for purposes that **do not compete** with WavEC Offshore Renewables.
- You may **not** use ORIOM to provide products or services that **compete** with WavEC’s line of business (see `LICENCE` for the governing definition of “compete”).
- Use of the Software for **AI/ML training** is **prohibited** without a separate written licence (see `LICENCE`).

If you are unsure whether a planned use competes, contact us: **oriom@wavec.org**.

### Examples of use

Examples of uses that are typically compatible (non-competing):
- Academic research (MSc/PhD work, open-access publications)
- Teaching and internal training
- Internal evaluation, benchmarking, or decision support within an organisation, where results are not offered as a competing external service/product

Examples of uses that are typically competing and therefore **not permitted without a separate agreement**:
- Providing third-party consulting, planning, optimisation, or design verification services based on ORIOM
- Packaging ORIOM into a product/SaaS offering offered to third parties in a competing market

**This section is non-binding guidance. The `LICENCE` file governs.**

---

## Key features

### Installation mode (under improvement)
Simulates an installation campaign by representing installable devices as deferred “events” to be executed using a constrained set of available vessels.

### Failure variation options
Supports sensitivity studies through:
- Failure-rate scaling
- Bathtub-shaped failure distributions
- Monthly failure distribution scenarios

### Port distance differentiation
Optional configuration to apply different port distances to subsets of vessel types.

### Testing suite
Automated tests are provided to cover key features and regression behaviour.

---

## Contributing

Contributions are welcome, but **subject to review and approval by WavEC Offshore Renewables**. ORIOM is published primarily for transparency and reproducibility and is not operated as a community-driven open-source project.

### What we’re most likely to accept
- Bug fixes and robustness improvements
- Documentation and examples
- Tests and reproducibility improvements
- Performance improvements that do not change model intent

### How to propose a change
1. Open an issue describing the problem and the proposed approach (or email us for sensitive topics).
2. If the change is in scope, submit a pull request referencing the issue.

### Contribution terms
By submitting a pull request, you confirm that:
- you have the right to submit the code (no third-party code with incompatible terms); and
- you grant WavEC Offshore Renewables the right to use, modify, and redistribute your contribution as part of ORIOM under the repository’s licence (PolyForm Shield License 1.0.0).

If your employer or institution requires a separate contributor agreement, contact us first: **oriom@wavec.org**.

We may not be able to respond to every request. Unapproved pull requests may be closed without merging.

---

## Installation

### Prerequisites
- [Python 3.10](https://www.python.org/) - tested
- Git

### 1) Clone the repository
Using SSH:
```bash
git clone git@github.com:WavEC-Offshore-Renewables/oriom.git
```

Or HTTPS:
```bash
git clone https://github.com/WavEC-Offshore-Renewables/oriom.git
```

Then:
```bash
cd oriom
```

### 2) Create and activate a virtual environment (recommended)

Create:
```bash
python -m virtualenv venv
```

Activate:

- Windows (PowerShell):
```powershell
.\venv\Scripts\Activate.ps1
```

- Windows (cmd):
```bat
venv\Scripts\activate.bat
```

- Linux/macOS:
```bash
source venv/bin/activate
```

Upgrade pip:
```bash
python -m pip install --upgrade pip
```

### 3) Install ORIOM

Install dependencies and install the package in editable mode:
```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

### 4) Quick verification
Run:
```bash
python
```
```python
>>> from oriom.test import test
>>> test()
ORIOM
Hello from ORIOM by WavEC - Offshore Renewables
```

---

## Usage

ORIOM is currently run via repository entry points (e.g., `main.py` or the `oriom.main` module). The key requirement is to point the configuration to your Excel input file.

### 1) Configure your run
In [`main.py`](src\oriom\main.py), update the configuration (lines 72-86) so that:
- `EXCEL_FILE_PATH` points to the directory containing your Excel input file
- `FORM_NAME` matches the Excel filename

Example:
```python
DEFAULT_CONFIG = ConfigRun(
        STATISTICAL_CHART=True,
        DIFF_DISTANCE=True,
        DIFF_KM_DISTANCE=5,
        KM_MOTHER_VESSEL=5,
        VESSEL_DIST_REDUCED_LIST=['ctv', 'sv'],
        FUEL_TO_ADD={},
        MOBILISATION_TO_ADD={},
        ENERGY_AVAILABILITY_CALCULATION=True,
        ENERGY_STATISTICAL_CALCULATION=False,
        PROJECT_NAME='TEST_TO_USE',
        BASEFILES_FROM_EXCEL=False,
        EXCEL_FILE_PATH=r'C:\Users\<USER>\...\oriom\tests\test_files\test_end_to_end',
        SOURCE_PATH_SHAREPOINT='',
        FORM_NAME='form_v8_test.xlsx',
        TIME_FAIL_OP_IMMEDIATELY=0.02,
)
```

### 2) Run
From the repository root:
```bash
python main.py
```

Or as a module:
```bash
python -m oriom.main
```

### 3) Logging
Avoid printing directly to the console; use Python’s `logging` module:
```python
import logging
logging.warning('Watch out!')
logging.info('FYI: ...')
```

Logging is configured at `DEBUG` level. The log file is written under:
- `./tmp/run_[YYYYMMDD_HHMMSS]/logging.log`

### 4) Documentation (Sphinx)
This repository can generate HTML documentation with Sphinx.

Install documentation dependencies:
```bash
python -m pip install sphinx sphinx-rtd-theme
```

Generate API stubs and build HTML docs:
```bash
sphinx-apidoc -f -e -o docs/source/_api ./src/oriom src/oriom/main.py
sphinx-build -b html docs/source/ docs/build/html
```

If you have `make` available in your system, you can run:
```bash
make documentation_build
```

Open:
- [./docs/build/html/index.html](docs\build\html\index.html)

---

## Testing

All newly added code must include corresponding unit tests. As a minimum quality requirement, only branches with **80% test coverage or higher** will be considered.

### Run tests
Using `unittest`:
```bash
python -m unittest
```
Using `pytest`:
```bash
python -m pip install pytest
python -m pytest -q
```

### Run coverage
Install coverage:
```bash
python -m pip install coverage
```

Run tests with coverage:
```bash
python -m coverage run --source=oriom -m pytest -q
python -m coverage report
```

If you have `make` available in your system, you can run:
```bash
make test
```

---

## Contact

For commercial licencing and collaboration enquiries:

WavEC – Offshore Renewables
**oriom@wavec.org**
