# MEI Customization Service

This web application provides a web-based front-end to the [TEI Stylesheets](https://github.com/TEIC/Stylesheets) to create
schemas for validating MEI XML files based on an MEI Customization.

## What is a customization?

A customization is a version of MEI that is tailored to validating a specific type of MEI file. For example,
 a customization that validates a MEI document containing common Western music notation (CWMN) will disable the functionality 
 contained in MEI for representing other types of notation (Tablature, Mensural, or Neume). A customization will disable
 the features for representing these types of notation, and produce a schema that is suited to only validate CWMN documents.

## Installing this web application

This web application uses the [Flask](http://flask.pocoo.org) web application server, and the [Celery](http://celery.readthedocs.org)
 processing queue system to generate the schema files. This section will cover the installation and configuration of the TEI Stylesheets, the Web application,
 and the Celery system.
 
***Caveat*** These instructions are written for Linux or Macintosh systems. They will not work for Windows systems.
 
### Installing the stylesheets

Check out the latest version of the TEI Stylesheets from https://github.com/TEIC/Stylesheets. You will need to install the `ant`
Java build tool to get these to run.

### Installing the web application

The easiest way to install the web application is to use a Python Virtual Environment. This will keep all of your modules self-contained
so you do not have any conflicts with other installations of Python.

To install virtualenv (all commands should be typed at the command line):

`$>sudo pip install virtualenv`

Once virtualenv is installed, you should get the latest version of this web application. The easiest way to do this is to
check it out via git:

`$> git clone https://github.com/music-encoding/customeization`

Inside of the `customeization` folder, create your virtual environment and activate it, e.g.,

`$> virtualenv customeization_env`
`$> source customeization_env/bin/activate`

(you will notice that your prompt changes to include the name of your environment):

`(customeization_env)$>`

To install the dependencies for the software, you can use the included `requirements.txt` file which will download and install
the Python modules:

`(customeization_env)$> pip install -r requirements.txt`

This will install the Python modules in your virtual environment. **NB**: This means that they will only be available after you've
activated your virtual environment (see the "source ..." command above).

Once this is done, you should also install the [RabbitMQ](http://www.rabbitmq.com) server system, which Celery depends on. This
is generally available in the package manager systems (yum, apt, homebrew) for the individual platforms.

This should be enough to get the system up and running.

## Configuring the web application

Copy the `conf.py.dist` file to `conf.py`. Edit this file to point to specific paths on your system. The `MEI_SVN_SOURCE_DIR`
 and the `BUILD_DIR` are perhaps the most important. These identify, respectively, the absolute paths to a checkout of the MEI source from 
 Google Code, and the directory where the built schemata will be stored (temporarily) for download. You must also fill in the
 absolute path to the TEI Stylesheets.
 
## Running the web application

Once everything is installed you will need to run two commands to start the system. The first is to run the Python web application
itself; the second is to run the Celery processing queue. To start the Python server:

`(customeization_env)$> python customeization.py`

This will start a web server locally running at `http://127.0.0.1:5000`.

To start the Celery server, open a new terminal window and activate the virtual environment:

`(customeization_env)$> celery -A customeization.celery worker`

## Ready to go

Once everything is up and running you should be able to visit `http://localhost:5000` in your web browser and start generating
customizations from the application server.

# Deploying

Deploying the application server is unnecessary if you just want to run the application locally. However, if you want to serve 
it publicly you should serve it using some more robust tools than the built-in web server system.

The deployment has been tested with Nginx (web server), uwsgi (WSGI application server), and Supervisor (process manager). There
are startup scripts in this system for starting the uwsgi and celery servers (`start.sh` and `start_celery.sh`) that also take care
of activating the virtual environment as needed.

## NginX Configuration

Here is a sample configuration for the NginX deployment:

```
server {
	server_name	custom.example.org;
	access_log	/var/log/nginx/access_log;
	error_log	/var/log/nginx/error_log;

	location / {
		try_files $uri @customeization;
	}

	location @customeization {
		include uwsgi_params;
		uwsgi_pass unix:/var/run/customeization_uwsgi.sock;
	}
}
```

## Supervisor Configuration

Here is a sample configuration for the Supervisor system:

```
[program:customeization]
command=/var/webapps/customeization/start.sh
directory=/var/webapps/customeization
user=www
autostart=true
autorestart=true
redirect_stderr=true

[program:customeization-celery]
command=/var/webapps/customeization/celery_start.sh
directory=/var/webapps/customeization
user=www
autostart=true
autorestart=true
redirect_stderr=true
```