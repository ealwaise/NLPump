# Project Overview
---
NLPump is a project attempting to apply natural language processing to stepcharts (sequences of steps in time to a particular song) from the arcade rhythm game Pump it Up. It's natural to think of steps as "letters" and sequences of steps as "words", so an NLP analysis of
stepcharts seems promising. In fact, such techniques have been [applied](https://medium.com/@brentbiseda/ddr-difficulty-classifier-with-fastai-nlp-part-1-847af2648e07) to Dance Dance Revolution, a similar rhythm game. Some of the goals of NLPump are:

* Serialization - Convert stepcharts into a format convenient for NLP.
* Pattern Search - Search stepcharts for particular step patterns.
* Stepchart Analytics - Extract insights from pattern data, such as associations between patterns and difficulty.
* Pattern Prediction - Predict the next step in a sequence given some number of prior steps.
* Difficulty Prediction - Predict the difficulty of a stepchart based on step patterns.
* Classification - Categorize/cluster stepcharts according to step patterns found within.

# User Guide
---
To use NLPump, you first need to generate the stepchart data. This will require an .ssc file directory, which should consist of "pack" folders, each of which should contain "song" folders. An .ssc file should be within each song folder. Follow the steps below:

* Run ``ssc_crawler.py`` (found in the ``src`` subfolder of the NLPump directory) from the command line.
* You will receive user prompts to enter in the path to your .ssc directory, the names of the pack folders you wish to process, and the name of the .csv file you wish to output.
* After running the script, a .csv file with the chosen name should be found in the ``data`` subfolder of the NLPump directory. You can now open a Jupyter notebook and read in this .csv file to search for step patterns, as illustrated by the example in the ``notebooks`` subfolder of the NLPump directory.

# Directory Structure
---

The following folders can be found within the main project directory:

* data - Contains an example .csv file containing serialized stepcharts.
* notebooks - Contains a Jupyter notebook illustrating how to search for step patterns.
* src - Contains the source code.

# Dependencies
---
This project was conducted in a Python 3.11.5 environment with the following packages installed:

* pandas 2.1.4
* numpy 1.26.4