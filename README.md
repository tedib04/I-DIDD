## _I-DiDD_: A Tool for the Incremental Discovery of Data-Aware Declare Models

**Authors**: Tedi Ibershimi (Free University of Bozen-Bolzano), Fabrizio Maria Maggi (Free University of Bozen-Bolzano), Marco Comuzzi (Ulsan National Institute of Science and Technology)

## Table of contents
  - [Overview](#overview)
  - [Installation](#installation)
  - [Architecture](#architecture)
  - [Repository structure](#repository-structure)
  - [License](#license)

## Overview
This repository contains all the materials related to the implementation of *I-DiDD*, the first and only tool that fully supports the incremental discovery of Data-Aware DECLARE Process Models from event logs.

## Installation
1. Ensure [_Docker_](https://www.docker.com/get-started/), [_Python 3.10_](https://www.python.org/downloads/), _JAVA 11_ and [_Graphviz_](https://graphviz.org/download) is installed on your machine.
2. Clone this repository.

```bash
  $  git clone https://github.com/tedib04/I-DIDD.git
  $  cd I-DIDD/
```

3. Copy `.env.example` into `.env` . In this file you can configure the ports of the running processes as well as the event log file to use for the discovery. By default, the demo is preconfigured to use the event log specified in this file. The event log must be located under `experiments/data/tagged/` and must be _tagged_ before use by running the script found in `experiments/src/`. Tagging is required to add an attribute to each event indicating whether it is the last event in a trace. This information is essential for the discovery process to function correctly.


On Linux/macOS, use the following command:

```bash
  $  cp .env.example .env
```

On Windows:
```bash
  $  copy .env.example .env
```


4. Install _Lydia_ backend using Docker:

Download the Lydia Docker image:

```bash
  $ docker pull whitemech/lydia:latest
 ```

On Linux and MacOS machines use the following commands:
```bash
  $ echo '#!/usr/bin/env sh' > lydia
  $ echo 'docker run -v$(pwd):/home/default whitemech/lydia lydia "$@"' >> lydia
  $ sudo chmod u+x lydia
  $ sudo mv lydia /usr/local/bin/
```

On Windows machines, make a `.bat` file and add it to your PATH variable:
```bash
  $ docker run --name lydia -v"%cd%":/home/default whitemech/lydia lydia %*
```

More information about the installation of _Lydia_ can be found [here](https://github.com/whitemech/logaut).

5. Run the application:

On Linux/macOS:
```bash
  $  ./runner.sh
```

On Windows:
```bash
  $  runner.bat
```
Once all the previous command are performed correctly, a web interface displaying the process mininig dashboard will be shown to you. This interface is continuously updated with the newly available analytics, as new processes are executed. 

Once the application is started, the following web UIs can be accessed:
- Kafka UI: http://localhost:28080/
- Flink UI http://localhost:8081/
- Streamlit frontend: http://localhost:8888/

## Architecture

The architecture of this project consist of the following components:

* `Kafka + Kafka UI` - Containing a single broker (KRaft mode) with Kafka UI accessible at http://localhost:28080/.
* `Python producer` - Ingests data into a Kafka `raw-process-events`topic.
* `Flink processor` - Computes dashboard statistics, performs _Online Data-Aware DECLARE Model Discovery_, and stores the results back to Kafka into the `dashboard-result` topic.
* `Schema Registry` - Manages schema evolution for the process data.
* `Web frontend` - Displays the latest process analytics, and it is accessible at  http://localhost:8888/.

## Repository Structure
- `assets:` Contains the pictures of the _easyDeclare_ patterns.
- `experiments:` Contains the experiments utils and results.
- `frontend:` Contains the implementation of the application's frontend.
- `producer:` Contains the code responsible for replaying event streams from a given event log.
- `processor:` Contains the code that processes the initial dataset by performing various analyses and producing the results to a Kafka topic, from which they are read by the frontend server.

## License
The code for this application is distributed under the MIT license, please check the [**LICENSE**](../Thesis/LICENSE) file for more information.
