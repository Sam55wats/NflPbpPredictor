import pandas as pd
import requests
import os

BASE_URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp"
DIRECTORY = "nfl_pbp_csvs"

#download play_by_play CSV files from the nflfastr repository from 1999 to 2024
def download_pbp_csvs(base_url, directory, start_year=2016, end_year=2023):
    os.makedirs(directory, exist_ok=True) # creates directory if it doesn't exists

    for year in range(start_year, end_year + 1):
        #filename = f"play_by_play_{year}.csv"
        filename = f"pbp_participation_{year}.csv"
        url = f"{base_url}/{filename}"
        path = os.path.join(directory, filename)

        if not os.path.exists(path):
            r = requests.get(url, stream=True)
            if r.status_code == 200:
                with open(path, 'wb') as file:
                    for chunk in r.iter_content(chunk_size=10*1024):
                        file.write(chunk)
            else:
                print(f"Failed to download {filename}: {r.status_code}")
        else:
            print(f"{filename} already exists, skipping download.")
    print("Download complete.")


download_pbp_csvs(BASE_URL, DIRECTORY)


