import os
import time
import pandas as pd
import requests
import sys

# Configuration
FOLDER_PATH = "ai_majority_articles.csv"  # Input CSV file
OUTPUT_FOLDER = "output"  # Output folder  
API_URL = "https://api.gptzero.me/v2/predict/text"
API_KEY = "YOUR_API_KEY_GOES_HERE."  # Add your API key here
HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json"
}
MAX_WORKERS = 4  
RETRY_DELAY = 70 * 60  # 70 minutes delay for retry

# Ensure output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def countdown_timer(seconds):
    """Displays a live countdown timer in HH:MM:SS format."""
    while seconds > 0:
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        sys.stdout.write(f"API limit exceeded for this file. Retrying in {hours:02}:{minutes:02}:{seconds:02}...")
        sys.stdout.flush()
        time.sleep(1)
        seconds -= 1
    print("Resuming this file...")

def send_request(text):
    """Sends a request to the API and handles rate limiting per file."""
    payload = {"document": text, "multilingual": False}
    while True:
        try:
            print(f"Sending request for text: {text[:30]}...")  
            response = requests.post(API_URL, json=payload, headers=HEADERS, timeout=60)  # Added timeout
            if response.status_code == 200:
                print(f"Received response for text: {text[:30]}...") 
                return response.json()
            elif response.status_code == 429 or "exceeded your usage threshold" in response.text:
                print("API limit reached for this file. Pausing only this file for 1 hour 10 minutes.")
                countdown_timer(RETRY_DELAY)  # Wait 70 minutes
            else:
                print(f"Error: {response.text}")
                return {"error": response.text}
        except requests.exceptions.Timeout:
            print("Timeout occurred. Retrying the request...")
        except requests.exceptions.RequestException as e:
            print(f"Error occurred during API request: {e}")
            return {"error": str(e)}

def process_file(file_path):
    """Processes a single CSV file with API request handling."""
    try:
        print(f"Reading file: {file_path}")
        df = pd.read_csv(file_path)
        if "inputText" not in df.columns or "File" not in df.columns or "GPTZero" not in df.columns or df.empty:
            print(f"Skipping {file_path}: Missing required columns or empty file.")
            return False

        # Filter for rows where GPTZero column is AI
        filtered_df = df[df["GPTZero"] == "AI"]

        if filtered_df.empty:
            print(f"No AI content found in {file_path}. Skipping.")
            return False

        texts = filtered_df["inputText"].dropna().tolist()
        file_entries = filtered_df["File"].dropna().tolist()

        responses = []
        for text in texts:
            responses.append(send_request(text))  # Process each text individually

        # Add "File" column back to results
        result_df = pd.DataFrame(responses)
        result_df.insert(0, "File", file_entries[:len(result_df)])

        # Save results to specific output file
        output_file = os.path.join(OUTPUT_FOLDER, f"processed_{os.path.basename(file_path)}")
        result_df.to_csv(output_file, index=False)
        print(f"Saved results to {output_file}")

        return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Process the CSV file while handling API rate limits."""
    print(f"Starting processing of the file: {os.path.basename(FOLDER_PATH)}...")
    
    while not process_file(FOLDER_PATH):  # Retry failed files after 70 minutes
        print(f"Retrying file: {os.path.basename(FOLDER_PATH)} after 1 hour 10 minutes...")
        countdown_timer(RETRY_DELAY)

    print("File processed successfully!")

if __name__ == "__main__":
    main()
