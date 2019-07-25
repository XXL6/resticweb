# resticweb

Basic WEB UI for the [Restic](https://github.com/restic/restic) backup application built for fun using Flask framework.
Application still under development so parts are likely unfinished/broken.

Executables/packages will come in the future, for now the app can be run in development mode with the following steps:

* Install python3
* Install pip
* Install pipenv by using pip
* Run ```pipenv install``` in the main project folder where the pipfiles are located.
* Run ```pipenv shell``` to start the virtual environment.
* ```python ./run.py``` Will start the development web server which will listen on port 8080
* The port can be changed within the run.py file and the host can be removed if the server should not listen over the local network.

**Note:** This app does not come with a restic executable. Download one from https://github.com/restic/restic for Windows or Linux and either add it to the PATH or add the executable under resticweb\engine folder and rename it to either 'restic' or 'restic.exe'.

Documentation and instructions on how to use the app will come soon.

