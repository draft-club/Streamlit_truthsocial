# Truth Social Streamlit Dashboard

A comprehensive dashboard for scrapping, analyzing, and exporting posts and comments from Truth Social. This application provides a user-friendly interface to interacting with the Truth Social data via the `truthbrush` library.

## Features

- **Real-time Scraping**: Fetch the latest posts and deep comment trees from any public Truth Social handle.
- **Interactive Dashboard**: View, filter, and search through scraped posts and comments.
- **Data Export**: Successfully scraped data is saved as structured JSON files for further analysis.
- **Antigravity Mode**: A fun visual twist for the UI.



## Installation

1.  **Clone the repository**:

    ```bash
    git clone <repository_url>
    cd TruthSocial/streamlitapp
    ```

2.  **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

    _Note: Ensure you have `truthbrush` installed._

3.  **Environment Setup**:
    You can set your Truth Social credentials as environment variables or enter them directly in the UI.
    ```bash
    # Optional .env file or export
    export TRUTHSOCIAL_USERNAME="your_username"
    export TRUTHSOCIAL_PASSWORD="your_password"
    ```

## Usage

1.  **Run the Streamlit App**:
    From the `streamlitapp` directory, run:

    ```bash
    streamlit run service/app.py
    ```

2.  **Configure Scraper**:
    - **Handle**: The username to scrape (e.g., `realDonaldTrump`).
    - **Days**: Number of past days to fetch.
    - **Max Comments**: Limit on comments to fetch.
    - **Credentials**: Enter your Truth Social username and password in the sidebar if not set in environment.

3.  **Run & View**:
    - Click **Scrape / Run Export**.
    - Wait for the process to complete (logs will appear in "Execution Logs").
    - Browse the Posts and Comments in the main view.
    - Download the raw JSON file if needed.

## Project Structure

- **`service/app.py`**: The main Streamlit application entry point.
- **`service/utils.py`**: Helper functions for running the scraping subprocess and processing data.
- **`export_with_comments.py`**: The underlying script that interfaces with `truthbrush` to perform the actual scraping.
- **`requirements.txt`**: Python dependencies.
