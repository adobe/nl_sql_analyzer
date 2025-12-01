# Author: Yuan Tian
# Gtihub: https://github.com/magic-YuanTian/SQLsynth


import random
import json
import numpy as np
import sqlparse
from collections import defaultdict
from sqlparse.sql import IdentifierList, Identifier, Where, Function
from sqlparse.tokens import Keyword, DML, Punctuation

from SQL2NL_clean import sql2nl
from collections import Counter

import sqlite3
import os
import uuid

import time

# Initial configuration object for probabilities
default_config = {
    'sample_table_probs': [0.5, 0.3, 0.2],
    'sample_column_probs': [0.4, 0.3, 0.2, 0.1],
    'select_star_prob': 0.2,
    'group_by_star_prob': 0.05,
    'group_by_probs': [0.5, 0.3, 0.2],
    'having_clause_prob': 0.3,
    'condition_not_prob': 0.3,
    'condition_subquery_prob': 0.1,
    'condition_and_prob': 0.1,
    'condition_or_prob': 0.1,
    'where_clause_prob': 0.3,
    'group_by_clause_prob': 0.2,
    'order_by_clause_prob': 0.3,
    'ieu_operator_prob': 0.1,
    'limit_clause_count': 0.1,
    'limit_num_probs': [0.5, 0.3, 0.2]
}

def learn_probabilities(sql_queries):
    
    config_records = {
        'sample_table_counts': [],  # convert to a distribution list
        'sample_column_counts': [],  # convert to a distribution list
        'group_by_counts': [],  # convert to a distribution list
        'limit_num_counts': [],  # convert to a distribution list
        'select_star_count': [],
        'group_by_clause_count': [],
        'group_by_star_count': [], 
        'having_clause_count': [],
        'where_clause_count': [],
        'order_by_clause_count': [],
        'limit_clause_count': [],
        'ieu_operator_count': [],
        'condition_subquery_count': [],
        'condition_not_count': [],
        'condition_and_count': [],
        'condition_or_count': [],
    }
    
    total_queries = len(sql_queries)

    for sql_query in sql_queries:
        print('SQL_query:', sql_query)
        
        try:
            explanation_data = sql2nl(sql_query)
        except Exception as e:
            print(f"Error: {e}")
            continue
        
        
        
        for query in explanation_data:
            table_count = 0
            column_count = 0
            group_by_count = 0
            select_star = 0
            group_by_clause = 0
            having_clause = 0
            where_clause = 0
            order_by_clause = 0
            limit_clause = 0
            ieu_operator = 0
            group_by_star = 0
            condition_subquery = 0  # nested query in condition
            condition_not = 0
            condition_and = 0
            condition_or = 0
            limit_num = 0
            
            for item in query['explanation']:
                subexpression = item['subexpression'].upper()
                
                if subexpression.startswith('FROM'):
                    table_count += 1
                    # count how many "JOIN" in the subexpression string
                    table_count += subexpression.count(' JOIN ')
                
                elif subexpression.startswith('SELECT'):
                    cols = subexpression.split('SELECT')[1].split('FROM')[0].strip()
                    
                    if cols == '*':
                        select_star = 1
                    else:
                        column_count = len(cols.split(','))
                
                elif subexpression.startswith('GROUP BY'):
                    group_by_clause = 1
                    
                    cols = subexpression.split('GROUP BY')[1].split('HAVING')[0].strip()
                    if cols == '*':
                        group_by_star = 1
                    else:
                        group_by_count = len(subexpression.split(','))
                    
                    
                
                elif subexpression.startswith('HAVING'):
                    having_clause = 1
                    
                    # get the condition in the HAVING clause
                    condition = subexpression.split('HAVING')[1].strip()
                    # count how many SELECT in the condition
                    condition_subquery += condition.count('SELECT')
                    # count how many 'NOT' in the condition
                    condition_not += condition.count(' NOT ')
                    # count how many 'AND' in the condition
                    condition_and += condition.count(' AND ')
                    # count how many 'OR' in the condition
                    condition_or += condition.count(' OR ')
                    
                    
                elif subexpression.startswith('WHERE'):
                    where_clause = 1

                    # get the condition in the WHERE clause
                    condition = subexpression.split('WHERE')[1].strip()
                    # count how many SELECT in the condition
                    condition_subquery += condition.count('SELECT')
                    # count how many 'NOT' in the condition
                    condition_not += condition.count(' NOT ')
                    # count how many 'AND' in the condition
                    condition_and += condition.count(' AND ')
                    # count how many 'OR' in the condition
                    condition_or += condition.count(' OR ')
                    
                elif subexpression.startswith('ORDER BY'):
                    order_by_clause = 1
                    
                
                    if 'LIMIT' in subexpression:
                        limit_clause = 1
                        
                        # get the number in the LIMIT clause
                        limit_num = subexpression.split('LIMIT')[1].strip()
                        # if the number is a number
                        if limit_num.isdigit():
                            limit_num = int(limit_num)
                        else:
                            limit_num = 0
                        
            # ieu operator, count how many "UNION", "INTERSECT", "EXCEPT" in the query
            ieu_operator = sql_query.count(' UNION ') + sql_query.count(' INTERSECT ') + sql_query.count(' EXCEPT ')
            
            # count how many 'SELECT' in the query
            select_star = sql_query.count('SELECT')
            
            # # count how many nested subquery in the condition (the difference between the number of 'SELECT' and 'IEU' in the condition)
            # if select_star > ieu_operator:
            #     condition_subquery = select_star - ieu_operator
            
            
            # update config_records
            config_records['sample_table_counts'].append(table_count)
            config_records['sample_column_counts'].append(column_count)
            config_records['group_by_counts'].append(group_by_count)
            config_records['select_star_count'].append(select_star)
            config_records['group_by_clause_count'].append(group_by_clause)
            config_records['having_clause_count'].append(having_clause)
            config_records['where_clause_count'].append(where_clause)
            config_records['order_by_clause_count'].append(order_by_clause)
            config_records['limit_clause_count'].append(limit_clause)
            config_records['ieu_operator_count'].append(ieu_operator)
            config_records['group_by_star_count'].append(group_by_star)
            config_records['condition_subquery_count'].append(condition_subquery)
            config_records['condition_not_count'].append(condition_not)
            config_records['condition_and_count'].append(condition_and)
            config_records['condition_or_count'].append(condition_or)
            config_records['limit_num_counts'].append(limit_num)
            
            

    # Calculate probabilities in config
    # Note that for key in ['sample_table_counts', 'sample_column_counts', 'group_by_counts'], return a distribution list, e.g., [0.5, 0.3, 0.2] representing the probability of sampling 1, 2, 3 tables/columns

    normalized_config = {
        'sample_table_probs': probability_distribution(config_records['sample_table_counts']),   # checked
        'sample_column_probs': probability_distribution(config_records['sample_column_counts']),  # checked
        'limit_num_probs': probability_distribution(config_records['limit_num_counts']),  # checked
        'group_by_probs': probability_distribution(config_records['group_by_counts']),  # checked
        'select_star_prob': config_records['select_star_count'].count(1) / total_queries,  # checked
        'group_by_clause_prob': config_records['group_by_clause_count'].count(1) / total_queries,  # checked
        'having_clause_prob': config_records['having_clause_count'].count(1) / total_queries,  # checked
        'where_clause_prob': config_records['where_clause_count'].count(1) / total_queries,  # checked
        'order_by_clause_prob': config_records['order_by_clause_count'].count(1) / total_queries,  # checked
        'limit_clause_count': config_records['limit_clause_count'].count(1) / total_queries,  # checked
        'ieu_operator_prob': config_records['ieu_operator_count'].count(1) / total_queries,  # checked
        'group_by_star_prob': config_records['group_by_star_count'].count(1) / total_queries,  # checked
        'condition_subquery_prob': config_records['condition_subquery_count'].count(1) / total_queries,  # checked
        'condition_not_prob': config_records['condition_not_count'].count(1) / total_queries,  # checked
        'condition_and_prob': config_records['condition_and_count'].count(1) / total_queries,  # checked
        'condition_or_prob': config_records['condition_or_count'].count(1) / total_queries,  # checked

    }
    

    return normalized_config




def probability_distribution(numbers):
    # Count the occurrences of each number
    count = Counter(numbers)
    # Calculate the total number of elements
    total = len(numbers)
    # Find the maximum number in the list
    max_num = max(numbers)
    # Create the probability distribution list
    distribution = [count[i] / total for i in range(1, max_num + 1)]
    
    return distribution

def find_connected_tables(schema, num_tables):
    """Find a set of connected tables with the required number of tables."""
    all_tables = list(schema.keys())
    
    # Shuffle the list of all tables to randomize the order of start tables
    random.shuffle(all_tables)
    
    for start_table in all_tables:
        connected_tables = set([start_table])
        to_visit = [start_table]
        
        while to_visit and len(connected_tables) < num_tables:
            current_table = to_visit.pop(0)
            if current_table in schema:
                for column in schema[current_table]:
                    if column['foreign_ref']:
                        referenced_table = column['foreign_ref'].split('(')[0]
                        if referenced_table not in connected_tables:
                            connected_tables.add(referenced_table)
                            to_visit.append(referenced_table)
                            if len(connected_tables) == num_tables:
                                return list(connected_tables)
        
        # If we've found at least the minimum number of tables, return them
        if len(connected_tables) >= num_tables:
            return list(connected_tables)[:num_tables]
    
    
    print('+'*50)
    print('connected_tables:', connected_tables)
    print('+'*50)
    
    # If we couldn't find enough connected tables, return as many as we could find
    return list(set().union(*[find_connected_tables(schema, 1) for _ in range(num_tables)]))


def sample_table(schema, config, min_tables=3):
    """Randomly sample connected tables from the schema, ensuring at least min_tables are selected."""
    tables = list(schema.keys())
    print('x'*50)
    print('tables:', tables)
    print('x'*50)
    
    num_tables = min(len(tables), len(config['sample_table_probs']))
    probs = config['sample_table_probs'][:num_tables]
    probs = [p/sum(probs) for p in probs]  # Normalize probabilities
    num_selected = max(min_tables, np.random.choice(range(1, num_tables + 1), p=probs))
    
    print('num_selected:', num_selected)
    
    # Find connected tables
    selected_tables = find_connected_tables(schema, num_selected)
    
    print('y'*50)
    print('selected_tables:', selected_tables)
    print('y'*50)
    
    # Ensure we have at least min_tables
    while len(selected_tables) < min_tables:
        remaining_tables = set(tables) - set(selected_tables)
        if not remaining_tables:
            break  # No more tables to add
        selected_tables.append(random.choice(list(remaining_tables)))
    
    print('num_tables:', len(selected_tables), end='\n\n')
    return selected_tables

def sample_column(schema, tables, config, min_tables=3):
    """Randomly sample columns from the sampled tables, ensuring columns come from at least min_tables."""
    columns = []
    column_types = []
    tables_used = set()

    # First, ensure we have at least one column from min_tables different tables
    for table in random.sample(tables, min(min_tables, len(tables))):
        num_columns = 1  # We'll select at least one column from each of these tables
        sampled_columns = random.sample(schema[table], num_columns)
        columns.extend([f"{table}.{col['field']}" for col in sampled_columns])
        column_types.extend([col['type'] for col in sampled_columns])
        tables_used.add(table)

    # Then, sample additional columns as before
    for table in tables:
        if table not in tables_used:
            num_columns = min(len(schema[table]), len(config['sample_column_probs']))
            probs = config['sample_column_probs'][:num_columns]
            probs = [p/sum(probs) for p in probs]  # Normalize probabilities
            num_selected = np.random.choice(range(0, num_columns + 1), p=[0] + probs)  # Allow selecting 0 columns
            
            if num_selected > 0:
                sampled_columns = random.sample(schema[table], num_selected)
                columns.extend([f"{table}.{col['field']}" for col in sampled_columns])
                column_types.extend([col['type'] for col in sampled_columns])
                tables_used.add(table)

    print(f'Columns sampled from {len(tables_used)} tables')
    return columns, column_types


def synthesize_select_clause(columns, config):
    """Generate SELECT clause from sampled columns."""
    if random.random() < config['select_star_prob']:
        return "SELECT *"
    return "SELECT " + ", ".join(columns)


def synthesize_from_clause(tables, schema, min_joins):
    base_table = tables[0]
    from_clause = f"FROM {base_table}"
    joined_tables = {base_table}
    joins = []

    # First, try to create joins based on foreign keys
    for table in tables[1:]:
        for column in schema[base_table]:
            if column['foreign_ref'] and column['foreign_ref'].startswith(table):
                foreign_ref_col = column['foreign_ref'].split('(')[0] + '.' + column['foreign_ref'].split('(')[1].split(')')[0]
                joins.append(f"JOIN {table} ON {base_table}.{column['field']} = {foreign_ref_col}")
                joined_tables.add(table)
                break

    # If we don't have enough joins, add random joins
    remaining_tables = set(tables) - joined_tables
    while len(joins) < min_joins and remaining_tables:
        table = random.choice(list(remaining_tables))
        join_table = random.choice(list(joined_tables))
        joins.append(f"JOIN {table} ON {join_table}.id = {table}.id") # TODO: improve this, build type -> column dict
        joined_tables.add(table)
        remaining_tables.remove(table)

    from_clause += " " + " ".join(joins)
    return from_clause, list(joined_tables)


def synthesize_where_clause(columns, column_types, records, schema, config):
    """Generate a WHERE clause using a sampled column for a condition."""
    condition = synthesize_condition(columns, column_types, records, schema, config)
    return f"WHERE {condition}" if condition else ""
    
def synthesize_order_by_clause(columns, column_types, config):
    """Generate an ORDER BY clause using a sampled column."""
    column = random.choice(columns)
    order = random.choice(["ASC", "DESC"])
    
    # add limit clause
    if random.random() < config['limit_clause_count']:
        # make sure the sum of the probabilities is 1
        temp_normalized_p = [p/sum(config['limit_num_probs']) for p in config['limit_num_probs']]
        limit = np.random.choice(range(1, 11), p=temp_normalized_p)
        return f"ORDER BY {column} {order} LIMIT {limit}"
    else:
        return f"ORDER BY {column} {order}"

def synthesize_group_by_clause(columns, column_types, records, schema, config):
    """Generate a GROUP BY clause using sampled columns."""
    if random.random() < config['group_by_star_prob']:
        return "GROUP BY *"
    
    num_columns = min(len(columns), len(config['group_by_probs']))
    probs = config['group_by_probs'][:num_columns]
    probs = [p/sum(probs) for p in probs]  # Normalize probabilities
    num_selected = np.random.choice(range(1, num_columns + 1), p=probs)
    group_columns = random.sample(columns, num_selected)
    
    group_by = f"GROUP BY {', '.join(group_columns)}"
    if random.random() < config['having_clause_prob']:
        having_condition = synthesize_condition(columns, column_types, records, schema, config)
        group_by += f" HAVING {having_condition}"
    return group_by

def synthesize_condition(columns, column_types, records, schema, config):
    """Create a conditional filter for WHERE and HAVING clauses."""
    column, column_type = random.choice(list(zip(columns, column_types)))
    
    text_operator = random.choice(["=", "!=", "LIKE", "NOT LIKE"])
    value_operator = random.choice(["=", "!=", ">", "<", ">=", "<="])
    boolean_operator = random.choice(["=", "!="])
    
    table, column = column.split(".")
    value = sample_value_from_column(records, table, column)
    
    if column_type == "text":
        operator = text_operator
        value = f"'{value}'" # TODO: add %
    elif column_type in ["int", "timestamp", "float", "double", "decimal"]:
        operator = value_operator
    elif column_type.lower() == "boolean":
        operator = boolean_operator
        value = random.choice(['False', 'True'])  #TODO: adapt to different dialects
    else:
        # for immutableTags (not sure where it comes from)
        operator = text_operator
        value = f"'{value}'"
    
    condition = f"{column} {operator} {value}"
    
    if random.random() < config['condition_not_prob']:
        condition = f"NOT ({condition})"
    
    if random.random() < config['condition_subquery_prob']:
        temp_select_clause, temp_from_clause, temp_where_clause, temp_group_by_clause, temp_columns, temp_column_types = synthesize_subquery(schema, records, config, min_joins=0)
        new_subquery = f"{temp_select_clause} {temp_from_clause} {temp_where_clause} {temp_group_by_clause}"
        new_subquery = new_subquery.strip()
        # replace 2 consecutive spaces with 1 space
        new_subquery = " ".join(new_subquery.split())
        condition = f"{column} {operator} ({new_subquery})"
    
    if random.random() < config['condition_and_prob']:
        another_condition = synthesize_condition(columns, column_types, records, schema, config)
        condition = f"{condition} AND {another_condition}"
    elif random.random() < config['condition_or_prob']:
        another_condition = synthesize_condition(columns, column_types, records, schema, config)
        condition = f"{condition} OR {another_condition}"
    
    return condition

def sample_value_from_column(records, table, column):
    """Sample a value from a specified column in a table within the provided records."""
    if table not in records:
        raise ValueError(f"Table '{table}' not found in the records.")
    if not records[table]:
        raise ValueError(f"No data available in table '{table}'.")
    record = random.choice(records[table])
    if column not in record:
        raise ValueError(f"Column '{column}' not found in table '{table}'.")
    return record[column]


def synthesize_subquery(schema, records, config, min_joins):
    all_tables = sample_table(schema, config, min_tables=min_joins+1)
    from_clause, used_tables = synthesize_from_clause(all_tables, schema, min_joins)
    columns, column_types = sample_column(schema, used_tables, config)
    
    select_clause = synthesize_select_clause(columns, config)
    
    where_clause = ""
    if random.random() < config['where_clause_prob']:
        where_clause = synthesize_where_clause(columns, column_types, records, schema, config)
    
    group_by_clause = ""
    if random.random() < config['group_by_clause_prob']:
        group_by_clause = synthesize_group_by_clause(columns, column_types, records, schema, config)
    
    return select_clause, from_clause, where_clause, group_by_clause, columns, column_types


# a helper function to execute a SQL query on the database
def execute_query(query, db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()


# helper function to create a sqlite database from the frontend records
def create_database(data):

    # generate a random database path based on uuid
    random_id = uuid.uuid4().hex[:6]
    db_path = f"temp_db/records_{random_id}.db"

    with sqlite3.connect(db_path, timeout=20) as conn:
        cursor = conn.cursor()

        for table_name, records in data.items():
            if records:
                # Print table name and columns
                columns = list(records[0].keys())
                # print(f"Table: {table_name}")
                # print(f"Columns: {columns}")

                # Create table
                create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join([f'{col} TEXT' for col in columns])})"
                print(f"Create table SQL: {create_table_sql}")
                cursor.execute(create_table_sql)

                # Insert data
                placeholders = ", ".join(["?" for _ in columns])
                insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

                print(f"Insert SQL: {insert_sql}")
                for record in records:
                    # print(f"Record: {[str(record[col]) for col in columns]}")
                    cursor.execute(insert_sql, [str(record[col]) for col in columns])

        conn.commit()

    # get absolute path
    db_path = os.path.abspath(db_path)

    # wait until the database file is created
    while not os.path.exists(db_path):
        pass
    
    return db_path


# Randomly sample a synthetic SQL query using the provided schema and records
# Making sure the query can return results based on the records in the database
def get_synthetic_SQL(schema, records, config, min_jonins):
    
    # create a temporary SQLite database based on the records
    db_path = create_database(records)
    
    
    max_attempts = 50
    attempt_count = 0
    
    # keep trying until we get a valid SQL query that can be executed and return non-empty results
    # when the db exists, we can execute the SQL query
    while os.path.exists(db_path) and attempt_count < max_attempts:
        try:
            attempt_sql = attempt_get_synthetic_SQL(schema, records, config, min_jonins)

            print('attempt_sql:', attempt_sql)
            
            # execute the SQL query on a temporary SQLite database based on the records
            result = execute_query(attempt_sql, db_path)
            print('result:', flush=True)
            print('-'*50)
            print(result)
            print('-'*50)
            
            if result:
                break
        
        except Exception as e:
            print(f"Error executing query: {e}")
            print(db_path)
            continue
        
        attempt_count += 1


    
    # delete the temporary SQLite database
    try:
        os.remove(db_path)
    except Exception as e:
        print(f"Error deleting database file: {e}")

    
    return attempt_sql



# without results checking
def attempt_get_synthetic_SQL(schema, records, config, min_joins=0):
    IEU_operator = ''
    if random.random() < config['ieu_operator_prob']:
        IEU_operator = random.choice(["UNION", "INTERSECT", "EXCEPT"])
    
    if IEU_operator:
        sql1 = attemp_get_synthetic_SQL(schema, records, config, min_joins)
        sql2 = attemp_get_synthetic_SQL(schema, records, config, min_joins)
        SQL = f"{sql1} {IEU_operator} {sql2}"
    else:
        select_clause, from_clause, where_clause, group_by_clause, columns, column_types = synthesize_subquery(schema, records, config, min_joins)
        SQL = f"{select_clause} {from_clause} {where_clause} {group_by_clause}"

    # Add ORDER BY clause at the end
    if random.random() < config['order_by_clause_prob']:
        order_by_clause = synthesize_order_by_clause(columns, column_types, config)
        SQL += f" {order_by_clause}"
    
    SQL = " ".join(SQL.split())
    SQL = SQL.strip()

    return SQL

# the function to load real dataset, and automatically learn probability from the dataset (convert to a list of SQL queries)
def learn_from_real_dataset(path = "/Users/yuantian/Desktop/Projects/nl_sql_analyzer/backend/real_data/train_spider.json"):
    with open(path, 'r') as file:
        data = json.load(file)
    
    sql_queries = []
    for item in data:
        sql_query = item['query']
        sql_queries.append(sql_query)
    
    learned_config = learn_probabilities(sql_queries)
    
    return learned_config

# if __name__ == "__main__":
    # Load schema and records
    with open('/Users/yuantian/Desktop/Projects/nl_sql_analyzer/backend/schema_description/schema_description.json', 'r') as file:
        schema = json.load(file)
    
    with open('/Users/yuantian/Desktop/Projects/nl_sql_analyzer/backend/synthetic_records_test.json', 'r') as file:
        records = json.load(file)
    
    # # Example list of SQL queries to learn from
    # example_queries = [
    #     # "SELECT * FROM users WHERE age > 30",
    #     "SELECT product_name FROM products JOIN apple ON products.id = APPLE.id GROUP BY product_name HAVING COUNT(*) > 10",
    #     "SELECT id, name FROM users WHERE age > 25 ORDER BY name DESC"
    # ]
    
    # # Learn probabilities from example queries
    # learned_config = learn_probabilities(example_queries)
    
    learned_config = learn_from_real_dataset("/Users/yuantian/Desktop/Projects/nl_sql_analyzer/backend/real_data/train_spider.json")
    
    
    # save the learned config to a flie
    with open('/Users/yuantian/Desktop/Projects/nl_sql_analyzer/backend/learned_config.json', 'w') as file:
        json.dump(learned_config, file)
    
    # Generate a synthetic SQL query using the learned configuration
    synthetic_SQL = get_synthetic_SQL(schema, records, learned_config)
    
    print('='*50)
    print("Learned Configuration:")
    print(json.dumps(learned_config, indent=2))
    

    
    print('-'*50)
    print("Generated SQL:")
    print(synthetic_SQL)
    print('-'*50)