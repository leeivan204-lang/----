# CLAUDE.md

## Commands
- **Run Server**: `start_server.bat` or `python main.py`
- **Run Server (Dev)**: `uvicorn main:app --reload`
- **Install Dependencies**: `pip install -r requirements.txt`
- **Test**: `pytest` (Note: No tests directory currently detected)

## Project Structure
- `main.py`: FastAPI backend application entry point.
- `index.html`: Single-page frontend application (Vanilla JS).
- `logs.db`: SQLite database file (Work logs storage).
- `uploads/`: Directory for storing uploaded user files.
- `start_server.bat`: Windows batch script to install dependencies and start the server.
- `requirements.txt`: Python package dependencies.
