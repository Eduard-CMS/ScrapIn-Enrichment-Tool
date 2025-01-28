# ScrapIn Email Enrichment Tool

## Overview

This script is designed to automate the enrichment of email and person data using the ScrapIn API. It reads data from a CSV file, processes it by calling the ScrapIn API to enrich the records, and outputs the results as a new CSV file. The tool supports email, first name, last name, and company name enrichment and handles rate limits to ensure smooth processing.

## Features

- **CSV File Input**: Allows users to select a CSV file containing the data to be enriched.
- **API Integration**: Connects to the ScrapIn API for enriching data based on emails, names, or company names.
- **Rate Limit Handling**: Automatically pauses requests when the rate limit of 500 requests per minute is reached.
- **Data Export**: Converts the enriched data to a CSV file with detailed information about the enrichment process.
- **User-Friendly Interface**: A simple popup for entering the ScrapIn API key and selecting the input CSV file.

## Requirements

- Python 3.7+
- Required libraries:
  - `aiohttp`: Asynchronous HTTP client for API requests.
  - `pandas`: Data manipulation and CSV handling.
  - `tqdm`: Progress bar for monitoring the enrichment process.
  - `tkinter`: For the graphical user interface (GUI) elements (e.g., input popup).

Install the required libraries with:

```bash
pip install aiohttp pandas tqdm
