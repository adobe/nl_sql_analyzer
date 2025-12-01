# Author: Yuan Tian
# Gtihub: https://github.com/magic-YuanTian/SQLsynth

import re
import json


def transform_backend_schema_to_frontend_schema(schema):
    result = {}
    
    # Iterate through each table in the schema
    for table_name, table_info in schema.items():
        field_list = []
        # Parse the DDL string to extract column details
        ddl = table_info['ddl']
        # Strip the prefix and suffix of the DDL to focus on columns and foreign keys
        ddl_content = ddl[ddl.find("(") + 1:ddl.rfind(")")]
        # Split into individual statements (columns and foreign keys)
        statements = [stmt.strip() for stmt in ddl_content.split(",")]

        # Initialize containers for primary keys and foreign keys
        primary_key = None
        foreign_keys = {}
        
        # First pass: Identify primary keys and foreign key constraints
        for statement in statements:
            if 'primary key' in statement.lower() and 'foreign key' not in statement.lower():
                primary_key = statement.split()[0]
            if 'foreign key' in statement.lower():
                # Extracting foreign key details accurately
                fk_part = statement.split("foreign key(")[1].split(") references ")
                fk_field = fk_part[0].strip()
                ref_table_field = fk_part[1].strip()
                foreign_keys[fk_field] = ref_table_field

        # Second pass: Assign columns to field_list with proper foreign key references
        for column in statements:
            if 'foreign key' in column.lower() or column.startswith("foreign key"):
                continue  # Skip processing foreign keys directly here
            parts = column.split()
            column_name = parts[0]
            column_type = parts[1] if len(parts) > 1 else 'text'  # Default to text if unspecified

            # Check if the column is a primary key
            is_primary = (column_name == primary_key)
            
            # Construct the dictionary for each column
            column_dict = {
                'field': column_name,
                'headerName': column_name,
                'isPrimary': is_primary,
                'foreign_ref': foreign_keys.get(column_name),  # Assigning foreign key reference
                'table_description': table_info['description'],
                'column_description': '',  # Placeholder for actual column descriptions if available
                'width': 300 if not is_primary else 400,
                'type': column_type.split()[0] if len(column_type.split()) > 0 else 'text'
            }

            field_list.append(column_dict)
        
        result[table_name] = field_list

    return result


# (obsolete)
# convert detailed schema information to only tables
'''
e.g., 

{
        users: [
            { field: 'id', headerName: 'ID', width: 90 },
            { field: 'firstName', headerName: 'First Name', width: 150 },
            { field: 'lastName', headerName: 'Last Name', width: 150 },
            { field: 'age', headerName: 'Age', type: 'number', width: 110 }
        ],
        orders: [
            { field: 'orderId', headerName: 'Order ID', width: 120 },
            { field: 'userId', headerName: 'User ID', width: 100 },
            { field: 'product', headerName: 'Product', width: 150 },
            { field: 'quantity', headerName: 'Quantity', type: 'number', width: 110 }
        ]
    }
'''
def get_pure_datagrid_data(schema):
    
    # for each elements in the schema, only keeps, field, headerName, width
    result = {}
    for table_name, table_info in schema.items():
        field_list = []
        for column in table_info:
            column_dict = {
                'field': column['field'],
                'headerName': column['headerName'],
                'width': column['width']
            }
            field_list.append(column_dict)
        result[table_name] = field_list
    
    return result


# read from local kg_db.json file, store it as a dict
def get_schema(file_path="kg_db.json"):
    with open(file_path, "r") as file:
        database_schema = json.load(file)
    
    return database_schema
