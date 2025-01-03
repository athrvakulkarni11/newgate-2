import sqlite3

def view_database():
    conn = sqlite3.connect('organizations.db')
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        print(f"\nTable: {table_name}")
        print("-" * 50)
        
        # Get table schema
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        print("Columns:", [col[1] for col in columns])
        
        # Get table contents
        cursor.execute(f"SELECT * FROM {table_name};")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
    
    conn.close()

# Call the function to view database contents
view_database()