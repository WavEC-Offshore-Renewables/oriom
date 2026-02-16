# ORIOM — Offshore Renewables Installation and O&M

ORIOM (Offshore Renewables Installation and O&M) is a open-code  Python-based modelling tool developed by **WavEC Offshore Renewables** to simulate and assess **installation** and **operations & maintenance (O&M)** logistics and costs for offshore renewable energy projects, including (but not limited to) **fixed-bottom offshore wind, floating wind, wave energy, and floating solar**.

ORIOM supports scenario-based simulation of:
- **Scheduling** and operational sequencing
- **Marine spread** definition and vessel utilisation (including vessel logs)
- **Port logistics**, mobilisation, and demobilisation assumptions
- **Cost build-up** and aggregated project KPIs

ORIOM has been developed and used over multiple years in WavEC R&D projects and consulting activities and is published primarily to improve **transparency, peer review, and reproducibility** of analyses.

## Contents
- [Citation](#citation)
- [License](#license)
- [Key features](#key-features)
- [Installation](#installation)
- [Contact](#contact)

---
## Citation

If you use ORIOM in academic work, reports, or benchmarking studies, please cite it as:

> WavEC Offshore Renewables, *ORIOM — Offshore Renewables Installation and O&M*, 2026.  
> (Please include repository URL and version/tag used.)

## License

ORIOM is made available under the **PolyForm Shield License 1.0.0** (see `LICENSE`).

### Summary
- You may **use, modify, and redistribute** ORIOM for purposes that **do not compete** with WavEC Offshore Renewables.
- You may **not** use ORIOM to provide products or services that **compete** with WavEC’s line of business (see `LICENSE` for the governing definition of “compete”).
- Use of the Software for **AI/ML training** is **prohibited** without a separate written licence (see `LICENSE`).

If you are unsure whether a planned use competes, contact us: **oriom@wavec.org**.

### Example of uses

Examples of uses that are typically compatible (non-competing):
- Academic research (MSc/PhD work, publications)
- Teaching and internal training
- Internal evaluation, benchmarking, or decision support within an organisation, where results are not offered as a competing external service/product

Examples of uses that are typically competing and therefore **not permitted without a separate agreement**:
- Providing third-party consulting, planning, optimisation, or design verification services based on ORIOM as a substitute for WavEC’s services
- Packaging ORIOM into a product/SaaS offering offered to third parties in a competing market

**This section is non-binding guidance. The `LICENSE` file governs.**

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

------

## Installation

### Prerequisites
- [Python 3.10.10](https://www.python.org/) - Used as base language.
- Git

### 1. Clone repository
To clone this repository, open a terminal, go to the directory you want to clone it to. For example `cd C:\Users\<USER_NAME>\ORIOM` and run:

```
git clone git@github.com:WavEC-Offshore-Renewables/eu-scores.git
```
or

```
git clone https://github.com/WavEC-Offshore-Renewables/eu-scores.git
```
### 2. Stay in your current folder, don't navigate into O&M TOOL yet

### 3. Instal Logistic Tools
A virtual environment is recommended for the Python interpreter. Enter the command:
```
python -m venv venv
```  
        
- _Warning : **This Python command may differ** depending on operating system, the command required could be **python3** or **py**_

### 4. Navigate into Popflix and initialize the virtual environment by using the following command: 

```
.\venv\Scripts\Activate.ps1 
```
- _Warning : **This command may differ** depending on your operating system_

### 5. Install all the requirements and dependancies with the command:

```
pip install .
```

### 6. Test installation

```
python
```

```python
>>> from logistic_tools.test import test
>>> test()
ORIOM
Hello from WavEC - Offshore Renewables Installation and O&M software
```

### 7.  Logging
Please, avoid printing text directly to the console. Instead, you should try to use [logging](https://docs.python.org/3/library/logging.html).

```python
import logging
logging.warning('Watch out!')
logging.info('I told you so')
```

`logging` is set to `DEBUG` level, meaning every information will be printed to a log file found in `./tmp/run_[YYYYMMDD_HHMMSS]/logging.log`.

### 8. Documentation
ORIOM repository is prepared t produce HTML documentation with [Sphinx](https://www.sphinx-doc.org/en/master/).

To do so, follow the next commands o produce docuentation source file:

**Note**: *Do not run this command if you want to keep the current documentation format.*
        
1) Activate virtual environment:

```
.\venv\Scripts\activate
```

2) Delete previous build:

```
del /Q .\docs\build\html
```

3) Get logistic_tools docstrings:

```
sphinx-apidoc -f -e -o docs/source/_api ./src/logistic_tools src/logistic_tools/main.py
```
        
4) Create HTML documentation:

```
sphinx-build -b html docs/source/ docs/build/html
```
You can also run the command bellow to test all software with a single command.

```
make test_ORIOM:
```

The documentation can be found in `./docs/build/html/index.html`

    
### 9. SET THE MAIN for the simulation 
Modify the main.py file from line 57 to 71 to set your simulation and pointing to the excel_input_file
    
### 10. You can now run the program locally with the following command: 

```
python main.py 
```
or
```
python -m logistic_tools.main         
```
<br><br>


## Contact
For commercial licensing and collaboration enquiries:

WavEC – Offshore Renewables
oriom@wavec.org
