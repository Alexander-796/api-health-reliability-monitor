from flask import Flask, render_template, request, redirect
import sqlite3
import os
import requests
import time
from datetime import datetime

app = Flask(__name__)

# Database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "monitor.db")


# --------------------------------------------------
# Database Connection
# --------------------------------------------------

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# --------------------------------------------------
# Create / Update Database Tables
# --------------------------------------------------

def create_table():
    conn = get_db_connection()

    # Main API table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS apis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL
        )
    """)

    # Add new columns if they do not already exist
    columns = conn.execute(
        "PRAGMA table_info(apis)"
    ).fetchall()

    existing_columns = [
        column["name"] for column in columns
    ]

    new_columns = {
        "status": "TEXT",
        "response_time": "REAL",
        "status_code": "INTEGER",
        "last_checked": "TEXT"
    }

    for column, data_type in new_columns.items():

        if column not in existing_columns:
            conn.execute(
                f"ALTER TABLE apis ADD COLUMN {column} {data_type}"
            )

    # Monitoring history table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS monitoring_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            response_time REAL,
            status_code INTEGER,
            checked_at TEXT NOT NULL,
            FOREIGN KEY (api_id) REFERENCES apis(id)
        )
    """)

    conn.commit()
    conn.close()


# --------------------------------------------------
# Dashboard
# --------------------------------------------------

@app.route("/")
def home():

    conn = get_db_connection()

    apis = conn.execute(
        "SELECT * FROM apis ORDER BY id DESC"
    ).fetchall()

    total_apis = len(apis)

    healthy_apis = sum(
        1 for api in apis
        if api["status"] == "UP"
    )

    down_apis = sum(
        1 for api in apis
        if api["status"] == "DOWN"
    )

    unchecked_apis = sum(
        1 for api in apis
        if api["status"] is None
    )

    conn.close()

    return render_template(
        "index.html",
        apis=apis,
        total_apis=total_apis,
        healthy_apis=healthy_apis,
        down_apis=down_apis,
        unchecked_apis=unchecked_apis
    )


# --------------------------------------------------
# Register New API
# --------------------------------------------------

@app.route("/add", methods=["POST"])
def add_api():

    name = request.form.get("name", "").strip()
    url = request.form.get("url", "").strip()

    # Basic validation
    if not name or not url:
        return redirect("/?error=invalid")

    # Make sure the URL has HTTP/HTTPS
    if not (
        url.startswith("http://")
        or url.startswith("https://")
    ):
        return redirect("/?error=invalid_url")

    conn = get_db_connection()

    # Prevent duplicate URLs
    existing_api = conn.execute(
        "SELECT id FROM apis WHERE url = ?",
        (url,)
    ).fetchone()

    if existing_api:
        conn.close()
        return redirect("/?error=duplicate")

    conn.execute(
        """
        INSERT INTO apis (name, url)
        VALUES (?, ?)
        """,
        (name, url)
    )

    conn.commit()
    conn.close()

    return redirect("/")


# --------------------------------------------------
# Perform Health Check
# --------------------------------------------------

def perform_health_check(api_id):

    conn = get_db_connection()

    # Get API details
    api = conn.execute(
        "SELECT * FROM apis WHERE id = ?",
        (api_id,)
    ).fetchone()

    if api is None:
        conn.close()
        return False

    checked_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    try:

        # Start timer
        start_time = time.perf_counter()

        # Send HTTP request
        response = requests.get(
            api["url"],
            timeout=5
        )

        # Stop timer
        end_time = time.perf_counter()

        # Calculate response time in milliseconds
        response_time = (
            end_time - start_time
        ) * 1000

        # Determine health status
        if response.status_code < 400:
            status = "UP"
        else:
            status = "DOWN"

        # Update current API status
        conn.execute("""
            UPDATE apis
            SET status = ?,
                response_time = ?,
                status_code = ?,
                last_checked = ?
            WHERE id = ?
        """, (
            status,
            response_time,
            response.status_code,
            checked_at,
            api_id
        ))

        # Store monitoring result
        conn.execute("""
            INSERT INTO monitoring_history
            (
                api_id,
                status,
                response_time,
                status_code,
                checked_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            api_id,
            status,
            response_time,
            response.status_code,
            checked_at
        ))

    except requests.Timeout:

        # Request took longer than 5 seconds
        conn.execute("""
            UPDATE apis
            SET status = ?,
                response_time = ?,
                status_code = ?,
                last_checked = ?
            WHERE id = ?
        """, (
            "DOWN",
            None,
            None,
            checked_at,
            api_id
        ))

        conn.execute("""
            INSERT INTO monitoring_history
            (
                api_id,
                status,
                response_time,
                status_code,
                checked_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            api_id,
            "DOWN",
            None,
            None,
            checked_at
        ))

    except requests.RequestException:

        # Handles connection errors and other request failures
        conn.execute("""
            UPDATE apis
            SET status = ?,
                response_time = ?,
                status_code = ?,
                last_checked = ?
            WHERE id = ?
        """, (
            "DOWN",
            None,
            None,
            checked_at,
            api_id
        ))

        conn.execute("""
            INSERT INTO monitoring_history
            (
                api_id,
                status,
                response_time,
                status_code,
                checked_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            api_id,
            "DOWN",
            None,
            None,
            checked_at
        ))

    conn.commit()
    conn.close()

    return True


# --------------------------------------------------
# Check Single API
# --------------------------------------------------

@app.route("/check/<int:api_id>")
def check_api(api_id):

    perform_health_check(api_id)

    return redirect("/")


# --------------------------------------------------
# Check All APIs
# --------------------------------------------------

@app.route("/check-all")
def check_all():

    conn = get_db_connection()

    apis = conn.execute(
        "SELECT id FROM apis"
    ).fetchall()

    conn.close()

    for api in apis:
        perform_health_check(api["id"])

    return redirect("/")


# --------------------------------------------------
# Monitoring History
# --------------------------------------------------

@app.route("/history/<int:api_id>")
def history(api_id):

    conn = get_db_connection()

    # Get API information
    api = conn.execute(
        "SELECT * FROM apis WHERE id = ?",
        (api_id,)
    ).fetchone()

    if api is None:
        conn.close()
        return "API not found", 404

    # Get monitoring history
    history_records = conn.execute("""
        SELECT *
        FROM monitoring_history
        WHERE api_id = ?
        ORDER BY id DESC
    """, (api_id,)).fetchall()

    conn.close()

    return render_template(
        "history.html",
        api=api,
        history_records=history_records
    )


# --------------------------------------------------
# Reliability Analytics
# --------------------------------------------------

@app.route("/analytics/<int:api_id>")
def analytics(api_id):

    conn = get_db_connection()

    # Get API information
    api = conn.execute(
        "SELECT * FROM apis WHERE id = ?",
        (api_id,)
    ).fetchone()

    if api is None:
        conn.close()
        return "API not found", 404

    # Total number of checks
    total_checks = conn.execute("""
        SELECT COUNT(*)
        FROM monitoring_history
        WHERE api_id = ?
    """, (api_id,)).fetchone()[0]

    # Successful checks
    successful_checks = conn.execute("""
        SELECT COUNT(*)
        FROM monitoring_history
        WHERE api_id = ?
        AND status = 'UP'
    """, (api_id,)).fetchone()[0]

    # Failed checks
    failed_checks = conn.execute("""
        SELECT COUNT(*)
        FROM monitoring_history
        WHERE api_id = ?
        AND status = 'DOWN'
    """, (api_id,)).fetchone()[0]

    # Average response time
    average_response_time = conn.execute("""
        SELECT AVG(response_time)
        FROM monitoring_history
        WHERE api_id = ?
        AND response_time IS NOT NULL
    """, (api_id,)).fetchone()[0]

    # Availability percentage
    if total_checks > 0:

        availability = (
            successful_checks / total_checks
        ) * 100

    else:
        availability = 0

    conn.close()

    return render_template(
        "analytics.html",
        api=api,
        total_checks=total_checks,
        successful_checks=successful_checks,
        failed_checks=failed_checks,
        average_response_time=average_response_time,
        availability=availability
    )

@app.route("/delete/<int:api_id>", methods=["POST"])
def delete_api(api_id):
    conn = get_db_connection()

    # Delete monitoring history first
    conn.execute(
        "DELETE FROM monitoring_history WHERE api_id = ?",
        (api_id,)
    )

    # Delete the API
    conn.execute(
        "DELETE FROM apis WHERE id = ?",
        (api_id,)
    )

    conn.commit()
    conn.close()

    return redirect("/")
# --------------------------------------------------
# Start Application
# --------------------------------------------------
create_table()
if __name__ == "__main__":

    

    port = int(os.environ.get("PORT",5000))
    
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False)