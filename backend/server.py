# Author: Yuan Tian
# Gtihub: https://github.com/magic-YuanTian/SQLsynth


from flask import Flask, request, jsonify
from flask_cors import CORS
from SQL2NL_clean import sql2nl
from llm_analysis import *
from db_handling import *
from records_synthesizer import *
from SQL_synthesizer import *
import SQL_synthesizer
from openai_api import get_openai_response
import re
import os
from ICL_retriever import *
import sqlite3
import json
import uuid
from werkzeug.utils import secure_filename
from sqlparse import parse, tokens as T
from collections import defaultdict
import nltk
from nltk import pos_tag, word_tokenize
from nltk.chunk import RegexpParser
import spacy


app = Flask(__name__)
CORS(app)  # This enables CORS for all domains on all routes.


UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'json'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------------------------- Dataset analysis ------------------------------

# Example input
'''
queries = [
    {
        "sqlQuery": "SELECT * FROM Apartment_Buildings WHERE building_manager NOT LIKE 'building_manager_02312f' AND building_manager LIKE 'building_manager_0edb5b' GROUP BY Apartment_Buildings.building_manager",
    },
    {
        "sqlQuery": "SELECT * FROM Guests GROUP BY Guests.guest_id ORDER BY Guests.guest_id ASC",
    },
    # ... (other queries)
]
'''

def count_sql_entities(queries):
    column_count = defaultdict(int)
    table_count = defaultdict(int)
    
    for query in queries:
        sql = query['sqlQuery']
        
        # Count columns
        columns = re.findall(r'(\w+\.\w+|\*)', sql)
        for col in columns:
            if col != '*':
                column_count[col] += 1
            else:
                table_aliases = re.findall(r'FROM\s+(\w+)|JOIN\s+(\w+)', sql)
                for alias in table_aliases:
                    alias = next(a for a in alias if a)  # Get the non-empty string
                    column_count[f"{alias}.*"] += 1
        
        # Count tables
        tables = re.findall(r'FROM\s+(\w+)|JOIN\s+(\w+)', sql)
        for table in tables:
            table = next(t for t in table if t)  # Get the non-empty string
            table_count[table] += 1
    
    return dict(column_count), dict(table_count)

def count_table_references(sql, schema):
    parsed = parse(sql)[0]
    table_references = {}
    for token in parsed.flatten():
        if token.ttype is T.Name and token.value in schema.keys():
            table_references[token.value] = table_references.get(token.value, 0) + 1
    return table_references

def count_column_references(sql, schema):
    parsed = parse(sql)[0]
    column_references = {}
    for token in parsed.flatten():
        if token.ttype is T.Name:
            for table in schema.keys():
                if token.value in [col['field'] for col in schema[table]]:
                    column_references[token.value] = column_references.get(token.value, 0) + 1
                    break
    return column_references

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def analyze_sql_structure(sql):
    parsed = parse(sql)[0]
    structure = []
    for token in parsed.flatten():
        if token.ttype in (T.Keyword, T.Keyword.DML, T.Keyword.DDL):
            structure.append(token.value.upper())
    return ' '.join(structure)

def count_clauses(sql):
    parsed = parse(sql)[0]
    clause_count = 0
    for token in parsed.flatten():
        if token.ttype is T.Keyword and token.value.upper() in ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY']:
            clause_count += 1
    return clause_count

def count_reference_values(sql):
    parsed = parse(sql)[0]
    reference_count = 0
    for token in parsed.flatten():
        if token.ttype in [T.Literal.String.Single, T.Literal.Number.Integer, T.Literal.Number.Float]:
            reference_count += 1
    return reference_count

# count the number of columns used in the query
def count_used_columns(sql):
    parsed = parse(sql)[0]
    column_count = 0
    for token in parsed.flatten():
        if token.ttype is T.Name:
            column_count += 1
    return column_count
    
# count the number of tables used in the query
def count_used_tables(sql):
    parsed = parse(sql)[0]
    table_count = 0
    for token in parsed.flatten():
        if token.ttype is T.Name:
            table_count += 1
    return table_count
    

def calculate_query_complexity(sql):
    clause_count = count_clauses(sql)
    reference_count = count_reference_values(sql)
    column_count = count_used_columns(sql)
    table_count = count_used_tables(sql)
    return clause_count + reference_count + column_count + table_count

def get_examples(data, key, n=3):
    sorted_data = sorted(data, key=lambda x: x[key])
    examples = sorted_data[:min(n, len(data))]
    return [f"{example[key]}: {example.get('count', example.get('value', 'N/A'))} queries" for example in examples]


@app.route('/analyze_dataset', methods=['POST'])
def analyze_dataset():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    schema = json.loads(request.form.get('schema', '{}'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        with open(filepath, 'r') as f:
            data = json.load(f)

        keywords = []
        structures = []
        clause_numbers = []
        reference_values = []
        used_columns = []
        used_tables = []
        query_complexities = []
        concrete_column_distribution, concrete_table_distribution = count_sql_entities(data)

        total_queries = len(data)  # Calculate total number of queries
        total_complexity = 0  # Initialize total complexity
        
        for item in data:
            sql = item['sqlQuery']
            parsed = parse(sql)[0]
            for token in parsed.flatten():
                if token.ttype in (T.Keyword, T.Keyword.DML, T.Keyword.DDL):
                    keywords.append(token.value.upper())
            structures.append(analyze_sql_structure(sql))
            clause_numbers.append(count_clauses(sql))
            reference_values.append(count_reference_values(sql))
            used_columns.append(count_used_columns(sql))
            used_tables.append(count_used_tables(sql))
            complexity = calculate_query_complexity(sql)
            query_complexities.append(complexity)
            total_complexity += complexity  # Add to total complexity

        average_complexity = total_complexity / total_queries if total_queries > 0 else 0
        
        print('-' * 50, flush=True)
        print(used_columns)
        print('-' * 50, flush=True)
        print(used_tables)
        
        keyword_distribution = [{'name': k, 'count': v} for k, v in Counter(keywords).items()]
        structure_distribution = [{'name': s, 'value': structures.count(s)} for s in set(structures)]
        clause_number_distribution = [{'name': str(k), 'count': v} for k, v in Counter(clause_numbers).items()]
        reference_value_distribution = [{'name': str(k), 'count': v} for k, v in Counter(reference_values).items()]
        used_columns_distribution = [{'name': str(k), 'count': v} for k, v in Counter(used_columns).items()]
        used_tables_distribution = [{'name': str(k), 'count': v} for k, v in Counter(used_tables).items()]
        query_complexity_distribution = [{'name': str(k), 'count': v} for k, v in Counter(query_complexities).items()]
        
        # print everything
        print('Total queries:', total_queries, flush=True)
        print('Average complexity:', average_complexity, flush=True)
        print('Keyword distribution:', keyword_distribution, flush=True)
        print('Structure distribution:', structure_distribution, flush=True)
        print('Clause number distribution:', clause_number_distribution, flush=True)
        print('Reference value distribution:', reference_value_distribution, flush=True)
        print('Used columns distribution:', used_columns_distribution, flush=True)
        print('Used tables distribution:', used_tables_distribution, flush=True)
        print('Query complexity distribution:', query_complexity_distribution, flush=True)
        print('Concrete column distribution:', concrete_column_distribution, flush=True)
        print('Concrete table distribution:', concrete_table_distribution, flush=True)
        
        
        os.remove(filepath)  # Remove the file after analysis

        return jsonify({
        'totalQueries': total_queries,
        'averageComplexity': average_complexity,
        'keywordDistribution': {
            'data': sorted(keyword_distribution, key=lambda x: x['name']),
            'examples': get_examples(keyword_distribution, 'name'),
            'explanation': "This distribution shows the frequency of SQL keywords used in the queries. It helps identify which SQL operations are most common in the dataset."
        },
        'structureDistribution': {
            'data': sorted(structure_distribution, key=lambda x: x['name']),
            'examples': get_examples(structure_distribution, 'name'),
            'explanation': "This chart represents the proportion of different SQL query structures. It provides insights into the complexity and variety of query patterns in the dataset."
        },
        'clauseNumberDistribution': {
            'data': sorted(clause_number_distribution, key=lambda x: int(x['name'])),
            'examples': get_examples(clause_number_distribution, 'name'),
            'explanation': "This distribution shows the number of clauses used in queries. More clauses often indicate more complex queries."
        },
        'referenceValueDistribution': {
            'data': sorted(reference_value_distribution, key=lambda x: int(x['name'])),
            'examples': get_examples(reference_value_distribution, 'name'),
            'explanation': "This illustrates the frequency of reference values (literals) in queries. It can indicate how often queries are parameterized or use specific values."
        },
        'usedColumnsDistribution': {
            'data': sorted(used_columns_distribution, key=lambda x: int(x['name'])),
            'examples': get_examples(used_columns_distribution, 'name'),
            'explanation': "This shows the distribution of the number of columns used in queries. It can help understand the breadth of data typically queried."
        },
        'usedTablesDistribution': {
            'data': sorted(used_tables_distribution, key=lambda x: int(x['name'])),
            'examples': get_examples(used_tables_distribution, 'name'),
            'explanation': "This illustrates the number of tables used in queries. More tables often indicate more complex joins or subqueries."
        },
        'queryComplexityDistribution': {
            'data': sorted(query_complexity_distribution, key=lambda x: int(x['name'])),
            'examples': get_examples(query_complexity_distribution, 'name'),
            'explanation': "This represents the distribution of query complexity based on various factors including the number of clauses, reference values, columns, and tables used. Higher values indicate more complex queries."
        },
        'concreteColumnDistribution': {
            'data': sorted([{'name': k, 'count': v} for k, v in concrete_column_distribution.items()], key=lambda x: x['name']),
            'examples': get_examples([{'name': k, 'count': v} for k, v in concrete_column_distribution.items()], 'name'),
            'explanation': "This distribution shows the frequency of specific columns used in the queries. It helps identify which columns are most commonly queried across the dataset."
        },
        'concreteTableDistribution': {
            'data': sorted([{'name': k, 'count': v} for k, v in concrete_table_distribution.items()], key=lambda x: x['name']),
            'examples': get_examples([{'name': k, 'count': v} for k, v in concrete_table_distribution.items()], 'name'),
            'explanation': "This distribution shows the frequency of specific tables used in the queries. It helps identify which tables are most commonly queried across the dataset."
        }
    })
        
    return jsonify({'error': 'File type not allowed'}), 400




# ----------------------------------------------------------

# Helper function: make sure the entity names in entity has no space. All sapce will be replaced by underscore
def replace_space_with_underscore(schema):
    new_entity = {}
    for key in schema.keys():
        new_key = key.replace(" ", "_")
        columns = schema[key]
        
        new_columns = []
        for column in columns:
            temp_new_column = copy.deepcopy(column)
            if temp_new_column["foreign_ref"]:
                temp_new_column["foreign_ref"] = temp_new_column["foreign_ref"].replace(" ", "_")
            if temp_new_column["field"]:
                temp_new_column["field"] = temp_new_column["field"].replace(" ", "_")
            new_columns.append(temp_new_column)
        
        new_entity[new_key] = new_columns

    return new_entity

# Helper function: remove aligned field in the parsed step-by-step data
def remove_aligned(parsed_step_by_step_data):

    new_data = copy.deepcopy(parsed_step_by_step_data)

    for subquery in new_data:
        for step in subquery["explanation"]:
            step.pop("aligned", None)

    return new_data


# Helper function: copy nl quesiton to the aligned field in the parsed step-by-step data. This indicates no alignment (used in case the alignement checking is not conducted)
def dummy_aligned(parsed_step_by_step_data, nl_query):

    new_data = copy.deepcopy(parsed_step_by_step_data)

    for subquery in new_data:
        for step in subquery["explanation"]:
            step["aligned"] = nl_query

    return new_data


# Helper function: Given a SQL query, translate it to natural language question based on in-context learning
def get_nl_ICL(schema, sql_query, step_by_step, example_file_path, example_num=5):

    data_pool = load_data(example_file_path)
    print("Retrieving examples...", flush=True)
    
    retrieved_examples_top_k = get_top_k_similar(
        k=example_num, data=data_pool, input_sql=sql_query
    )

    # form retieved examples, only keep the examples with similarity higher than threshold
    threshold = 0.85
    print("Filtering examples...", flush=True)
    similar_examples = [example for example in retrieved_examples_top_k if example["similarity"] > threshold]
    print("Filtered examples:", similar_examples, flush=True)
    
    print("Synthesizing natural language query...", flush=True)
    nl_query = llm_summarize_nl_query(
        step_by_step_description=str(step_by_step),
        sql=sql_query,
        examples=similar_examples,
        schema=schema,
    )

    return nl_query, retrieved_examples_top_k


# Helper function: Given a SQL query, translate it to natural language question based on simple context
def get_simple_nl_and_examples(
    schema, sql_query, step_by_step, example_file_path, example_num=5
):

    data_pool = load_data(example_file_path)
    print("Retrieving examples...", flush=True)
    retrieved_examples = get_top_k_similar(
        k=example_num, data=data_pool, input_sql=sql_query
    )

    print("Synthesizing natural language query...", flush=True)
    nl_query = llm_summarize_nl_query(
        step_by_step_description="", sql=sql_query, examples="", schema=schema
    )

    return nl_query, retrieved_examples

# split a NL question into chunks
def chunk_sentence(sentence):
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(sentence)
    
    chunks = []
    current_chunk = []
    
    for token in doc:
        current_chunk.append(token.text)
        
        # End a chunk at these dependency labels
        if token.dep_ in ['ROOT', 'conj', 'prep', 'advcl'] and len(current_chunk) > 1:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
        
        # Also end a chunk at punctuation
        elif token.text in [',', '.', ';', ':', '?', '!'] and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
    
    # Add any remaining tokens as a final chunk
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    # Clean up: remove any empty chunks and strip whitespace
    chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
    
    print('** ' * 10)
    print('chunks:', chunks)
    
    return chunks

# a warpper function to get the alignment between sub-questions and the natural language question
def get_alignment(nl_query_chunks, nl_query, sql_query, step, finished_task, schema):
        
    
    # get the fisrt round prompt for alignment analysis
    prompt1 = get_map_subquestion_to_substring_prompt_1(
        nl_query_chunks, nl_query, sql_query, step, "", schema,
    )
    
    first_round_response_analysis = get_openai_response(prompt1)
    
    print('0' * 50, flush=True)
    print('first round response:', first_round_response_analysis, flush=True)
    
    promt2 = get_map_subquestion_to_substring_prompt_2(
        nl_query_chunks, first_round_response_analysis, nl_query, sql_query, step, "", schema
    )
    
    second_round_response_formatted = get_openai_response(promt2)
    
    aligned_question = extract_aligned_question(second_round_response_formatted)
    
    return aligned_question



# extract values/columns/tables from an explanation step
def extract_properties_from_step(step):
    print('~' * 50)
    print('step:', step)
    
    # extract values from <value>...</value>
    values = re.findall(r"<value>(.*?)</value>", step)
    # extract columns from <column>...</column>
    columns = re.findall(r"<column>(.*?)</column>", step)
    # extract tables from <table>...</table>
    tables = re.findall(r"<table>(.*?)</table>", step)
    
    print('values:', values)
    print('columns:', columns)
    print('tables:', tables)
    
    return values, columns, tables

# get alignments between sub-questions and the natural language question
def get_alignment_data(parsed_step_by_step_data, nl_query, sql_query, schema):

    finished_alignment_tasks = []

    threshold = 60

    new_data = copy.deepcopy(parsed_step_by_step_data)
    # remove the aligned field in the parsed step-by-step data
    new_data = remove_aligned(new_data)

    # get chunks of the nl_query
    nl_query_chunks = chunk_sentence(nl_query)
    
    low_threshold = 0.3
    high_threshold = 0.8
    
    for subquery in new_data:
        for step in subquery["explanation"]:
            # print('step:', step, flush=True)
            sub_question = step["subNL"]
            step_description = step["explanation"]
            
            step_values, step_columns, step_tables = extract_properties_from_step(step_description)

            
            llm_align_flag = True
            syntax_align = {}  # if there is substring that syntatically matched a lot, use it, rather LLM
            # if values or columns or tables are not in the step
            all_props = step_values + step_columns + step_tables
            value_props = step_values
            for prop in all_props:
                # briefly handle props
                prop = prop.lower()
                prop = prop.replace("_", " ")
                prop = prop.strip("'")
                prop = prop.strip('"')
                # remove the last 's' in prop if it is a plural form
                if prop.endswith('s'):
                    prop = prop[:-1]
                
                
                
                # if any prop not mentioned in the question, directly set this alignment failed
                score, match = find_most_relevant_substring(nl_query, prop)
                if score < low_threshold:
                    llm_align_flag = False
                    print('!' * 50, flush=True)
                    print('prop not in nl_query:', prop, flush=True)
                    syntax_align = {}
                    break
                elif score > high_threshold:
                    # add match:100
                    if prop in value_props:
                        for chunk in nl_query_chunks:
                            if prop in chunk:
                                syntax_align[chunk] = 100
                    else:
                        syntax_align[match] = 100
                    
                    # find the corresponding chunk that contains the match with the hihgest score
                    max_score = 0
                    max_chunk = ""
                    for chunk in nl_query_chunks:
                        chunk_score = substring_match_score(chunk, match)
                        if chunk_score > max_score:
                            max_score = chunk_score
                            max_chunk = chunk
                    if max_score > 0.9:
                        syntax_align[max_chunk] = 100
                        print('max_chunk:', max_chunk, flush=True)
                    

                                
                            
                    
                    llm_align_flag = False
                    print('^' * 50, flush=True)
                    print('syntatically match a lot:', prop, flush=True)
                    # don't break here, we still need to check other props
                    
    
            if llm_align_flag:
                aligned_question = get_alignment(
                    nl_query_chunks, nl_query, sql_query, step_description, "", schema
                )


                # 1) Make sure each key in aligned_question is in the original NL query, otherwise, remove the key
                # 2) Make sure the value of each key in aligned_question is higher than 90, otherwise, remove the key
                temp_key_to_remove = []
                for key in aligned_question:
                    if key not in nl_query:
                        temp_key_to_remove.append(key)
                    elif aligned_question[key] < threshold:
                        temp_key_to_remove.append(key)

                for key in temp_key_to_remove:
                    aligned_question.pop(key)
            
            else:
                aligned_question = syntax_align

            step["aligned"] = copy.deepcopy(aligned_question)

    print('Aligned data:', flush=True)
    print(new_data, flush=True)
    print('*' * 50, flush=True)
    
    return new_data

# the portion: whether the second string is a substring of the first string
def substring_match_score(reference, query):
    # Convert both strings to lowercase for case-insensitive matching
    reference = reference.lower()
    query = query.lower()
    
    if not query:  # If query is empty, return 1 if reference is also empty, else 0
        return 1.0 if not reference else 0.0
    
    # Find the longest common substring
    longest_match = 0
    for i in range(len(query)):
        for j in range(i + 1, len(query) + 1):
            if query[i:j] in reference:
                longest_match = max(longest_match, j - i)
            else:
                break
    
    # Calculate the score based on the longest match relative to the query length
    return longest_match / len(query)

def find_most_relevant_substring(reference, query):
    # Convert both strings to lowercase for case-insensitive matching
    reference = reference.lower()
    query = query.lower()
    
    if not query:  # If query is empty, return 1 if reference is also empty, else 0
        return (1.0 if not reference else 0.0, "")
    
    best_score = 0
    best_match = ""
    
    for i in range(len(query)):
        for j in range(i + 1, len(query) + 1):
            substring = query[i:j]
            if substring in reference:
                score = len(substring) / len(query)
                if score > best_score:
                    best_score = score
                    best_match = substring
            else:
                break
    
    # Find the full context in the reference for the best match
    if best_match:
        start_index = reference.index(best_match)
        end_index = start_index + len(best_match)
        
        # Extend the match to include full words
        while start_index > 0 and reference[start_index - 1].isalnum():
            start_index -= 1
        while end_index < len(reference) and reference[end_index].isalnum():
            end_index += 1
        
        best_match = reference[start_index:end_index]
    
    return (best_score, best_match)

# Helper function: Given a natural language question, and the aligned parsed data, return a list of sub-strings that are not covred by all the aligned fields
# For example, the natural language question is "what is the name and id of the student", and the aligned substrings are "what is the name", and "student", then you should return remaining text "and id of the".
def get_uncovered_substrings(nl_query, aligned_substrings):
    # Create a list of characters to mark covered positions
    covered = [False] * len(nl_query)
    
    
    # Mark all covered positions
    for substring in aligned_substrings:
        start = nl_query.find(substring)
        if start != -1:
            for i in range(start, start + len(substring)):
                covered[i] = True

    # Find uncovered substrings
    uncovered = []
    current = []
    for i, char in enumerate(nl_query):
        if not covered[i]:
            current.append(char)
        elif current:
            uncovered.append("".join(current).strip())
            current = []

    if current:
        uncovered.append("".join(current).strip())

    # Remove empty strings
    uncovered = [s for s in uncovered if s]
    
    # filter out some inappropriate uncovered substrings
    uncovered = filter_out_chunks(uncovered)
    

    print("*" * 50, flush=True)
    print("NL Query:", nl_query, flush=True)
    print("Aligned Substrings:", aligned_substrings, flush=True)
    print("Remaining Substrings:", uncovered, flush=True)
    print("*" * 50, flush=True)

    return uncovered


# Helper function: filter out some inappropriate uncovered substrings
def filter_out_chunks(uncovered_substrings):
    
    print('## ' * 10)
    print('raw uncovered substrings:', uncovered_substrings)
    
    
    start_keywords = ["could ", "would ", "what ", "can ", "will " "where ", "when ", "how ", "which ", "who ", "why ", "whose "]
    
    equals_keywords = ["'", '"', ",", ".", "?", "in", "of", "or", "and", "with", "the"]
    
    new_uncovered_substrings = []
    # make sure each substring does not contain any keywords
    for substring in uncovered_substrings:
        if not any(substring.lower().startswith(keyword) for keyword in start_keywords) and not any(keyword == substring.lower() for keyword in equals_keywords):
            new_uncovered_substrings.append(substring)
    
    return new_uncovered_substrings
            

# Helper function: Given a SQL query, get the hybrid step-by-step explanation
def get_step_by_step_explanation(sql_query, schema):
    prompt = get_llm_sql2nl_prompt(sql_query, schema)
    openai_response = get_openai_response(prompt)

    print("&" * 30)
    print(openai_response)
    print("&" * 30)

    # extract json from the response
    explanation_data = extract_json_from_text(openai_response)

    if explanation_data == "":
        explanation_data = "Failed to generate step-by-steƒp description."

    # dump the explanation data to a local file
    with open("temp_explanation_data.json", "w") as file:
        json.dump(explanation_data, file)

    # read the explanation data from the local file
    with open("temp_explanation_data.json", "r") as file:
        explanation_data = json.load(file)

    return explanation_data


# Helper function: extract JSON data from the response
def extract_json_from_text(content):
    # Find the JSON part
    json_match = re.search(r"```(?:JSON|json)?\s*([\s\S]*?)\s*```", content)
    if not json_match:
        return json.dumps({"error": "No JSON found in the response"})

    json_str = json_match.group(1).strip()

    # Remove any "JSON" or "json" prefix if present
    json_str = re.sub(r"^(?:JSON|json)\s*", "", json_str)

    try:
        # Try to parse the JSON
        parsed_json = json.loads(json_str)
        # If successful, return the JSON string
        return json.dumps(parsed_json)
    except json.JSONDecodeError as e:
        # If parsing fails, attempt to fix common issues
        json_str = re.sub(
            r"'([^']*)':", r'"\1":', json_str
        )  # Replace single quotes with double quotes for keys
        json_str = re.sub(
            r":\s*\'([^\']*)\'\s*([,}])", r': "\1"\2', json_str
        )  # Replace single quotes with double quotes for values
        json_str = re.sub(
            r"([{,]\s*)(\w+)(\s*:)", r'\1"\2"\3', json_str
        )  # Add quotes to bare keys

        try:
            # Try to parse the fixed JSON
            parsed_json = json.loads(json_str)
            return json.dumps(parsed_json)
        except json.JSONDecodeError:
            # If it still fails, return an error JSON
            return json.dumps(
                {"error": f"Failed to parse JSON: {str(e)}", "raw_content": json_str}
            )


# Helper function: Given a schema from frontend, get a neat schema for llm reading
import re
import json


def get_neat_schema(data):
    def convert_to_valid_json(s):
        # Remove any leading/trailing whitespace
        s = s.strip()

        # Remove the outermost curly braces if present
        if s.startswith("{") and s.endswith("}"):
            s = s[1:-1]

        # Split the string into key-value pairs
        pairs = re.findall(r"[\'\"]?(\w+)[\'\"]?\s*:\s*([^,}]+)(?:,|$)", s)

        # Convert each pair to valid JSON
        json_pairs = []
        for key, value in pairs:
            # Ensure the key is wrapped in double quotes
            key = f'"{key}"'

            # Convert Python booleans and None to JSON format
            if value.strip() in ("True", "False", "None"):
                value = value.lower()
            # If it's a string, ensure it's wrapped in double quotes
            elif not value.strip().startswith("{") and not value.strip().startswith(
                "["
            ):
                value = f'"{value.strip()}"'

            json_pairs.append(f"{key}: {value}")

        # Join the pairs and wrap in curly braces
        return "{" + ", ".join(json_pairs) + "}"

    # Convert data to string if it's not already
    if not isinstance(data, str):
        data = str(data)

    data = convert_to_valid_json(data)

    try:
        processed_data = json.loads(data)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None

    result = {}

    for table_name, table_content in processed_data.items():
        result[table_name] = {"table_description": "", "columns": []}

        if isinstance(table_content, list):
            for column in table_content:
                if isinstance(column, dict):
                    if "table_description" in column:
                        result[table_name]["table_description"] = column[
                            "table_description"
                        ]
                    else:
                        result[table_name]["columns"].append(column)
        elif isinstance(table_content, dict):
            if "table_description" in table_content:
                result[table_name]["table_description"] = table_content[
                    "table_description"
                ]
            if "columns" in table_content:
                result[table_name]["columns"] = table_content["columns"]

    return result


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
                    print(f"Record: {[str(record[col]) for col in columns]}")
                    cursor.execute(insert_sql, [str(record[col]) for col in columns])

        conn.commit()

    # get absolute path
    db_path = os.path.abspath(db_path)

    return db_path


# a helper function to execute a SQL query on the database
def execute_query(query, db_path):
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)
        column_names = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        result = [dict(zip(column_names, row)) for row in rows]
        table_name = query.split()[3].split(".")[-1].lower()
        return {table_name: result}
    finally:
        if conn:
            conn.close()
        try:
            os.remove(db_path)
        except Exception as e:
            print(f"Error deleting database file: {e}")


# helper function that used to synthesize dataset from in batch
# including schema loading
# This is for automatic synthetic data generation
def auto_synthetic_data(schema_path, save_path, config_path, synthesized_DB_records_path, example_path, data_num):

    # load schema saved from frontend
    with open(schema_path, "r") as file:
        schema = json.load(file)

    print(schema, flush=True)

    # synthesize thousands of records for each table in the database
    records = generate_data(schema, num_records=2000)

    # save the records to a local file
    with open(
        synthesized_DB_records_path,
        "w",
    ) as file:
        json.dump(records, file)

    # load config from local file
    with open(
        config_path,
        "r",
    ) as file:
        config = json.load(file)



    
    print("Synthesizing NL2SQL data now...", flush=True)

    past_sqls = []  # store the past SQL queries, to avoid duplicates
    
    for i in range(data_num):
        try:
                    
            # synthesize a SQL query
            SQL = SQL_synthesizer.get_synthetic_SQL(schema, records, config, min_jonins=0)

            # avoid duplicate SQL queries
            while SQL in past_sqls:
                SQL = SQL_synthesizer.get_synthetic_SQL(schema, records, config, min_jonins=0)
            
            past_sqls.append(SQL)
            
            # synthesize a NL query
            try:
                step_by_step_explanation = rule_sql2nl_str(SQL)
            except:
                step_by_step_explanation = get_step_by_step_explanation(SQL, schema)

            # retrieve examples
            data_pool = load_data(example_path)
            # retrieved_examples = get_top_k_similar(k=5, data=data_pool, input_sql=SQL)
            retrieved_examples = get_threshold_similar_examples(
                input_sql=SQL, data=data_pool, threshold=0.6
            )

            nl_query = llm_summarize_nl_query(
                step_by_step_description=step_by_step_explanation,
                sql=SQL,
                examples=retrieved_examples,
                schema=str(schema),
            )
            
            # create the data point
            data_point = {
                "sql": SQL,
                "nl": nl_query,
                "rule_description": step_by_step_explanation,
                "related_examples": retrieved_examples,
            }

            # Append the single data point to the file immediately
            with open(save_path, "a") as file:
                json.dump(data_point, file)
                file.write("\n")  # Add a newline after each JSON object

            if (i + 1) % 10 == 0 or i == data_num - 1:
                print(f"Processed {i + 1} / {data_num} data points")

        except Exception as e:
            print(f"Error processing data point {i + 1}: {str(e)}")
            continue


    
    print(f"Synthetic data generation complete. Data saved to {save_path}")

    return save_path


# convert sql to rule-based step-by-step description string
def rule_sql2nl_str(sql_query):

    description = ""

    try:
        explanation_data = sql2nl(sql_query)

        step_cnt = 1

        for subquery in explanation_data:
            if len(explanation_data) > 1:
                description += f"# {subquery['number']}\n"

            for step in subquery["explanation"]:
                description += f"({step_cnt}) {step['explanation']}\n\n"
                step_cnt += 1

            step_cnt = 1

            print("\n")

    except:
        description = "Failed to generate rule-based step-by-step description."

    return description


# convert sql to llm-based step-by-step description string
# OBSOLETE
def llm_sql2nl_str(sql_query):

    prompt = get_llm_sql2nl_prompt(sql_query)
    description = get_openai_response(prompt)

    lines = description.split("\n")
    description = ""
    for line in lines:
        if line.strip() != "":
            description += line + "\n\n"

    return description


# Based on the step-by-step explanation, generate a NL query
def llm_summarize_nl_query(step_by_step_description, sql, schema, examples):

    prompt = get_nl_query_prompt(step_by_step_description, sql, schema, examples)

    nl_query = get_openai_response(prompt)

    # extract the NL query from the response <nl_query>...</nl_query>
    nl_query = extract_nl_query(nl_query)

    return nl_query


# extract from <nl_query> </nl_query>'
def extract_nl_query(llm_response):
    # extract the NL query from the response <nl_query>...</nl_query>
    nl_query = re.search(r"<nl_query>(.*)</nl_query>", llm_response).group(1)

    # if there are multiple lines in the description, remove the line starting with '#'
    nl_query_lines = nl_query.split("\n")
    nl_query = ""
    for line in nl_query_lines:
        if not line.startswith("#") and line.strip() != "":
            nl_query += line + "\n\n"

    return nl_query.strip()


# merge table comment to each column element, adapt the frontend to the backend schema
def merge_table_comment_to_column(schema):
    new_schema = {}
    for key in schema.keys():
        column_elements = schema[key]["columns"]
        table_description = schema[key]["comment"]
        new_col_list = []
        for col in column_elements:
            col["table_description"] = table_description
            new_col_list.append(copy.deepcopy(col))

        new_schema[key] = new_col_list

    return new_schema


@app.route("/step_by_step_description", methods=["POST"])
def sql_to_step_by_step_description():

    data = request.get_json()
    sql_query = data["sql"]
    schema = data["schema"]
    try:
        schema = get_neat_schema(schema)  # convert the schema to a neat format
    except Exception as e:
        raise Exception(f"Error converting schema to neat format: {str(e)}")
        schema = schema

    # rule_description = rule_sql2nl_str(sql_query)  # used for later symbolic + llm

    print("Generating step-by-step description for SQL query...", flush=True)
    # llm_description = llm_sql2nl_str(sql_query)

    explanation_data = get_step_by_step_explanation(sql_query, schema)


    # print('Dummy Step-by-step explanation data:', flush=True)
    # print(explanation_data, flush=True)

    return jsonify(
        {
            "explanation_data": str(explanation_data),
            # 'rule_description': rule_description,
        }
    )


# @app.route('/step_by_step_description', methods=['POST'])
# def OLD_sql_to_step_by_step_description():

#     data = request.get_json()
#     sql_query = data['sql']
#     schema= data['schema']

#     rule_description = rule_sql2nl_str(sql_query)

#     print('Generating step-by-step description for SQL query...', flush=True)
#     llm_description = llm_sql2nl_str(sql_query)

#     return jsonify({
#         'llm_description': llm_description,
#         'rule_description': rule_description,
#     })


# handle suggested NL query
@app.route("/suggested_nl", methods=["POST"])
def get_suggested_nl():
    data = request.get_json()
    sql_query = data["sql"]
    schema = data["schema"]
    step_by_step_llm = data["step_by_step_llm"]
    step_by_step_rule = data["step_by_step_rule"]
    parsed_step_by_step_data = data["parsed_step_by_step_data"]

    # if the parsed step-by-step data is empty, synthesize the step-by-step explanation
    if not parsed_step_by_step_data:
        parsed_step_by_step_data = get_step_by_step_explanation(sql_query, schema)

    # nl_query, retrieved_examples = get_simple_nl_and_examples(
    #     schema,
    #     sql_query,
    #     parsed_step_by_step_data,
    #     example_file_path="/Users/yuantian/Desktop/Projects/nl_sql_analyzer/backend/kg_examples_harvester.json",
    #     example_num=5,
    # )

    nl_query, retrieved_examples = get_nl_ICL(
        schema,
        sql_query,
        parsed_step_by_step_data,
        example_file_path="spider_example_pool.json",
        example_num=5,
    )

    return jsonify({"examples": retrieved_examples, "nl_query": nl_query})


# handle alignment check
@app.route("/check_alignment", methods=["POST"])
def check_alignment():
    data = request.get_json()
    sql_query = data["sql"]
    nl_query = data["nl"]
    schema = data["schema"]
    parsed_step_by_step_data = data["parsed_step_by_step_data"]

    alignment_data = get_alignment_data(
        parsed_step_by_step_data, nl_query, sql_query, schema
    )
    
    print('*' * 50, flush=True)
    print('Alignment data:', flush=True)
    print(alignment_data, flush=True)
    

    # get the uncovered substrings

    aligned_substrings = []

    for query in alignment_data:
        for step in query["explanation"]:
            aligned_dict = step["aligned"]
            for key in aligned_dict:
                if key in nl_query:
                    aligned_substrings.append(key)

    uncovered_substrings = get_uncovered_substrings(nl_query, aligned_substrings)
    
    print('Uncovered substrings:', flush=True)

    return jsonify(
        {"alignment_data": alignment_data, "uncovered_substrings": uncovered_substrings}
    )


# handle decomposition of NL query
@app.route("/sub_questions", methods=["POST"])
def get_sub_questions():
    data = request.get_json()
    nl_query = data["nl"]
    schema = data["schema"]
    use_schema = data["useSchema"]

    schema = get_neat_schema(schema)

    # print('Decomposing natural language query...', flush=True)
    # print(f'Using schema: {use_schema}', flush=True, end='\n\n')

    if not use_schema:
        schema = "N/A"

    sub_questions = nl_2_sub_questions(schema, nl_query)

    return jsonify({"sub_questions": sub_questions})


@app.route("/analyze", methods=["POST"])
def analyze():

    # run multiple times and get the average score
    analysis_num = 2

    data = request.get_json()
    sql_query = data["sql"]
    nl_query = data["nl"]
    schema = data["schema"]

    if schema == "":
        schema = "N/A"

    prompt = get_llm_nl_sql_equivalence_rating_prompt(
        database_schema=schema, generated_sql_query=sql_query, nl_query=nl_query
    )

    print("Analyzing equivalence between SQL and NL query...", flush=True)

    score_sum = 0
    analysis_history = ""
    for i in range(analysis_num):

        equivalence_analysis = get_openai_response(prompt)

        analysis_history += f">>> Analysis {i+1}:\n{equivalence_analysis}\n\n"

        score = get_score_from_response(equivalence_analysis)

        print("score:", score, flush=True)

        score_sum += float(score)
        # print(f'Analysis {i+1}: {score}', flush=True)

    # # get the prompt for summarizing the analysis candidate analysis
    # summarize_analysis_prompt = review_summarize_multiple_llm_nl_sql_equivalence_rating_prompt(analysis_history=analysis_history, database_schema=schema, generated_sql_query=sql_query, nl_query=nl_query)
    # # get response from LLM based on the prompt
    # equivalence_analysis = get_openai_response(summarize_analysis_prompt)

    # calculate the average score, round to the nearest integer
    final_score = int(score_sum / analysis_num)
    final_llm_score = get_score_from_response(equivalence_analysis)

    # process the raw analysis response
    # delete all lines starting with '#'
    equivalence_analysis_lines = equivalence_analysis.split("\n")
    equivalence_analysis = ""
    for line in equivalence_analysis_lines:
        if "equivalence score:" in line.lower():
            break

        if not line.startswith("#") and not line.startswith("*"):
            equivalence_analysis += line + "\n"

    # delete the score <score>...</score> from the response using regular expression
    equivalence_analysis = re.sub(r"<score>.*</score>", "", equivalence_analysis)

    return jsonify({"equivalence": equivalence_analysis, "score": final_score})


# retrieve the schema of the database from the local file from server
# the schema is stored in a json file, named 'kg_db.json'
@app.route("/retrieve_schema", methods=["GET"])
def retrieve_schema():
    print("Retrieving schema...", flush=True)

    local_schema = get_schema("kg_db.json")
    # # convert it to front-end friendly format
    # transformed_schema = transform_backend_schema_to_frontend_schema(local_schema)

    # just load the already transformed local schema file (with documentation of each entity)
    with open("schema_description/schema_description.json", "r") as file:
        transformed_schema = json.load(file)
        # print(transformed_schema, flush=True)

    # print(transformed_schema, flush=True)

    # # get the first key as the default table
    # default_table = list(transformed_schema.keys())[0]

    # get the intial records data by copying keys in transformed_schema, but all corresponding values are empty list
    intial_records = {}
    for key in transformed_schema.keys():
        intial_records[key] = []

    print("\nInitial records:", flush=True)
    print(intial_records, flush=True)

    # save transformed schema to a local file
    with open("schema.json", "w") as file:
        json.dump(transformed_schema, file)

    return jsonify(
        {
            "schema_data": transformed_schema,
            "initial_records": intial_records,
            "local_schema": str(transformed_schema),
            # 'local_schema': str(local_schema),
        }
    )


# update schema from the shemaTab
# necessary to compute initial empty records
@app.route("/update_schema", methods=["POST"])
def update_schema():
    print("Updating schema...", flush=True)

    data = request.get_json()
    updated_schema = data["schema"]

    print("\nUpdated schema:", flush=True)

    print(updated_schema, flush=True)
    


    # check if the format is frontend format, if it is, convert it to backend format
    # if the element of updated_schema has a key 'comment', it is frontend-format
    if (
        len(updated_schema) > 0
        and "comment" in updated_schema[list(updated_schema.keys())[0]]
    ):
        # convert it to backend format, merge table comment to each column element
        updated_schema = merge_table_comment_to_column(updated_schema)

    # replace all space in the schema keys with underscore
    updated_schema = replace_space_with_underscore(updated_schema)


    intial_records = {}
    for key in updated_schema.keys():
        intial_records[key] = []

    print("\nInitial records:", flush=True)
    print(intial_records, flush=True)

    # save transformed schema to a local file
    with open("edited_schema.json", "w") as file:
        json.dump(updated_schema, file)

    return jsonify(
        {
            "schema_data": updated_schema,
            "initial_records": intial_records,
            "local_schema": str(updated_schema),
        }
    )


@app.route("/synthesize_records", methods=["POST"])
def synthesize_records():
    print("Randomly synthesizing records...", flush=True)

    data = request.get_json()
    transformed_schema = data["schema"]
    
    # replace all space in the schema keys with underscore
    transformed_schema = replace_space_with_underscore(transformed_schema)
    
    # replace all space in the schema keys with underscore
    print("Schema is like this-------------", flush=True)
    print(transformed_schema)
    
    num = int(data["num"])  # number of new synthesized records

    # save the schema to a local file
    with open("saved_frontend_schema.json", "w") as file:
        json.dump(transformed_schema, file)

    print("Transformed schema for records synthesis:", flush=True)

    print("=" * 50)
    print(transformed_schema, flush=True)
    print("=" * 50)

    synthetic_records = generate_data(transformed_schema, num_records=num)

    # print('-'*50)
    # print(synthetic_records)
    # print('-'*50)

    return jsonify(
        {
            "synthetic_records": synthetic_records,
        }
    )


# save the synthesized records to a local file on the server
@app.route("/save_records", methods=["POST"])
def save_records():
    file_name = "synthetic_records.json"

    print("Saving records...", flush=True)

    data = request.get_json()
    records = data["records"]

    # get the full path of the file
    path = os.path.join(os.getcwd(), file_name)

    with open(file_name, "w") as file:
        json.dump(records, file)

    return jsonify({"status": "success", "path": path})


# load records from a local file on the server
@app.route("/load_records", methods=["GET"])
def load_records():
    file_name = "synthetic_records.json"

    print("Loading records...", flush=True)

    with open(file_name, "r") as file:
        records = json.load(file)

    return jsonify({"records": records})


# randomly synthesize a SQL query based on the schema and records
@app.route("/synthetic_sql", methods=["POST"])
def synthetic_sql():
    print("Randomly synthesizing SQL query...", flush=True)

    data = request.get_json()
    schema = data["schema"]
    records = data["records"]

    # read configuration from local file "/Users/yuantian/Desktop/Projects/nl_sql_analyzer/backend/learned_config.json"
    config = {}
    with open(
        "learned_config.json",
        "r",
    ) as file:
        config = json.load(file)

    SQL = SQL_synthesizer.get_synthetic_SQL(schema, records, config, min_jonins=0)


    return jsonify(
        {
            "synthetic_sql": SQL,
            "config": config,
        }
    )


# execute a SQL query on the database from the frontend, and return the result
@app.route("/execute_sql", methods=["POST"])
def execute_sql():
    data = request.get_json()
    sql_query = data["sql"]
    records = data["records"]

    print("Creating database...", flush=True)
    db_path = create_database(records)

    try:
        print("Executing SQL query...", flush=True)
        result = execute_query(sql_query, db_path)
        return jsonify({"result": result})
    finally:
        try:
            os.remove(db_path)
            print(f"Deleted temporary database: {db_path}")
        except Exception as e:
            print(f"Error deleting database file: {e}")


# handle the inject a certain step into current NL query
@app.route("/inject", methods=["POST"])
def inject():
    # given all the context (SQL query, NL question, schema), update the NL question by injecting/outweighting a certain step
    def inject_step_to_NL(
        sql_query, nl_question, subquestion, sql_clause, step_explanation, schema
    ):

        prompt = get_inject_step_prompt(
            sql_query, nl_question, step_explanation, schema
        )

        print("prompt:", prompt, flush=True)

        new_nl_query_response = get_openai_response(prompt)

        print("new_nl_query_response:", new_nl_query_response, flush=True)

        # extract the NL query from the response <nl_query>...</nl_query>
        new_nl_query = extract_nl_query(new_nl_query_response)

        return new_nl_query

    print("Injecting step into NL query...", flush=True)

    data = request.get_json()
    # print(data, flush=True)
    sql_query = data["sql"]
    nl_query = data["nl"]
    schema = data["schema"]
    sql_clause = data["sql_clause"]
    sub_question = data["corresponding_subquestion"]
    step_explanation = data["corresponding_explanation"]

    # generate new NL query by injecting the step
    new_nl_query = inject_step_to_NL(
        sql_query, nl_query, sub_question, sql_clause, step_explanation, schema
    )

    print("Finished injecting.", flush=True)

    return jsonify({"new_nl_query": new_nl_query})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
    # app.run(debug=True, host="0.0.0.0", port=3503)
