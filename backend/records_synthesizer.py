# Author: Yuan Tian
# Gtihub: https://github.com/magic-YuanTian/SQLsynth


import random
import uuid
from datetime import datetime, timedelta
from collections import defaultdict

# Helper functions
def generate_uuid():
    return str(uuid.uuid4())

def random_date(start, end):
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))

def random_int():
    return random.randint(1, 9999)

def random_string(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:6]}"

def random_boolean():
    return random.choice([True, False])

def random_timestamp():
    return random_date(datetime(2020, 1, 1), datetime.now()).isoformat()

def generate_value(field, foreign_key_values, existing_values, repetition_prob=0.3):
    field_type = field.get('type', 'text')
    if field.get('foreign_ref'):
        referenced_table, referenced_field = field['foreign_ref'].split('(')
        referenced_field = referenced_field.rstrip(')')

        # if foreign_key_values is empty, generate a random value
        if not foreign_key_values:
            return generate_value({'type': 'text', 'field': 'text'}, {}, [])
        else:
            return random.choice(foreign_key_values[(referenced_table, referenced_field)])
    
    # Check if we should use an existing value
    if not field.get('isPrimary') and existing_values and random.random() < repetition_prob:
        return random.choice(existing_values)
    
    if field_type == 'int':
        return random_int()
    elif field_type == 'text':
        return random_string(field.get('field', 'text'))
    elif field_type == 'boolean':
        return random_boolean()
    elif field_type == 'timestamp':
        return random_timestamp()
    else:
        return random_string('value')

def determine_table_order(schema):
    dependencies = defaultdict(set)
    for table, fields in schema.items():
        for field in fields:
            if field.get('foreign_ref'):
                referenced_table = field['foreign_ref'].split('(')[0]
                dependencies[table].add(referenced_table)
    
    ordered_tables = []
    visited = set()
    
    def dfs(table):
        if table in visited:
            return
        visited.add(table)
        for dep in dependencies[table]:
            dfs(dep)
        ordered_tables.append(table)
    
    for table in schema:
        dfs(table)
    
    return ordered_tables

def generate_data(schema, num_records=10):
    data = {}
    foreign_key_values = defaultdict(list)
    existing_values = defaultdict(list)
    table_order = determine_table_order(schema)

    for table_name in table_order:
        fields = schema[table_name]
        table_data = []
        for _ in range(num_records):
            record = {"id": generate_uuid()}  # Add a unique id to each record
            for field in fields:
                if field.get('isPrimary'):
                    value = generate_value(field, {}, [])
                    while value in foreign_key_values[(table_name, field['field'])]:
                        value = generate_value(field, {}, [])
                    record[field['field']] = value
                else:
                    record[field['field']] = generate_value(field, foreign_key_values, existing_values[field['field']])
                
                foreign_key_values[(table_name, field['field'])].append(record[field['field']])
                existing_values[field['field']].append(record[field['field']])
            
            table_data.append(record)
        data[table_name] = table_data

    
    return data

# Example schema (unchanged)
schema_example = {
    "hkg_dim_dataset": [
        {
            "field": "datasetId",
            "type": "text",
            "isPrimary": True
        },
        {
            "field": "name",
            "type": "text"
        }
    ],
    "hkg_dim_schema": [
        {
            "field": "schemaId",
            "type": "text",
            "isPrimary": True
        },
        {
            "field": "name",
            "type": "text"
        }
    ],
    "hkg_br_schema_dataset": [
        {
            "field": "datasetId",
            "type": "text",
            "foreign_ref": "hkg_dim_dataset(datasetId)"
        },
        {
            "field": "schemaId",
            "type": "text",
            "foreign_ref": "hkg_dim_schema(schemaId)"
        }
    ]
}

if __name__ == "__main__":
    # Generating data
    synthetic_data = generate_data(schema_example, num_records=5)

    # Printing the generated data
    for table in synthetic_data:
        print(f"Table: {table}")
        for record in synthetic_data[table]:
            print(record)
        print()