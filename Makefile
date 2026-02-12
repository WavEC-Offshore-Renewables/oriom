documentation_build:
# Activate virtual environment
	.\venv\Scripts\activate
# Delete previous build
	del /Q .\docs\build\html
# Get logistic_tools docstrings
	sphinx-apidoc -f -e -o docs/source/_api ./src/logistic_tools src/logistic_tools/main.py
# Create HTML documentation
	sphinx-build -b html docs/source/ docs/build/html


install_package:
# Install package for users
	pip install .


dev:
# Install package for developers
	pip install -e .


test_ORIOM:
# Enter src package
	cd src
# Run the tests
	coverage run --source=logistic_tools -m pytest -s
# Show the reports
	coverage report