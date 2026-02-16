
## **ORIOM**

Offshore Renewables Installation and O&M (ORIOM) is a Python-based tool developed by WavEC to simulate the scheduling, marine spread, port logistics, and total costs of the installation and O&M operations in offshore renewable energy farms, including fixed-bottom offshore wind, floating wind, wave energy and floating solar. Various functionality can be implemented, averaged results show the most important KPI such as OPEX, availabilities and vessels logs
<br><br>

# INDEX
- [**Table of Contents:**](#table-of-contents)
    - [**License**](#license)
    - [**Intended use**](#intended-use)
    - [**Features**](#features)
    - [**Technologies**](#technologies)
    - [**Deployment**](#deployment)
    - [**Contacts**](#contacts)
<br><br>

## **License**

ORIOM is licensed under the PolyForm Noncommercial License 1.0.0.

You may use, modify, and share ORIOM for noncommercial purposes, including academic research and public projects.
Commercial use is not permitted under this license.  
For any commercial use (including consultancy, integration into commercial software, SaaS platforms, or paid services), a separate commercial license from WavEC – Offshore Renewables is required.
<br><br>

# Intended use:

Allowed without a separate licence (noncommercial):

- MSc and PhD theses using ORIOM.
University courses and internal teaching.
- Public research institutes and universities using ORIOM in research projects.
- Publicly funded R&D projects where results are not sold as a commercial product or service.

Typically commercial (requires a commercial licence from WavEC):

- Using ORIOM in paid consultancy studies for clients.
- Integrating ORIOM into commercial software, SaaS platforms or internal commercial tools.
- Using ORIOM to provide paid optimisation, planning or O&M scheduling services.

If you are unsure whether your use is commercial, please contact us.
## Features:

**Installation Mode** (under improvement)
- How to use Installation Mode

    1) ```
        Create a "dates_failures.csv" compliant to the requirement filled with the devices to be installed
        ```
    2) ```
        In Gen_Inputs link the path of reuse failure events to the "dates_failures.csv" created
        ```
    3)  ```
        Set all strategy failure as deferred with the desired start of the installation
        ```
    4)  ```
        ORIOM will simulate deferred correction of each failure for the year of their occurrency using the set of available vessels. This will represent an installation campaign of devices
        ```
<br>

**Failure variation**

    Modification of failure occurrence are available.
- Modify failure rate by single command:

    ```
    tick "True" to each failure the "fail_variation" attribute (Failure class)
    ```
    
    ```
    set the factor to variation in "Failure ratio sensitivity factor" (SA inputs)
    ```
- Implement bathtub failure distribution:

    ```
    signalize as True to each failure the "bath_tub" attribute (Failure class)
    ```
    
    ```
    set the "Infant mortality" and "period Wear" out period for initial/end year of bathtube curve
    ```
    ```
    set "Failure ratio during these periods" to variation in Failure rates for Bath tub curve (SA inputs)
    ```
- Modify monthly distribution of failure rate

    ```
    set various scenarios in "SA_Scenarios"
    ```
    ```
    activate in main config_run "FAILURE_SCENARIO_SELECTION" selecting the scenario to analyze
    ```

<br>

**Modify and consider two different port distance for O&M**
- How to implement two different port distance
    ```
    activate in main config_run "DIFF_DISTANCE"
    ```

    ```
    indicate in main config_run "VESSEL_DIST_REDUCED_LIST" creating a list of vessel type and indicate "DIFF_KM_DISTANCE"
    ```
<br>

**Statistical duration for short term vessels chart (not available in open source mode)**

- How to implement STATISTICAL_CHART
    ```
    Contact WavEC to access to the full version of ORIOM
    ```

<br>

**Reuse preexisting file to retore previous simulation (not available in open source mode)**

- How to implement Reuse file
    ```
    Contact WavEC to access to the full version of ORIOM
    ```

<br>

**Testing suite**

Unit testing accommodates all project features with test.
- To run coverage tests, use this command in terminal:

    ```
    python -m unittest
    ```
    
    ```
    coverage run --source="." -m pytest
    ```
- Coverage report available with command:

    ```
    coverage report
    ```
- You can also run the command bellow to test all software with a single command.

    ```
    make test_ORIOM:
    ```

<br><br>

## Explanations:

**Installation Mode**
- Simulate an installation campaign of the offshore renewable farm
    - Consider deferred failure to be corrected as devices to be installed
    - Consider a limited number of vessel available
    - Will proced in installing one device after the other till all the deferred failure yearly are all corrected. More year can be simulated to distribute the installation in different periods.
    - Taylored operations and activities must be defined
<br>

**Failure variation**

- Modify the failure generation in various methods
    - create taylored monthly probabilities of failure to simulate weather impact and severities
    - Increase failure rate occurrences for sensitivities analysis
    - Use bath tub failure curve for components that undergoes to initial failure and degradation
<br>


**Modify and consider two different port distance for O&M**
- Consider a different port distance for some specific vessels
<br>

**Statistical duration for short term vessels chart (not available in open source mode)**
- Simulate real logistic scenarios along the O&M lifetime
    - Consider statistical duration of the contract time for short term vessel use considering the monthly statistical duration of the operation to conduct
    - Reutilize available vessels that conducted their task and are still contractually available
    - Recreate a contract for the vessels that did not succeded to complete the task inside the contractual terms. Consider a re-mobilitation of a new vessel if required
<br>

**Reuse preexisting file (not available in open source mode)**
- Reuse previous operation file to avoid regeneration of data  

<br>

**Testing suite**

Unit testing accommodates all project features with test.


## Technologies:

- **Python**    
    - [Python 3.10.10](https://www.python.org/) - Used as base language.

<br><br>

## Deployment:

### Local Deployment:

Please note - in order to run this project locally on your own system, you will need the following installed:
- [Python3.10](https://www.python.org/) to run the application.
- [GIT](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) for version control.

    ## 1. Clone repository
    To clone this repository, open a terminal, go to the directory you want to clone it to. For example `cd C:\Users\<USER_NAME>\ORIOM` and run:

    ```
    git clone git@github.com:WavEC-Offshore-Renewables/oriom.git
    ```
    or

    ```
    git clone https://github.com/WavEC-Offshore-Renewables/oriom.git
    ```
    ## 2. Stay in your current folder, don't navigate into O&M TOOL yet

    ## 3. Instal Logistic Tools
    A virtual environment is recommended for the Python interpreter. Enter the command:
    ```
    python -m venv venv
    ```  
            
    - _Warning : **This Python command may differ** depending on operating system, the command required could be **python3** or **py**_

    ## 4. Navigate into Popflix and initialize the virtual environment by using the following command: 

    ```
    .\venv\Scripts\Activate.ps1 
    ```
    - _Warning : **This command may differ** depending on your operating system_

    ## 5. Install all the requirements and dependancies with the command:

    ```
    pip install .
    ```

    ## 6. Test installation

    ```
    python
    ```

    ```python
    >>> from logistic_tools.test import test
    >>> test()
    ORIOM
    Hello from WavEC - Offshore Renewables Installation and O&M software
    ```

    ## 7.  Logging
    Please, avoid printing text directly to the console. Instead, you should try to use [logging](https://docs.python.org/3/library/logging.html).

    ```python
    import logging
    logging.warning('Watch out!')
    logging.info('I told you so')
    ```

    `logging` is set to `DEBUG` level, meaning every information will be printed to a log file found in `./tmp/run_[YYYYMMDD_HHMMSS]/logging.log`.

    ## 8. Documentation
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

        
    ## 9. SET THE MAIN for the simulation 
    Modify the main.py file from line 57 to 71 to set your simulation and pointing to the excel_input_file
        
    ## 10. You can now run the program locally with the following command: 

    ```
    python main.py 
    ```
    or
    ```
    python -m logistic_tools.main         
    ```
    <br><br>


## Contacts
For commercial licensing and collaboration enquiries:

WavEC – Offshore Renewables
oriom@wavec.org
