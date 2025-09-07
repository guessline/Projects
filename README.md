Project setup and notebooks execution

Requirements
- Python 3.13 (already available in this workspace)
- Virtual environment will be created at `/workspace/.venv`

Setup
1) Create venv and install dependencies:
```
python3 -m pip install --user --break-system-packages virtualenv
~/.local/bin/virtualenv /workspace/.venv -p python3
. /workspace/.venv/bin/activate
pip install -r /workspace/requirements.txt
```

Data
Some notebooks expect datasets in `/datasets`:
- `/datasets/yandex_music_project.csv`
- `/datasets/real_estate_data.csv`
- `/datasets/calls.csv`, `/datasets/internet.csv`, `/datasets/messages.csv`, `/datasets/tariffs.csv`, `/datasets/users.csv`
- `/datasets/games.csv`

Place these files under `/datasets` (create the folder if missing) or adjust paths inside notebooks to point to your local copies.

Running notebooks non-interactively
```
. /workspace/.venv/bin/activate
jupyter nbconvert --to notebook --execute Project_1_Daily_Scooter_Rental_Analysis/Daily_Scooter_Rentals_Analysis.ipynb --output Project_1_Daily_Scooter_Rental_Analysis/Daily_Scooter_Rentals_Analysis_executed.ipynb
```

Notes
- `Project 1` runs as-is (uses a public CSV URL).
- Other projects will fail to execute until the required files are available at `/datasets` or paths are updated.

