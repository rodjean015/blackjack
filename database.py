import sqlite3
import pandas as pd
from datetime import datetime

# Ensure formatted_now is defined globally or within the function
formatted_now = datetime.now().strftime("%Y%m%d_%H%M%S")

def create_table():
    print("Creating table if it doesn't exist...")
    conn = sqlite3.connect('card_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS card_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region_name TEXT,
            label_value TEXT,
            sum_value INTEGER
        )
    ''')
    conn.commit()
    conn.close()
    print("Table creation checked.")

def save_card_data(region_name, label_value, sum_value):
    if label_value != "No card detected":
        conn = sqlite3.connect('card_data.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO card_data (region_name, label_value, sum_value)
            VALUES (?, ?, ?)
        ''', (region_name, label_value, sum_value))
        conn.commit()
        conn.close()

def load_card_data():
    conn = sqlite3.connect('card_data.db')
    cursor = conn.cursor()

    # Check if the table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='card_data';")
    table_exists = cursor.fetchone()
    if not table_exists:
        print("Table 'card_data' does not exist!")
        conn.close()
        return []

    cursor.execute('SELECT region_name, label_value, sum_value FROM card_data')
    data = cursor.fetchall()
    conn.close()
    return data

def populate_treeview(treeview):
    # Clear existing entries
    treeview.delete(*treeview.get_children())

    # Load data from the database
    card_data = load_card_data()

    # Disable redrawing of the treeview while inserting data
    treeview.configure(takefocus=0)

    # Batch insert data into the Treeview
    batch_size = 6  # Number of rows to insert at a time

    def insert_batch(start_index):
        # Insert a batch of data
        batch = card_data[start_index:start_index + batch_size]
        for row in batch:
            treeview.insert("", "0", values=row)  # Insert at the end for efficiency

        # Check if there are more data batches to insert
        if start_index + batch_size < len(card_data):
            treeview.after(1, insert_batch, start_index + batch_size)
        else:
            # Re-enable focus and UI updates once all data is inserted
            treeview.configure(takefocus=1)
            treeview.update_idletasks()  # Ensure the UI is refreshed

    # Start the first batch insert
    insert_batch(0)

def delete_all_data():
    """Delete all data from the card_data table."""
    conn = sqlite3.connect('card_data.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM card_data')
    conn.commit()
    conn.close()

def db_excel():
    """Export data from the card_data.db to an Excel file."""
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect('card_data.db')

        # Read data from the card_data table into a DataFrame
        card_data_df = pd.read_sql_query('SELECT * FROM card_data', conn)

        # Close the database connection
        conn.close()

        # Create an Excel writer object and write the DataFrame to a sheet
        file_path = f'database/card_data_{formatted_now}.xlsx'
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            card_data_df.to_excel(writer, sheet_name='Card Data', index=False)

        print(f"Database exported to Excel successfully: {file_path}")
    except Exception as e:
        print(f"An error occurred while exporting data to Excel: {e}")



