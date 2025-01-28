import asyncio
import aiohttp
import pandas as pd
import json
from tempfile import NamedTemporaryFile
from tqdm import tqdm
from tkinter import Tk, simpledialog, messagebox
from tkinter.filedialog import askopenfilename
import math
import time

# Initialize global variables for API key and URL
API_KEY = None
API_URL = 'https://api.scrapin.io/enrichment'

# Rate limit control variables
requests_made = 0
start_time = time.time()

# Function to get the API Key from user via pop-up
def get_api_key():
    global API_KEY
    root = Tk()
    root.withdraw()  # Hide the main window
    API_KEY = simpledialog.askstring("API Key", "Please enter your ScrapIn API Key:")
    if not API_KEY:
        messagebox.showerror("Error", "API Key is required!")
        exit()  # Exit if API key is not provided
    
    # Print the API key to check if it's captured correctly
    print(f"API Key: {API_KEY}")  # This line will show the API key
    
    root.quit()

# Function to manage rate limit and pause if necessary
def manage_rate_limit():
    global requests_made, start_time
    if requests_made >= 500:
        elapsed_time = time.time() - start_time
        if elapsed_time < 60:
            sleep_time = 60 - elapsed_time  # Time to sleep to complete 60 seconds
            print(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds.")
            time.sleep(sleep_time)  # Sleep until the start of the next minute
        requests_made = 0  # Reset the request counter for the next minute
        start_time = time.time()  # Reset the timer

# Function to call the ScrapIn API and get enriched data for email or person search
async def enrich_data(email=None, first_name=None, last_name=None, company_name=None, session=None):
    global requests_made

    # Check rate limit before making a request
    manage_rate_limit()

    try:
        params = {'apikey': API_KEY}

        # Add the query parameters as needed
        if email:
            params['email'] = email
        if first_name:
            params['firstName'] = first_name
        if last_name:
            params['lastName'] = last_name
        if company_name:
            params['companyName'] = company_name
        
        # Debug print: Check what parameters are being sent to the API
        print(f"Sending parameters: {params}")

        async with session.get(API_URL, params=params) as response:
            # Log the API response status
            print(f"Response Status for {email or first_name + ' ' + last_name or company_name}: {response.status}")

            if response.status == 200:
                result = await response.json()
                # Log the response JSON
                print(f"API Response for {email or first_name + ' ' + last_name or company_name}: {json.dumps(result, indent=2)}")
                requests_made += 1  # Increment the request count
                return {"success": True, "data": result}
            else:
                print(f"Error for {email or first_name + ' ' + last_name or company_name}: {response.status}")
                return {"success": False, "error": f"Failed with status code {response.status}"}
    except Exception as e:
        print(f"Exception for {email or first_name + ' ' + last_name or company_name}: {e}")
        return {"success": False, "error": str(e)}

# Function to process CSV for email enrichment and save as temporary JSON
async def process_csv_to_temp_json(input_csv):
    df = pd.read_csv(input_csv)
    tasks = []
    results = []

    with tqdm(total=len(df), desc="Enriching Data", unit="entry") as pbar:
        async with aiohttp.ClientSession() as session:
            for _, row in df.iterrows():
                # Check for NaN values and skip or mark with failure reason
                email = row.get('email', None)
                first_name = row.get('firstName', '')
                last_name = row.get('lastName', '')
                company_name = row.get('companyName', '')

                # Explicit check for NaN values before processing
                if isinstance(email, float) and math.isnan(email):
                    email = None
                if isinstance(first_name, float) and math.isnan(first_name):
                    first_name = None
                if isinstance(last_name, float) and math.isnan(last_name):
                    last_name = None
                if isinstance(company_name, float) and math.isnan(company_name):
                    company_name = None

                # Check if email, first name, or last name is NaN, and handle them
                if not email and not first_name and not last_name:
                    results.append({
                        "email": email,
                        "firstName": first_name,
                        "lastName": last_name,
                        "companyName": company_name,
                        "status": "Failed: Missing email, first name, or last name"
                    })
                    pbar.update(1)
                    continue  # Skip this row

                # Check if email is available and valid
                if email:
                    # Enrich using email
                    tasks.append(enrich_data(email=email, session=session))
                elif first_name and last_name:
                    # Enrich using first name and last name
                    tasks.append(enrich_data(first_name=first_name, last_name=last_name, company_name=company_name, session=session))
                elif first_name:
                    # Enrich using first name
                    tasks.append(enrich_data(first_name=first_name, company_name=company_name, session=session))
                elif last_name:
                    # Enrich using last name
                    tasks.append(enrich_data(last_name=last_name, company_name=company_name, session=session))

            # Collect all results from the enrichment process
            for future in asyncio.as_completed(tasks):
                result = await future
                results.append(result)
                pbar.update(1)

    temp_file = NamedTemporaryFile(delete=False, suffix=".json")
    with open(temp_file.name, 'w') as f:
        json.dump(results, f, indent=4)

    return temp_file.name, results

# Function to convert JSON to CSV with unique columns for all API response data
def json_to_csv(json_file, original_file_name, enrichment_results):
    flattened_data = []
    for idx, entry in enumerate(enrichment_results):
        flattened_row = entry.copy()  # Copy the data

        # Check if the entry was successful or failed
        if entry.get("success", False):
            api_data = entry.get("data", {})
            # Flattening API data (can be extended as per requirement)
            for key, value in api_data.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        flattened_row[f"{key}_{sub_key}"] = sub_value
                else:
                    flattened_row[key] = value
            flattened_row['status'] = 'Success'
        else:
            flattened_row['status'] = f"Failed: {entry.get('error', 'No error message')}"
        
        flattened_data.append(flattened_row)

    # Write the flattened data to a CSV file
    df = pd.DataFrame(flattened_data)
    output_csv = f"{original_file_name}_results.csv"
    df.to_csv(output_csv, index=False)

# Main function to select task and run accordingly
async def main():
    get_api_key()  # Prompt user for API Key

    # Ask the user to upload the CSV file
    input_csv = askopenfilename(title="Select your CSV file", filetypes=(("CSV files", "*.csv"), ("All files", "*.*")))

    original_file_name = input_csv.split("/")[-1].split(".")[0]

    # Process the CSV to automatically detect whether to use email or person search
    temp_json, enrichment_results = await process_csv_to_temp_json(input_csv)
    json_to_csv(temp_json, original_file_name, enrichment_results)
    print(f"Enriched data saved to {original_file_name}_results.csv")

# Run the main function
asyncio.run(main())
