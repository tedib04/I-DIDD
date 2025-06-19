## _ODADD_: A Tool for Real-Time Discovery of Data-Aware DECLARE Process Models

**Authors**: Tedi Ibershimi (Free University of Bozen-Bolzano), Fabrizio Maria Maggi (Free University of Bozen-Bolzano), Marco Comuzzi (Ulsan National Institute of Science and Technology)

## Table of contents
  - [Overview](#overview)
  - [Installation](#installation)
  - [Architecture](#architecture)
  - [Repository structure](#repository-structure)
  - [License](#license)

## Overview
This repository contains all the materials related to the implementation of *ODDAD*, the first and only tool that fully supports the discovery of Data-Aware DECLARE Process Models from event logs, using an approach based on *Typed Automata*.

## Installation
1. Ensure [_Docker_](https://www.docker.com/get-started/) and [_Python 3.10_](https://www.python.org/downloads/) is installed on your machine.
2. Clone this repository and copy `.env.example` into `.env`, possibly editing it (just creating `.env` is enough). Please note that here must be specified the _tagged event log_ that should be used to perform model discovery.

```bash
  $  git clone git@github.com:tedib04/ODADD.git
  $  cd ODADD/
  $  cp .env.example .env
```

3. Install _Lydia_ backend using Docker:

In Linux and MacOS machines, the following commands should work:
```bash
  $ docker pull whitemech/lydia:latest
  $ echo '#!/usr/bin/env sh' > lydia
  $ echo 'docker run -v$(pwd):/home/default whitemech/lydia lydia "$@"' >> lydia
  $ sudo chmod u+x lydia
  $ sudo mv lydia /usr/local/bin/
```
While for Windows machines, make a `.bat` file and add it to your PATH variable:
```bash
  $ docker run --name lydia -v"%cd%":/home/default whitemech/lydia lydia %*
```

More information about the installation can be found [here](https://github.com/whitemech/logaut).

4. Run the application using the following command:
```bash
  $  /.runner.sh
```

Once all the previous command are performed correctly, a web interface displaying the process data will be shown to you. This interface is continuously updated with the newly available analytics, as new processes are executed. 

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

- `producer:` Contains the code responsible for replaying event streams from a given event log.
- `processor:` Contains the code that processes the initial dataset by performing various analyses and producing the results to a Kafka topic, from which they are read by the frontend server.
- `frontend:` Contains the implementation of the application's frontend.
- `experiments:` Contains the experiments utils and results.

## License
The code for this application is distributed under the MIT license, please check the [**LICENSE**](../Thesis/LICENSE) file for more information.
