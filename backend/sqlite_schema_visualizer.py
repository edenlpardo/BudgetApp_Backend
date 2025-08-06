import argparse
import sqlite3
from graphviz import Digraph

def get_tables_and_fks(conn):
    cursor = conn.cursor()

    # Get table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cursor.fetchall()]

    columns = []
    foreign_keys = []

    for table in tables:
        # Get columns for each table
        cursor.execute(f"PRAGMA table_info({table});")
        for col in cursor.fetchall():
            columns.append((table, col[1], col[2]))  # (table, column_name, data_type)

        # Get foreign key constraints
        cursor.execute(f"PRAGMA foreign_key_list({table});")
        for fk in cursor.fetchall():
            foreign_keys.append((
                table,          # source_table
                fk[3],          # source_column
                fk[2],          # target_table
                fk[4]           # target_column
            ))

    return columns, foreign_keys

def visualize_schema(columns, foreign_keys, output):
    dot = Digraph(comment='SQLite Schema')
    tables = {}

    for table, column, dtype in columns:
        tables.setdefault(table, []).append(f"{column} : {dtype}")

    for table, cols in tables.items():
        label = f"<<TABLE BORDER='1' CELLBORDER='1' CELLSPACING='0'>"
        label += f"<TR><TD BGCOLOR='lightgray'><B>{table}</B></TD></TR>"
        for col in cols:
            label += f"<TR><TD ALIGN='LEFT'>{col}</TD></TR>"
        label += "</TABLE>>"
        dot.node(table, label=label, shape='plaintext')

    for src_table, src_col, tgt_table, tgt_col in foreign_keys:
        dot.edge(src_table, tgt_table, label=f"{src_col} ➝ {tgt_col}")

    dot.render(output, format='png', cleanup=True)
    print(f"Schema diagram saved as {output}.png")

def main():
    parser = argparse.ArgumentParser(description="Visualize SQLite schema as a graph")
    parser.add_argument('--dbpath', required=True, help='Path to your SQLite .db file')
    parser.add_argument('--output', default='sqlite_schema', help='Output filename (without extension)')

    args = parser.parse_args()

    conn = sqlite3.connect(args.dbpath)
    columns, foreign_keys = get_tables_and_fks(conn)
    visualize_schema(columns, foreign_keys, args.output)

if __name__ == "__main__":
    main()
