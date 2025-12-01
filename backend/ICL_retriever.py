# Author: Yuan Tian
# Gtihub: https://github.com/magic-YuanTian/SQLsynth


import json
import sqlparse
from difflib import SequenceMatcher
from typing import List, Tuple

def sql_similarity(sql1: str, sql2: str) -> float:
    def tokenize_and_normalize(sql):
        parsed = sqlparse.format(sql, keyword_case='upper', identifier_case='lower', strip_comments=True)
        tokens = sqlparse.parse(parsed)[0].flatten()
        return [str(token).strip() for token in tokens if str(token).strip()]
    
    def token_set_similarity(tokens1, tokens2):
        set1, set2 = set(tokens1), set(tokens2)
        if not set1 and not set2:
            return 1.0
        union = len(set1 | set2)
        if union == 0:
            return 0.0
        return len(set1 & set2) / union
    
    def sequence_similarity(tokens1, tokens2):
        return SequenceMatcher(None, tokens1, tokens2).ratio()
    
    def clause_similarity(tokens1, tokens2):
        def get_clauses(tokens):
            clauses = {'SELECT': [], 'FROM': [], 'JOIN': [], 'WHERE': [], 'GROUP BY': [], 'HAVING': [], 'ORDER BY': []}
            current_clause = None
            for token in tokens:
                if token in clauses:
                    current_clause = token
                elif current_clause:
                    clauses[current_clause].append(token)
            return clauses
        
        clauses1, clauses2 = get_clauses(tokens1), get_clauses(tokens2)
        similarities = []
        for clause in clauses1:
            sim = token_set_similarity(clauses1[clause], clauses2[clause])
            similarities.append(sim)
        return sum(similarities) / len(similarities) if similarities else 0
    
    def join_similarity(tokens1, tokens2):
        def extract_joins(tokens):
            joins = []
            is_join = False
            current_join = []
            for token in tokens:
                if token in ['JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN']:
                    if current_join:
                        joins.append(' '.join(current_join))
                    current_join = [token]
                    is_join = True
                elif is_join:
                    current_join.append(token)
                    if token == 'ON':
                        is_join = False
                        joins.append(' '.join(current_join))
                        current_join = []
            if current_join:
                joins.append(' '.join(current_join))
            return joins
        
        joins1 = extract_joins(tokens1)
        joins2 = extract_joins(tokens2)
        
        if not joins1 and not joins2:
            return 1.0
        elif not joins1 or not joins2:
            return 0.0
        
        join_sim = token_set_similarity(joins1, joins2)
        return join_sim
    
    
    try:
        tokens1 = tokenize_and_normalize(sql1)
        tokens2 = tokenize_and_normalize(sql2)
        
        set_sim = token_set_similarity(tokens1, tokens2)
        seq_sim = sequence_similarity(tokens1, tokens2)
        clause_sim = clause_similarity(tokens1, tokens2)
        join_sim = join_similarity(tokens1, tokens2)
        
        final_sim = (0.25 * set_sim + 0.25 * seq_sim + 0.25 * clause_sim + 0.25 * join_sim)
    
    except Exception as e:
        print(f"Error: {e}")
        final_sim = 0.0    
    
        
    return final_sim

def get_top_k_similar(input_sql: str, data: List[dict], k: int) -> List[Tuple[str, str, float]]:
    similarities = []
    for item in data:
        if 'sql_query' in item and item['sql_query']:
            similarity = sql_similarity(input_sql, item['sql_query'])
            
            new_item = {}
            new_item['sql_query'] = item['sql_query']
            new_item['nl_query'] = item['nl_query']
            new_item['similarity'] = similarity
            similarities.append(new_item)
            
    
    similarities.sort(key=lambda x: x['similarity'], reverse=True)
    return similarities[:k]

# get similar examples above a certain threshold, the threshold is a float between 0 and 1, the default is 0.85
def get_threshold_similar_examples(input_sql: str, data: List[dict], threshold: float = 0.85) -> List[Tuple[str, str, float]]:
    similarities = []
    
    for item in data:
        if 'sql_query' in item and item['sql_query']:
            similarity = sql_similarity(input_sql, item['sql_query'])
            if similarity >= threshold:
                new_item = {}
                new_item['sql_query'] = item['sql_query']
                new_item['nl_query'] = item['nl_query']
                new_item['similarity'] = similarity
                similarities.append(new_item)
            
    
    similarities.sort(key=lambda x: x['similarity'], reverse=True)
    return similarities


def load_data(file_path: str) -> List[dict]:
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data


if __name__ == "__main__":
    file_path = "/Users/yuantian/Desktop/Projects/nl_sql_analyzer/backend/kg_examples_harvester.json"  # Replace with your actual file path
    input_sql = "SELECT COUNT(*) FROM users WHERE age > 18"  # Replace with your input SQL query
    k = 5  # Number of top similar queries to retrieve

    retrieved_examples = get_top_k_similar(input_sql=input_sql, data = load_data(file_path), k=k)
    print(retrieved_examples)
    
    