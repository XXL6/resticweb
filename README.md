# resticweb

Basic WEB UI for the [Restic](https://github.com/restic/restic) backup application built for fun using Flask framework.
Application still under development so parts are likely unfinished/broken.

The app can be run with the following steps for now:

* Install python3
* Install pip
* Install pipenv by using pip
* Run ```pipenv install``` in the main project folder where the pipfiles are located. (ignore if psutil and few others fail to install on Linux, as they are only used on Windows)
* Run ```pipenv shell``` to start the virtual environment.
* ```python ./run.py``` or ```python3 ./run.py``` Will start flasks' built-in web server which will listen on port 8080
  * The port can be changed within the run.py file and the host can be removed if the server should not listen over the local network.
  * The debug parameter can be set to True to enable debugging, but I would also suggest turning off the auto_reloader as otherwise it will interfere with the scheduling thread.
  

**Note:** This app does not come with a restic executable. Download one from https://github.com/restic/restic for Windows or Linux and either add it to the PATH or add the executable under resticweb\engine folder and rename it to either 'restic' or 'restic.exe'.

Some pages have a little question mark button in the upper-right hand corner. Clicking it will open up a modal with more information about said page.
