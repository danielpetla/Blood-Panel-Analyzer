from pathlib import Path
import random
import markers
import schema


data_dir = Path(__file__).resolve().parent / "data" # path to the data folder

patient_file = [f for f in data_dir.glob("*.csv") if f.is_file()] # list of all csv files in the data folder