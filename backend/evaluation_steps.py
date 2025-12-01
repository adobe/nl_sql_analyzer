################################
# val: number(float)/string(str)/sql(dict)
# col_unit: (agg_id, col_id, isDistinct(bool))
# val_unit: (unit_op, col_unit1, col_unit2)
# table_unit: (table_type, col_unit/sql)
# cond_unit: (not_op, op_id, val_unit, val1, val2)
# condition: [cond_unit1, 'and'/'or', cond_unit2, ...]
# sql {
#   'select': (isDistinct(bool), [(agg_id, val_unit), (agg_id, val_unit), ...])
#   'from': {'table_units': [table_unit1, table_unit2, ...], 'conds': condition}
#   'where': condition
#   'groupBy': [col_unit1, col_unit2, ...]
#   'orderBy': ('asc'/'desc', [val_unit1, val_unit2, ...])
#   'having': condition
#   'limit': None/limit value
#   'intersect': None/sql
#   'except': None/sql
#   'union': None/sql
# }
################################
from __future__ import print_function
import os, sys

sys.path.append(os.getcwd())
sys.path.append(os.getcwd() + 'mine')
sys.path.append('MISP-mine')



import time
import nltk
import pathlib
import gdown
import torch
import json
import sqlite3
import traceback
import argparse
import re
from allennlp.common.params import *
from allennlp.common import Params
from allennlp.models import Model
from allennlp.data import DatasetReader, Instance
import tqdm
from allennlp.models.archival import Archive, load_archive, archive_model
from allennlp.data.vocabulary import Vocabulary
from allennlp.predictors import Predictor

from process_sql import tokenize, get_schema, get_tables_with_alias, Schema, get_sql

sys.path.append('..')
from backend.SmBop import *
from backend.SmBop.smbop.modules.relation_transformer import *
import backend.SmBop.smbop.utils.node_util as node_util
from backend.SmBop.smbop.models.smbop import SmbopParser
from backend.SmBop.smbop.modules.lxmert import LxmertCrossAttentionLayer
from backend.SmBop.smbop.dataset_readers.spider import SmbopSpiderDatasetReader
from backend.SQL2NL.SQL2NL import *
from backend.SQL2NL.explanation2subexpression import *

from fuzzywuzzy import fuzz
from fuzzywuzzy import process

# here load structured SmBop
os.chdir("..")

from backend.structuredSmBop import run_structure

print(os.getcwd(), flush=True)  # print current work directory
# load normal SMBOP
os.chdir("backend/SmBop")
print('Loading normal SmBop...', flush=True)
overrides = {
    "dataset_reader": {
        "tables_file": "dataset/tables.json",
        "dataset_path": "dataset/database",
    },
    "validation_dataset_reader": {
    "tables_file": "dataset/tables.json",
    "dataset_path": "dataset/database",
    }
}
predictor = Predictor.from_path(
    "pretrained_original_model.tar.gz", cuda_device=0, overrides=overrides
)
instance_0 = predictor._dataset_reader.text_to_instance(
    utterance="asds", db_id="aircraft"
)
predictor._dataset_reader.apply_token_indexers(instance_0)

def inference(question,db_id):
  instance = predictor._dataset_reader.text_to_instance(
      utterance=question, db_id=db_id,
  )

  predictor._dataset_reader.apply_token_indexers(instance)

  with torch.cuda.amp.autocast(enabled=True):
      out = predictor._model.forward_on_instances(
          [instance, instance_0]
      )
      return out[0]["sql_list"]

os.chdir("../../spider_evaluation")

# load normal SMBOP
os.chdir("../backend/SmBop")
overrides = {
    "dataset_reader": {
        "tables_file": "dataset/tables.json",
        "dataset_path": "dataset/database",
    },
    "validation_dataset_reader": {
    "tables_file": "dataset/tables.json",
    "dataset_path": "dataset/database",
    }
}
predictor = Predictor.from_path(
    "pretrained_original_model.tar.gz", cuda_device=0, overrides=overrides
)
instance_0 = predictor._dataset_reader.text_to_instance(
    utterance="asds", db_id="aircraft"
)
predictor._dataset_reader.apply_token_indexers(instance_0)

def inference(question,db_id):
  instance = predictor._dataset_reader.text_to_instance(
      utterance=question, db_id=db_id,
  )

  predictor._dataset_reader.apply_token_indexers(instance)

  with torch.cuda.amp.autocast(enabled=True):
      out = predictor._model.forward_on_instances(
          [instance, instance_0]
      )
      return out[0]["sql_list"]

os.chdir("../../spider_evaluation")
print('Loading normal SmBop...', flush=True)

# Flag to disable value evaluation
DISABLE_VALUE = True
# Flag to disable distinct in select evaluation
DISABLE_DISTINCT = True


CLAUSE_KEYWORDS = ('select', 'from', 'where', 'group', 'order', 'limit', 'intersect', 'union', 'except')
JOIN_KEYWORDS = ('join', 'on', 'as')

WHERE_OPS = ('not', 'between', '=', '>', '<', '>=', '<=', '!=', 'in', 'like', 'is', 'exists')
UNIT_OPS = ('none', '-', '+', "*", '/')
AGG_OPS = ('none', 'max', 'min', 'count', 'sum', 'avg')
TABLE_TYPE = {
    'sql': "sql",
    'table_unit': "table_unit",
}

COND_OPS = ('and', 'or')
SQL_OPS = ('intersect', 'union', 'except')
ORDER_OPS = ('desc', 'asc')


HARDNESS = {
    "component1": ('where', 'group', 'order', 'limit', 'join', 'or', 'like'),
    "component2": ('except', 'union', 'intersect')
}


def condition_has_or(conds):
    return 'or' in conds[1::2]


def condition_has_like(conds):
    return WHERE_OPS.index('like') in [cond_unit[1] for cond_unit in conds[::2]]


def condition_has_sql(conds):
    for cond_unit in conds[::2]:
        val1, val2 = cond_unit[3], cond_unit[4]
        if val1 is not None and type(val1) is dict:
            return True
        if val2 is not None and type(val2) is dict:
            return True
    return False


def val_has_op(val_unit):
    return val_unit[0] != UNIT_OPS.index('none')


def has_agg(unit):
    return unit[0] != AGG_OPS.index('none')


def accuracy(count, total):
    if count == total:
        return 1
    return 0


def recall(count, total):
    if count == total:
        return 1
    return 0


def F1(acc, rec):
    if (acc + rec) == 0:
        return 0
    return (2. * acc * rec) / (acc + rec)


def get_scores(count, pred_total, label_total):
    if pred_total != label_total:
        return 0,0,0
    elif count == pred_total:
        return 1,1,1
    return 0,0,0


def eval_sel(pred, label):
    pred_sel = pred['select'][1]
    label_sel = label['select'][1]
    label_wo_agg = [unit[1] for unit in label_sel]
    pred_total = len(pred_sel)
    label_total = len(label_sel)
    cnt = 0
    cnt_wo_agg = 0

    for unit in pred_sel:
        if unit in label_sel:
            cnt += 1
            label_sel.remove(unit)
        if unit[1] in label_wo_agg:
            cnt_wo_agg += 1
            label_wo_agg.remove(unit[1])

    return label_total, pred_total, cnt, cnt_wo_agg


def eval_where(pred, label):
    pred_conds = [unit for unit in pred['where'][::2]]
    label_conds = [unit for unit in label['where'][::2]]
    label_wo_agg = [unit[2] for unit in label_conds]
    pred_total = len(pred_conds)
    label_total = len(label_conds)
    cnt = 0
    cnt_wo_agg = 0

    for unit in pred_conds:
        if unit in label_conds:
            cnt += 1
            label_conds.remove(unit)
        if unit[2] in label_wo_agg:
            cnt_wo_agg += 1
            label_wo_agg.remove(unit[2])

    return label_total, pred_total, cnt, cnt_wo_agg


def eval_group(pred, label):
    pred_cols = [unit[1] for unit in pred['groupBy']]
    label_cols = [unit[1] for unit in label['groupBy']]
    pred_total = len(pred_cols)
    label_total = len(label_cols)
    cnt = 0
    pred_cols = [pred.split(".")[1] if "." in pred else pred for pred in pred_cols]
    label_cols = [label.split(".")[1] if "." in label else label for label in label_cols]
    for col in pred_cols:
        if col in label_cols:
            cnt += 1
            label_cols.remove(col)
    return label_total, pred_total, cnt


def eval_having(pred, label):
    pred_total = label_total = cnt = 0
    if len(pred['groupBy']) > 0:
        pred_total = 1
    if len(label['groupBy']) > 0:
        label_total = 1

    pred_cols = [unit[1] for unit in pred['groupBy']]
    label_cols = [unit[1] for unit in label['groupBy']]
    if pred_total == label_total == 1 \
            and pred_cols == label_cols \
            and pred['having'] == label['having']:
        cnt = 1

    return label_total, pred_total, cnt


def eval_order(pred, label):
    pred_total = label_total = cnt = 0
    if len(pred['orderBy']) > 0:
        pred_total = 1
    if len(label['orderBy']) > 0:
        label_total = 1
    if len(label['orderBy']) > 0 and pred['orderBy'] == label['orderBy'] and \
            ((pred['limit'] is None and label['limit'] is None) or (pred['limit'] is not None and label['limit'] is not None)):
        cnt = 1
    return label_total, pred_total, cnt


def eval_and_or(pred, label):
    pred_ao = pred['where'][1::2]
    label_ao = label['where'][1::2]
    pred_ao = set(pred_ao)
    label_ao = set(label_ao)

    if pred_ao == label_ao:
        return 1,1,1
    return len(pred_ao),len(label_ao),0


def get_nestedSQL(sql):
    nested = []
    for cond_unit in sql['from']['conds'][::2] + sql['where'][::2] + sql['having'][::2]:
        if type(cond_unit[3]) is dict:
            nested.append(cond_unit[3])
        if type(cond_unit[4]) is dict:
            nested.append(cond_unit[4])
    if sql['intersect'] is not None:
        nested.append(sql['intersect'])
    if sql['except'] is not None:
        nested.append(sql['except'])
    if sql['union'] is not None:
        nested.append(sql['union'])
    return nested


def eval_nested(pred, label):
    label_total = 0
    pred_total = 0
    cnt = 0
    if pred is not None:
        pred_total += 1
    if label is not None:
        label_total += 1
    if pred is not None and label is not None:
        cnt += Evaluator().eval_exact_match(pred, label)
    return label_total, pred_total, cnt


def eval_IUEN(pred, label):
    lt1, pt1, cnt1 = eval_nested(pred['intersect'], label['intersect'])
    lt2, pt2, cnt2 = eval_nested(pred['except'], label['except'])
    lt3, pt3, cnt3 = eval_nested(pred['union'], label['union'])
    label_total = lt1 + lt2 + lt3
    pred_total = pt1 + pt2 + pt3
    cnt = cnt1 + cnt2 + cnt3
    return label_total, pred_total, cnt


def get_keywords(sql):
    res = set()
    if len(sql['where']) > 0:
        res.add('where')
    if len(sql['groupBy']) > 0:
        res.add('group')
    if len(sql['having']) > 0:
        res.add('having')
    if len(sql['orderBy']) > 0:
        res.add(sql['orderBy'][0])
        res.add('order')
    if sql['limit'] is not None:
        res.add('limit')
    if sql['except'] is not None:
        res.add('except')
    if sql['union'] is not None:
        res.add('union')
    if sql['intersect'] is not None:
        res.add('intersect')

    # or keyword
    ao = sql['from']['conds'][1::2] + sql['where'][1::2] + sql['having'][1::2]
    if len([token for token in ao if token == 'or']) > 0:
        res.add('or')

    cond_units = sql['from']['conds'][::2] + sql['where'][::2] + sql['having'][::2]
    # not keyword
    if len([cond_unit for cond_unit in cond_units if cond_unit[0]]) > 0:
        res.add('not')

    # in keyword
    if len([cond_unit for cond_unit in cond_units if cond_unit[1] == WHERE_OPS.index('in')]) > 0:
        res.add('in')

    # like keyword
    if len([cond_unit for cond_unit in cond_units if cond_unit[1] == WHERE_OPS.index('like')]) > 0:
        res.add('like')

    return res


def eval_keywords(pred, label):
    pred_keywords = get_keywords(pred)
    label_keywords = get_keywords(label)
    pred_total = len(pred_keywords)
    label_total = len(label_keywords)
    cnt = 0

    for k in pred_keywords:
        if k in label_keywords:
            cnt += 1
    return label_total, pred_total, cnt


def count_agg(units):
    return len([unit for unit in units if has_agg(unit)])


def count_component1(sql):
    count = 0
    if len(sql['where']) > 0:
        count += 1
    if len(sql['groupBy']) > 0:
        count += 1
    if len(sql['orderBy']) > 0:
        count += 1
    if sql['limit'] is not None:
        count += 1
    if len(sql['from']['table_units']) > 0:  # JOIN
        count += len(sql['from']['table_units']) - 1

    ao = sql['from']['conds'][1::2] + sql['where'][1::2] + sql['having'][1::2]
    count += len([token for token in ao if token == 'or'])
    cond_units = sql['from']['conds'][::2] + sql['where'][::2] + sql['having'][::2]
    count += len([cond_unit for cond_unit in cond_units if cond_unit[1] == WHERE_OPS.index('like')])

    return count


def count_component2(sql):
    nested = get_nestedSQL(sql)
    return len(nested)


def count_others(sql):
    count = 0
    # number of aggregation
    agg_count = count_agg(sql['select'][1])
    agg_count += count_agg(sql['where'][::2])
    agg_count += count_agg(sql['groupBy'])
    if len(sql['orderBy']) > 0:
        agg_count += count_agg([unit[1] for unit in sql['orderBy'][1] if unit[1]] +
                            [unit[2] for unit in sql['orderBy'][1] if unit[2]])
    agg_count += count_agg(sql['having'])
    if agg_count > 1:
        count += 1

    # number of select columns
    if len(sql['select'][1]) > 1:
        count += 1

    # number of where conditions
    if len(sql['where']) > 1:
        count += 1

    # number of group by clauses
    if len(sql['groupBy']) > 1:
        count += 1

    return count


class Evaluator:
    """A simple evaluator"""
    def __init__(self):
        self.partial_scores = None

    def eval_hardness(self, sql):
        count_comp1_ = count_component1(sql)
        count_comp2_ = count_component2(sql)
        count_others_ = count_others(sql)

        if count_comp1_ <= 1 and count_others_ == 0 and count_comp2_ == 0:
            return "easy"
        elif (count_others_ <= 2 and count_comp1_ <= 1 and count_comp2_ == 0) or \
                (count_comp1_ <= 2 and count_others_ < 2 and count_comp2_ == 0):
            return "medium"
        elif (count_others_ > 2 and count_comp1_ <= 2 and count_comp2_ == 0) or \
                (2 < count_comp1_ <= 3 and count_others_ <= 2 and count_comp2_ == 0) or \
                (count_comp1_ <= 1 and count_others_ == 0 and count_comp2_ <= 1):
            return "hard"
        else:
            return "extra"

    def eval_exact_match(self, pred, label):
        partial_scores = self.eval_partial_match(pred, label)
        self.partial_scores = partial_scores

        for _, score in partial_scores.items():
            if score['f1'] != 1:
                return 0
        if len(label['from']['table_units']) > 0:
            label_tables = sorted(label['from']['table_units'])
            pred_tables = sorted(pred['from']['table_units'])
            return label_tables == pred_tables
        return 1

    def eval_partial_match(self, pred, label):
        res = {}

        label_total, pred_total, cnt, cnt_wo_agg = eval_sel(pred, label)
        acc, rec, f1 = get_scores(cnt, pred_total, label_total)
        res['select'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}
        acc, rec, f1 = get_scores(cnt_wo_agg, pred_total, label_total)
        res['select(no AGG)'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}

        label_total, pred_total, cnt, cnt_wo_agg = eval_where(pred, label)
        acc, rec, f1 = get_scores(cnt, pred_total, label_total)
        res['where'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}
        acc, rec, f1 = get_scores(cnt_wo_agg, pred_total, label_total)
        res['where(no OP)'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}

        label_total, pred_total, cnt = eval_group(pred, label)
        acc, rec, f1 = get_scores(cnt, pred_total, label_total)
        res['group(no Having)'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}

        label_total, pred_total, cnt = eval_having(pred, label)
        acc, rec, f1 = get_scores(cnt, pred_total, label_total)
        res['group'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}

        label_total, pred_total, cnt = eval_order(pred, label)
        acc, rec, f1 = get_scores(cnt, pred_total, label_total)
        res['order'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}

        label_total, pred_total, cnt = eval_and_or(pred, label)
        acc, rec, f1 = get_scores(cnt, pred_total, label_total)
        res['and/or'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}

        label_total, pred_total, cnt = eval_IUEN(pred, label)
        acc, rec, f1 = get_scores(cnt, pred_total, label_total)
        res['IUEN'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}

        label_total, pred_total, cnt = eval_keywords(pred, label)
        acc, rec, f1 = get_scores(cnt, pred_total, label_total)
        res['keywords'] = {'acc': acc, 'rec': rec, 'f1': f1,'label_total':label_total,'pred_total':pred_total}

        return res


def isValidSQL(sql, db):
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
    except:
        return False
    return True


def print_scores(scores, etype):
    levels = ['easy', 'medium', 'hard', 'extra', 'all']
    partial_types = ['select', 'select(no AGG)', 'where', 'where(no OP)', 'group(no Having)',
                     'group', 'order', 'and/or', 'IUEN', 'keywords']

    print("{:20} {:20} {:20} {:20} {:20} {:20}".format("", *levels))
    counts = [scores[level]['count'] for level in levels]
    print("{:20} {:<20d} {:<20d} {:<20d} {:<20d} {:<20d}".format("count", *counts))

    if etype in ["all", "exec"]:
        print('=====================   EXECUTION ACCURACY     =====================')
        this_scores = [scores[level]['exec'] for level in levels]
        print("{:20} {:<20.3f} {:<20.3f} {:<20.3f} {:<20.3f} {:<20.3f}".format("execution", *this_scores))

    if etype in ["all", "match"]:
        print('\n====================== EXACT MATCHING ACCURACY =====================')
        exact_scores = [scores[level]['exact'] for level in levels]
        print("{:20} {:<20.3f} {:<20.3f} {:<20.3f} {:<20.3f} {:<20.3f}".format("exact match", *exact_scores))
        print('\n---------------------PARTIAL MATCHING ACCURACY----------------------')
        for type_ in partial_types:
            this_scores = [scores[level]['partial'][type_]['acc'] for level in levels]
            print("{:20} {:<20.3f} {:<20.3f} {:<20.3f} {:<20.3f} {:<20.3f}".format(type_, *this_scores))

        print('---------------------- PARTIAL MATCHING RECALL ----------------------')
        for type_ in partial_types:
            this_scores = [scores[level]['partial'][type_]['rec'] for level in levels]
            print("{:20} {:<20.3f} {:<20.3f} {:<20.3f} {:<20.3f} {:<20.3f}".format(type_, *this_scores))

        print('---------------------- PARTIAL MATCHING F1 --------------------------')
        for type_ in partial_types:
            this_scores = [scores[level]['partial'][type_]['f1'] for level in levels]
            print("{:20} {:<20.3f} {:<20.3f} {:<20.3f} {:<20.3f} {:<20.3f}".format(type_, *this_scores))


def evaluate(gold, predict, db_dir, etype, kmaps):
    # figure out why hard level is lower
    error_prediction_path = "predicted_error.json"
    # error_type = 'hard'

    # question_list = []

    temp_error_list = []

    temp_error = {
        # 'db id': '',
        # 'gold': '',
        # 'pred': '',
        # 'hardness': '',
        # 'question': '',
        # 'one-shot': '',
        # 'explanation': ''
        # # 'partial score': {}
    }

    # with open(gold) as f:
    #     question_list = [l.strip().split('\t')[1] for l in f.readlines() if len(l.strip()) > 0]

    with open('question.txt') as f:
        question_list = [l.strip() for l in f.readlines() if len(l.strip()) > 0]

    with open(gold) as f:
        glist = [l.strip().split('\t') for l in f.readlines() if len(l.strip()) > 0]

    with open(predict) as f:
        plist = [l.strip().split('\t') for l in f.readlines() if len(l.strip()) > 0]

    with open('pred_NL2SQL.txt') as f:
        ori_plist = [l.strip().split('\t') for l in f.readlines() if len(l.strip()) > 0]

    # plist = [("select max(Share),min(Share) from performance where Type != 'terminal'", "orchestra")]
    # glist = [("SELECT max(SHARE) ,  min(SHARE) FROM performance WHERE TYPE != 'Live final'", "orchestra")]
    evaluator = Evaluator()

    levels = ['easy', 'medium', 'hard', 'extra', 'all']
    partial_types = ['select', 'select(no AGG)', 'where', 'where(no OP)', 'group(no Having)',
                     'group', 'order', 'and/or', 'IUEN', 'keywords']
    entries = []
    scores = {}

    for level in levels:
        scores[level] = {'count': 0, 'partial': {}, 'exact': 0.}
        scores[level]['exec'] = 0
        for type_ in partial_types:
            scores[level]['partial'][type_] = {'acc': 0., 'rec': 0., 'f1': 0.,'acc_count':0,'rec_count':0}

    eval_err_num = 0
    temp_cnt = 0


    for ori, p, g, question in zip(ori_plist, plist, glist, question_list):
        temp_cnt += 1
        ori_pred_sql = ori[0]
        p_str = p[0]
        g_str, db = g

        db_name = db
        db = os.path.join(db_dir, db, db + ".sqlite")
        schema = Schema(get_schema(db))


        try:
            g_sql = get_sql(schema, g_str)
        except Exception as e:
            continue

        hardness = evaluator.eval_hardness(g_sql)
        scores[hardness]['count'] += 1
        scores['all']['count'] += 1

        try:
            p_sql = get_sql(schema, p_str)
        except:
            # If p_sql is not valid, then we will use an empty sql to evaluate with the correct sql
            p_sql = {
            "except": None,
            "from": {
                "conds": [],
                "table_units": []
            },
            "groupBy": [],
            "having": [],
            "intersect": None,
            "limit": None,
            "orderBy": [],
            "select": [
                False,
                []
            ],
            "union": None,
            "where": []
            }
            eval_err_num += 1
            print("eval_err_num:{}".format(eval_err_num), flush=True)

        # rebuild sql for value evaluation
        kmap = kmaps[db_name]
        g_valid_col_units = build_valid_col_units(g_sql['from']['table_units'], schema)
        g_sql = rebuild_sql_val(g_sql)
        g_sql = rebuild_sql_col(g_valid_col_units, g_sql, kmap)
        p_valid_col_units = build_valid_col_units(p_sql['from']['table_units'], schema)
        p_sql = rebuild_sql_val(p_sql)
        p_sql = rebuild_sql_col(p_valid_col_units, p_sql, kmap)

        if etype in ["all", "exec"]:
            exec_score = eval_exec_match(db, p_str, g_str, p_sql, g_sql)
            if exec_score:
                scores[hardness]['exec'] += 1.0
                scores['all']['exec'] += 1.0
            else:
                # store the information
                # if hardness == error_type:

                # structured_exp = sql2nl(g[0])

                temp_error['db id'] = g[1]
                temp_error['question'] = question
                temp_error['hardness'] = hardness
                temp_error['gold'] = g[0]
                temp_error['pred'] = p[0]
                temp_error['one-shot'] = ori_pred_sql
                temp_error_list.append(temp_error)
                # temp_error['explanation'] = structured_exp
                temp_error['instance id'] = temp_cnt

                # empty temp error
                temp_error = {
                    # 'db id': '',
                    # 'gold': '',
                    # 'pred': '',
                    # 'hardness': '',
                    # 'question': '',
                    # 'one-shot': '',
                    # 'explanation': ''
                }

                print('\n\n' + '-' * 50)
                print(temp_cnt)
                print('-' * 50)
                print('dbid: ', db_name)
                print("\ngold:")
                print(g_str)
                print("\none-shot pred:")
                print(ori_pred_sql)
                print("\nuser simulation pred:")
                print(p_str)

        if etype in ["all", "match"]:
            exact_score = evaluator.eval_exact_match(p_sql, g_sql)
            partial_scores = evaluator.partial_scores
            if exact_score == 0:
                print("{} pred: {}".format(hardness,p_str))
                print("{} gold: {}".format(hardness,g_str))
                print("")
            scores[hardness]['exact'] += exact_score
            scores['all']['exact'] += exact_score
            for type_ in partial_types:
                if partial_scores[type_]['pred_total'] > 0:
                    scores[hardness]['partial'][type_]['acc'] += partial_scores[type_]['acc']
                    scores[hardness]['partial'][type_]['acc_count'] += 1
                if partial_scores[type_]['label_total'] > 0:
                    scores[hardness]['partial'][type_]['rec'] += partial_scores[type_]['rec']
                    scores[hardness]['partial'][type_]['rec_count'] += 1
                scores[hardness]['partial'][type_]['f1'] += partial_scores[type_]['f1']
                if partial_scores[type_]['pred_total'] > 0:
                    scores['all']['partial'][type_]['acc'] += partial_scores[type_]['acc']
                    scores['all']['partial'][type_]['acc_count'] += 1
                if partial_scores[type_]['label_total'] > 0:
                    scores['all']['partial'][type_]['rec'] += partial_scores[type_]['rec']
                    scores['all']['partial'][type_]['rec_count'] += 1
                scores['all']['partial'][type_]['f1'] += partial_scores[type_]['f1']

            entries.append({
                'predictSQL': p_str,
                'goldSQL': g_str,
                'hardness': hardness,
                'exact': exact_score,
                'partial': partial_scores
            })

    for level in levels:
        if scores[level]['count'] == 0:
            continue
        if etype in ["all", "exec"]:
            scores[level]['exec'] /= scores[level]['count']

        if etype in ["all", "match"]:
            scores[level]['exact'] /= scores[level]['count']
            for type_ in partial_types:
                if scores[level]['partial'][type_]['acc_count'] == 0:
                    scores[level]['partial'][type_]['acc'] = 0
                else:
                    scores[level]['partial'][type_]['acc'] = scores[level]['partial'][type_]['acc'] / \
                                                             scores[level]['partial'][type_]['acc_count'] * 1.0
                if scores[level]['partial'][type_]['rec_count'] == 0:
                    scores[level]['partial'][type_]['rec'] = 0
                else:
                    scores[level]['partial'][type_]['rec'] = scores[level]['partial'][type_]['rec'] / \
                                                             scores[level]['partial'][type_]['rec_count'] * 1.0
                if scores[level]['partial'][type_]['acc'] == 0 and scores[level]['partial'][type_]['rec'] == 0:
                    scores[level]['partial'][type_]['f1'] = 1
                else:
                    scores[level]['partial'][type_]['f1'] = \
                        2.0 * scores[level]['partial'][type_]['acc'] * scores[level]['partial'][type_]['rec'] / (
                        scores[level]['partial'][type_]['rec'] + scores[level]['partial'][type_]['acc'])


    # sort errors based on the hardness

    levels = ['easy', 'medium', 'hard', 'extra']

    sorted_list = []

    for level in levels:
        for data in temp_error_list:
            if data['hardness'].lower() == level.lower():
                sorted_list.append(data)

    with open(error_prediction_path, 'w') as error_file:
        outputFile = json.dumps(sorted_list)
        error_file.write(outputFile)

    print_scores(scores, etype)


def eval_exec_match(db, p_str, g_str, pred, gold):
    """
    return 1 if the values between prediction and gold are matching
    in the corresponding index. Currently not support multiple col_unit(pairs).
    """

    p_str = addCollateNocase(p_str)
    g_str = addCollateNocase(g_str)

    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    try:
        cursor.execute(p_str)
        p_res = cursor.fetchall()
    except Exception as e:
        print(e)
        return False

    try:
        cursor.execute(g_str)
    except Exception as e:
        print(e)

    q_res = cursor.fetchall()

    def res_map(res, val_units):
        rmap = {}
        for idx, val_unit in enumerate(val_units):
            key = tuple(val_unit[1]) if not val_unit[2] else (val_unit[0], tuple(val_unit[1]), tuple(val_unit[2]))
            rmap[key] = [r[idx] for r in res]
        return rmap

    p_val_units = [unit[1] for unit in pred['select'][1]]
    q_val_units = [unit[1] for unit in gold['select'][1]]

    res1 = res_map(p_res, p_val_units)
    res2 = res_map(q_res, q_val_units)

    if res1 != res2:
        print('different res')

    return res1 == res2


# Rebuild SQL functions for value evaluation
def rebuild_cond_unit_val(cond_unit):
    if cond_unit is None or not DISABLE_VALUE:
        return cond_unit

    not_op, op_id, val_unit, val1, val2 = cond_unit
    if type(val1) is not dict:
        val1 = None
    else:
        val1 = rebuild_sql_val(val1)
    if type(val2) is not dict:
        val2 = None
    else:
        val2 = rebuild_sql_val(val2)
    return not_op, op_id, val_unit, val1, val2


def rebuild_condition_val(condition):
    if condition is None or not DISABLE_VALUE:
        return condition

    res = []
    for idx, it in enumerate(condition):
        if idx % 2 == 0:
            res.append(rebuild_cond_unit_val(it))
        else:
            res.append(it)
    return res


def rebuild_sql_val(sql):
    if sql is None or not DISABLE_VALUE:
        return sql

    sql['from']['conds'] = rebuild_condition_val(sql['from']['conds'])
    sql['having'] = rebuild_condition_val(sql['having'])
    sql['where'] = rebuild_condition_val(sql['where'])
    sql['intersect'] = rebuild_sql_val(sql['intersect'])
    sql['except'] = rebuild_sql_val(sql['except'])
    sql['union'] = rebuild_sql_val(sql['union'])

    return sql


# Rebuild SQL functions for foreign key evaluation
def build_valid_col_units(table_units, schema):
    col_ids = [table_unit[1] for table_unit in table_units if table_unit[0] == TABLE_TYPE['table_unit']]
    prefixs = [col_id[:-2] for col_id in col_ids]
    valid_col_units= []
    for value in schema.idMap.values():
        if '.' in value and value[:value.index('.')] in prefixs:
            valid_col_units.append(value)
    return valid_col_units


def rebuild_col_unit_col(valid_col_units, col_unit, kmap):
    if col_unit is None:
        return col_unit

    agg_id, col_id, distinct = col_unit
    if col_id in kmap and col_id in valid_col_units:
        col_id = kmap[col_id]
    if DISABLE_DISTINCT:
        distinct = None
    return agg_id, col_id, distinct


def rebuild_val_unit_col(valid_col_units, val_unit, kmap):
    if val_unit is None:
        return val_unit

    unit_op, col_unit1, col_unit2 = val_unit
    col_unit1 = rebuild_col_unit_col(valid_col_units, col_unit1, kmap)
    col_unit2 = rebuild_col_unit_col(valid_col_units, col_unit2, kmap)
    return unit_op, col_unit1, col_unit2


def rebuild_table_unit_col(valid_col_units, table_unit, kmap):
    if table_unit is None:
        return table_unit

    table_type, col_unit_or_sql = table_unit
    if isinstance(col_unit_or_sql, tuple):
        col_unit_or_sql = rebuild_col_unit_col(valid_col_units, col_unit_or_sql, kmap)
    return table_type, col_unit_or_sql


def rebuild_cond_unit_col(valid_col_units, cond_unit, kmap):
    if cond_unit is None:
        return cond_unit

    not_op, op_id, val_unit, val1, val2 = cond_unit
    val_unit = rebuild_val_unit_col(valid_col_units, val_unit, kmap)
    return not_op, op_id, val_unit, val1, val2


def rebuild_condition_col(valid_col_units, condition, kmap):
    for idx in range(len(condition)):
        if idx % 2 == 0:
            condition[idx] = rebuild_cond_unit_col(valid_col_units, condition[idx], kmap)
    return condition


def rebuild_select_col(valid_col_units, sel, kmap):
    if sel is None:
        return sel
    distinct, _list = sel
    new_list = []
    for it in _list:
        agg_id, val_unit = it
        new_list.append((agg_id, rebuild_val_unit_col(valid_col_units, val_unit, kmap)))
    if DISABLE_DISTINCT:
        distinct = None
    return distinct, new_list


def rebuild_from_col(valid_col_units, from_, kmap):
    if from_ is None:
        return from_

    from_['table_units'] = [rebuild_table_unit_col(valid_col_units, table_unit, kmap) for table_unit in from_['table_units']]
    from_['conds'] = rebuild_condition_col(valid_col_units, from_['conds'], kmap)
    return from_


def rebuild_group_by_col(valid_col_units, group_by, kmap):
    if group_by is None:
        return group_by

    return [rebuild_col_unit_col(valid_col_units, col_unit, kmap) for col_unit in group_by]


def rebuild_order_by_col(valid_col_units, order_by, kmap):
    if order_by is None or len(order_by) == 0:
        return order_by

    direction, val_units = order_by
    new_val_units = [rebuild_val_unit_col(valid_col_units, val_unit, kmap) for val_unit in val_units]
    return direction, new_val_units


def rebuild_sql_col(valid_col_units, sql, kmap):
    if sql is None:
        return sql

    sql['select'] = rebuild_select_col(valid_col_units, sql['select'], kmap)
    sql['from'] = rebuild_from_col(valid_col_units, sql['from'], kmap)
    sql['where'] = rebuild_condition_col(valid_col_units, sql['where'], kmap)
    sql['groupBy'] = rebuild_group_by_col(valid_col_units, sql['groupBy'], kmap)
    sql['orderBy'] = rebuild_order_by_col(valid_col_units, sql['orderBy'], kmap)
    sql['having'] = rebuild_condition_col(valid_col_units, sql['having'], kmap)
    sql['intersect'] = rebuild_sql_col(valid_col_units, sql['intersect'], kmap)
    sql['except'] = rebuild_sql_col(valid_col_units, sql['except'], kmap)
    sql['union'] = rebuild_sql_col(valid_col_units, sql['union'], kmap)

    return sql


def build_foreign_key_map(entry):
    cols_orig = entry["column_names_original"]
    tables_orig = entry["table_names_original"]

    # rebuild cols corresponding to idmap in Schema
    cols = []
    for col_orig in cols_orig:
        if col_orig[0] >= 0:
            t = tables_orig[col_orig[0]]
            c = col_orig[1]
            cols.append("__" + t.lower() + "." + c.lower() + "__")
        else:
            cols.append("__all__")

    def keyset_in_list(k1, k2, k_list):
        for k_set in k_list:
            if k1 in k_set or k2 in k_set:
                return k_set
        new_k_set = set()
        k_list.append(new_k_set)
        return new_k_set

    foreign_key_list = []
    foreign_keys = entry["foreign_keys"]
    for fkey in foreign_keys:
        key1, key2 = fkey
        key_set = keyset_in_list(key1, key2, foreign_key_list)
        key_set.add(key1)
        key_set.add(key2)

    foreign_key_map = {}
    for key_set in foreign_key_list:
        sorted_list = sorted(list(key_set))
        midx = sorted_list[0]
        for idx in sorted_list:
            foreign_key_map[cols[idx]] = cols[midx]

    return foreign_key_map


def build_foreign_key_map_from_json(table):
    with open(table) as f:
        data = json.load(f)
    tables = {}
    for entry in data:
        tables[entry['db_id']] = build_foreign_key_map(entry)
    return tables

# replace all aliases with the original table names
def temp_removeAlias(sql):
    sql0 = sql
    sql = sql.lower()
    # remove space around '.'
    sql = re.sub(' *\. *', '.', sql)

    g_p = Parser(sql0)  # get the parser

    # delete AS XXX
    temp_dict = g_p.tables_aliases
    # replace all aliases in the original SQL
    for key in temp_dict:
        temp_alias = key + '.'
        temp_table = temp_dict[key] + '.'
        sql = sql.replace(temp_alias, temp_table)
    # delete all 'AS xxx'
    temp_tokens = sql.split()
    idx = 0
    while True:
        if temp_tokens[idx].lower() == 'as' and idx != len(temp_tokens) - 1:
            del temp_tokens[idx + 1]
            del temp_tokens[idx]
            idx = -1
        idx += 1
        if idx == len(temp_tokens):
            break

    res = ' '.join(temp_tokens)
    return res

def temp_preprocess(str):
    str = str.replace(',', ' , ')
    str = str.replace('%', ' % ')
    str = str.replace('>', ' > ')
    str = str.replace('<', ' < ')
    str = str.replace('=', ' = ')
    str = str.replace('(', ' ( ')
    str = str.replace(')', ' ) ')
    str = str.replace('\'', ' \" ')
    quotes = re.findall(r'" *.*? *"', str)
    for qt in quotes:
        new_qt = qt.strip('"')
        new_qt = new_qt.strip()
        new_qt = '"' + new_qt + '"'
        str = str.replace(qt, new_qt)

    str = re.sub('> *=', '>=', str)
    str = re.sub('< *=', '<=', str)
    str = re.sub('! *=', '!=', str)
    str = re.sub(' +', ' ', str)  # replace multiple spaces to 1

    return str

# simply preprocess a sql to make sure their format are unified
def simplePreprocess(sql):
    sql = sql.lower()

    sql = re.sub('! +=', '!=', sql)
    sql = re.sub('< +=', '<=', sql)
    sql = re.sub('> +=', '>=', sql)
    sql = re.sub(' *= *', ' = ', sql)
    sql = re.sub(' *\. *', '.', sql)
    sql = re.sub(' *\( *', '(', sql)
    sql = re.sub(' *\) *', ') ', sql)
    sql = re.sub(' *, *', ' , ', sql)
    sql = sql.replace('\'', '')
    sql = sql.replace('\"', '')

    sql = re.sub(' +', ' ', sql)
    sql = sql.strip('; ')
    sql = sql.strip()
    return sql


# generate mapping from NL words to columns menu
# return a mapping dict
def get_DIY_mapping(NL, dbid, SQL):
    # hyper-parameter
    threshold = 66  # 0-100

    NL = NL.strip('.;?!')

    visited_word_list = [] # remove repetitve words

    # only keep the top K candidates
    K = 6

    # get NL tokens
    NL_tok_list = NL.split()

    SQL_tok_list = SQL.split()

    # get columns from dbid
    # TO-DO
    column_list = []

    table_list = os.listdir('../DBjson/' + dbid)
    table_list = [tb.split('.')[0] for tb in table_list]
    for tableid in table_list:
        file_name = '../DBjson/' + dbid + '/' + tableid + '.json'

        with open(file_name, 'r') as f:
            # the content of table (which is a dictionary list)
            print('open file')
            table_content = json.load(f)

            if len(table_content) > 0:
                temp_columns = list(table_content[0].keys())
            else:
                temp_columns = []

            temp_columns = [tableid + '.' + col for col in temp_columns]

            column_list += temp_columns

    mapping_list = []

    global_max = 0
    max_mapping = {}

    for word in NL_tok_list:
        if word in visited_word_list:
            continue
        visited_word_list.append(word)
        mapping_col = '' # the maximum with highest matching score (need to > threshold)
        max_score = 0 # maximum matching score of this word
        for col in SQL_tok_list:
            score = fuzz.ratio(word, col.split('.')[-1]) # current score
            if score > max_score:
                max_score = score
                mapping_col = col

        # store the global max one
        if max_score > global_max:
            temp_dict = {
                'key': word,
                'value': mapping_col,
                'score': max_score
            }
            max_mapping = copy.deepcopy(temp_dict)

        if max_score > threshold:
            temp_dict = {
                'key': word,
                'value': mapping_col,
                'score': max_score
            }
            mapping_list.append(copy.deepcopy(temp_dict))

    # sort the list based on the score (high to low)
    mapping_list = sorted(mapping_list, key=lambda dict: dict['score'])
    mapping_list.reverse() # from high to low

    # remove repetitive values
    temp_list = []
    visited_sql_tok_list = []
    i = 0
    while i < len(mapping_list):
        if mapping_list[i]['value'].lower() in visited_sql_tok_list:
            del mapping_list[i]
            i = 0
            continue
        else:
            temp_list.append(mapping_list[i])
            visited_sql_tok_list.append(mapping_list[i]['value'].lower())
            i += 1

    mapping_list = copy.deepcopy(temp_list)

    # only keep the top K candidates
    if len(mapping_list) > K:
        mapping_list = mapping_list[:5]


    # at least return the maximum score
    if len(mapping_list) == 0:
        mapping_list.append(max_mapping)

    return mapping_list

if __name__ == "__main__":

    etype = "exec"
    etype = "match"
    etype = "all"

    db_dir = '../dataset/original/spider/database'
    table = "../dataset/original/spider/tables.json"

    data_dir = "../dataset/structured/spider/dev.json"
    # data_dir = "../dataset/paraphrased/dev.json"

    gold_dir = 'gold.txt'
    pred_dir = 'pred.txt'
    question_dir = 'question.txt'

    pred_NL2SQL_dir = 'pred_NL2SQL.txt'

    assert etype in ["all", "exec", "match"], "Unknown evaluation method"

    simple_modification_cnt = 0 # for counting how many times the simple modification is triggered
    modification_num = 0

    total_running_time1 = 0
    total_running_time2 = 0

    kmaps = build_foreign_key_map_from_json(table)

    print("current directory")
    print(os.getcwd(), flush=True)  # print current work directory

    # user simulation for structured explanation
    # -------------- generate gold.txt & pred.txt for evaluation, the evaluate ----------------------------

    # open the output file
    f_question = open(question_dir, "w")  # for user simulation
    f_gold = open(gold_dir, "w")
    f_pred = open(pred_dir, "w") # for user simulation
    f_NL2SQL_pred = open(pred_NL2SQL_dir, "w") # for purely NL2SQL model

    exception_num = 0 # exception number

    with open(data_dir) as f:
        data = json.load(f)

    # convert the dataset format to user-simulation format
    # (group by spider instance)
    sim_data = []
    previous_sql = ''
    previous_question = ''
    continue_flag = False # used to indicate if jump this one
    data_piece = {}
    cnt = 0
    for idx, ex in enumerate(data):
        # judge if it is a singe select, jump
        # if ex['original_sql'].lower().count('select') != 1 or ' intersect ' in ex['original_sql'].lower() or ' union ' in ex['original_sql'].lower() or ' except ' in ex['original_sql'].lower():
        #     print(ex['original_sql'], flush=True)
        #     continue

        # if 'select country from singer where age > 40 intersect select country from singer where age < 30'.lower() in ex['original_sql'].lower():
        #     print('here')

        if 'Find the districts in which there are both shops selling less than 3000 products and shops selling more than 10000 products.'.lower() in ex['original_question'].lower():
            print('here')

        # judge if new instance is met
        # decided by both question and sql
        if ex['original_sql'] != previous_sql or ex['original_question'] != previous_question:
            cnt += 1
            # add the previous data piece
            sim_data.append(data_piece)
            # update the previous sql and question
            previous_sql = ex['original_sql']
            previous_question = ex['original_question']

            # decompose the sql by IEU
            subquery_list = splitByIEU(ex['original_sql'])

            # construct new data piece
            # based on the number of subqueries
            data_piece = {}
            data_piece['sql_list'] = []  # the subquery list
            data_piece['ins_id'] = cnt
            data_piece['db_id'] = ex['db_id']
            data_piece['original_sql'] = removeAlias(ex['original_sql'])
            data_piece['question'] = ex['original_question']

            for subquery in subquery_list:
                dp = {}
                dp['IEU'] = subquery['concatenate']
                dp['subquery'] = subquery['subquery']
                # define subexpression of gold
                dp['select'] = {'sub': '', 'exp': ''}
                dp['from'] = {'sub': '', 'exp': ''}
                dp['where'] = {'sub': '', 'exp': ''}
                dp['group'] = {'sub': '', 'exp': ''}
                dp['having'] = {'sub': '', 'exp': ''}
                dp['order'] = {'sub': '', 'exp': ''}

                data_piece['sql_list'].append(dp)

        # must ensure that the select subexpression is the most outside select, not the inner one
        temp_original = simplePreprocess(removeAlias(ex['original_sql']))
        temp_subexpression = simplePreprocess(ex['query'])

        if temp_subexpression.startswith('select ') and temp_subexpression not in temp_original:
            print(temp_original)
            print(temp_subexpression)
            raise Exception(temp_subexpression + '-------- not in ---------' + temp_original)

        # Fill subexpression along with its paraphrased explanation
        if ex['query'].lower().startswith('select ') and temp_original.startswith(temp_subexpression):
            for i in range(len(data_piece['sql_list'])):

                # decompose and judge if this query is not from the nested part
                temp_decompose_res = sql2nl(data_piece['sql_list'][i]['subquery'])
                discard_flag = True
                for temp_sub in temp_decompose_res[-1]['explanation']:
                    if temp_sub['subexpression'].lower().startswith('select '):
                        data_piece['sql_list'][i]['select']['sub'] = temp_sub['subexpression']
                        data_piece['sql_list'][i]['select']['exp'] = temp_sub['explanation']




                # data_piece['select']['exp'] = ex['template explanation']
        elif ex['query'].lower().startswith('from '):
            for i in range(len(data_piece['sql_list'])):

                # decompose and judge if this query is not from the nested part
                temp_decompose_res = sql2nl(data_piece['sql_list'][i]['subquery'])
                discard_flag = True

                for temp_sub in temp_decompose_res[-1]['explanation']:
                    if temp_sub['subexpression'].lower().startswith('from '):
                        pattern = re.compile('\( *select', re.IGNORECASE)
                        # don't replace the nested where
                        if not re.search(pattern, data_piece['sql_list'][i]['select']['sub']):
                            data_piece['sql_list'][i]['from']['sub'] = temp_sub['subexpression']
                            data_piece['sql_list'][i]['from']['exp'] = temp_sub['explanation']


                # data_piece['group']['exp'] = ex['template explanation']
        elif ex['query'].lower().startswith('where '):
            for i in range(len(data_piece['sql_list'])):

                # decompose and judge if this query is not from the nested part
                temp_decompose_res = sql2nl(data_piece['sql_list'][i]['subquery'])
                discard_flag = True
                for temp_sub in temp_decompose_res[-1]['explanation']:
                    if temp_sub['subexpression'].lower().startswith('where '):
                        pattern = re.compile('\( *select', re.IGNORECASE)
                        # don't replace the nested where
                        if not re.search(pattern, data_piece['sql_list'][i]['select']['sub']):
                            data_piece['sql_list'][i]['where']['sub'] = temp_sub['subexpression']
                            data_piece['sql_list'][i]['where']['exp'] = temp_sub['explanation']


                # data_piece['where']['exp'] = ex['template explanation']
        elif ex['query'].lower().startswith('group by '):
            for i in range(len(data_piece['sql_list'])):

                # decompose and judge if this query is not from the nested part
                temp_decompose_res = sql2nl(data_piece['sql_list'][i]['subquery'])
                discard_flag = True
                for temp_sub in temp_decompose_res[-1]['explanation']:
                    if temp_sub['subexpression'].lower().startswith('group by '):
                        pattern = re.compile('\( *select', re.IGNORECASE)
                        # don't replace the nested where
                        if not re.search(pattern, data_piece['sql_list'][i]['select']['sub']):
                            data_piece['sql_list'][i]['group']['sub'] = temp_sub['subexpression']
                            data_piece['sql_list'][i]['group']['exp'] = temp_sub['explanation']



                    # data_piece['group']['exp'] = ex['template explanation']
        elif ex['query'].lower().startswith('having '):
            for i in range(len(data_piece['sql_list'])):

                # decompose and judge if this query is not from the nested part
                temp_decompose_res = sql2nl(data_piece['sql_list'][i]['subquery'])
                discard_flag = True
                for temp_sub in temp_decompose_res[-1]['explanation']:
                    if temp_sub['subexpression'].lower().startswith('having '):
                        pattern = re.compile('\( *select', re.IGNORECASE)
                        # don't replace the nested where
                        if not re.search(pattern, data_piece['sql_list'][i]['select']['sub']):
                            data_piece['sql_list'][i]['having']['sub'] = temp_sub['subexpression']
                            data_piece['sql_list'][i]['having']['exp'] = temp_sub['explanation']


                    # data_piece['group']['exp'] = ex['template explanation']
        elif ex['query'].lower().startswith('order by '):
            for i in range(len(data_piece['sql_list'])):

                # decompose and judge if this query is not from the nested part
                temp_decompose_res = sql2nl(data_piece['sql_list'][i]['subquery'])
                discard_flag = True
                for temp_sub in temp_decompose_res[-1]['explanation']:
                    if temp_sub['subexpression'].lower().startswith('order by '):
                        pattern = re.compile('\( *select', re.IGNORECASE)
                        # don't replace the nested where
                        if not re.search(pattern, data_piece['sql_list'][i]['select']['sub']):
                            data_piece['sql_list'][i]['order']['sub'] = temp_sub['subexpression']
                            data_piece['sql_list'][i]['order']['exp'] = temp_sub['explanation']
                            # data_piece['order']['exp'] = ex['template explanation']



    # finished preparing data for user simulation
    sim_data.append(data_piece) # push the last instance
    sim_data.pop(0) # pop the 1st empty data piece

    # start to do user simulation
    for idx, ex in enumerate(sim_data):

        # if idx < 159:
        #     # print('neglect')
        #     continue

        # if 'select accelerate from cars_data order by horsepower desc limit 1'.lower() in ex['original_sql'].lower():
        #     print('here')

        print('\n' + '=' * 20 + ' ' + str(idx) + ' ' + '=' * 20)
        print('DBid:', ex['db_id'])

        gold_sql_no_alias = removeAlias(ex['original_sql'])

        # if gold_sql_no_alias == 'select count ( * ) from concert where year = 2014 or year = 2015':
        #     print('here')

        # print gold subexpressions
        print('gold SQL\n' + ex['original_sql'])
        print('gold SQL no alias\n' + gold_sql_no_alias)

        for k in range(len(ex['sql_list'])):
            print('\n' + str(k+1) + 'th subexpressions of gold SQL\n')
            print('select: ', ex['sql_list'][k]['select']['sub'])
            print('from: ', ex['sql_list'][k]['from']['sub'])
            print('where: ', ex['sql_list'][k]['where']['sub'])
            print('group: ', ex['sql_list'][k]['group']['sub'])
            print('having: ', ex['sql_list'][k]['having']['sub'])
            print('order: ', ex['sql_list'][k]['order']['sub'])


        # generate the predicted SQL using a NL2SQL model

        # SMBOP
        NL2SQL_pred_sql = inference(ex['question'], ex['db_id'])

        # # EditSQL
        # os.chdir("MISP_mine")
        # try:
        #     NL2SQL_pred_sql = interaction_editsql.getSQL(ex['question'], ex['db_id'])
        # except Exception as e:
        #     NL2SQL_pred_sql = ''
        # os.chdir("..")

        print('\npredicted SQL (one-shot)\n' + NL2SQL_pred_sql)

        # declare the subexpressions of the predicted SQL
        pred_subquery_list = splitByIEU(ex['original_sql'])
        pred_content_list = []  # the decomposed contents of the predicted sql

        for subquery_idx in range(len(pred_subquery_list)):
            content = {
                'select': '',
                'from': '',
                'where': '',
                'group': '',
                'having': '',
                'order': '',
                'IEU': '',
                'exp': {
                    'select': '',
                    'from': '',
                    'where': '',
                    'group': '',
                    'having': '',
                    'order': '',
                }
            }

            # decompose pred_sql
            try:
                pred_subquery = removeAlias(pred_subquery_list[subquery_idx]['subquery'])  # remove aliases in the generated sql
                decomposed_content = sql2nl(pred_subquery)
                print(pred_subquery_list[subquery_idx]['concatenate'])

            except Exception as e:
                exception_num += 1
                decomposed_content = [{'explanation': []}]

            # temp_str = pred_subquery.lower().replace(' ', '')
            # if '(select' in temp_str:
            #     print('here')

            # the NL2SQL model may make a SQL composition, which means it is wrong, it doesn't, just use the first subquery by default

            content['IEU'] = pred_subquery_list[subquery_idx]['concatenate']
            for ct in decomposed_content[-1]['explanation']:
                if ct['subexpression'].lower().startswith('select '):
                    content['select'] = ct['subexpression']
                    content['exp']['select'] = ct['explanation']
                if ct['subexpression'].lower().startswith('from '):
                    content['from'] = ct['subexpression']
                    content['exp']['from'] = ct['explanation']
                elif ct['subexpression'].lower().startswith('where '):
                    content['where'] = ct['subexpression']
                    content['exp']['where'] = ct['explanation']
                elif ct['subexpression'].lower().startswith('group by '):
                    content['group'] = ct['subexpression']
                    content['exp']['group'] = ct['explanation']
                elif ct['subexpression'].lower().startswith('having '):
                    content['having'] = ct['subexpression']
                    content['exp']['having'] = ct['explanation']
                elif ct['subexpression'].lower().startswith('order by '):
                    content['order'] = ct['subexpression']
                    content['exp']['order'] = ct['explanation']

            pred_content_list.append(content)


        # compare subexpressions of the predicted SQL with subexpressions of gold SQL, one by one
        # can handle the nested and IEU situation
        # compare if equivalent using match score
        print('\nModification:\n')
        threshold = 1  # a threshold, if less than this score, then the simulated user will decide to regenerate this subexpression


        # adjust the IEU structure

        # remove extra predicted subqueries
        if len(pred_content_list) > len(ex['sql_list']):
            pred_content_list = pred_content_list[:len(ex['sql_list'])]
        # add extra contents
        elif len(pred_content_list) < len(ex['sql_list']):
            for temp_i in range(len(pred_content_list), len(ex['sql_list'])):
                content = {'select': '', 'from': '', 'where': '', 'group': '', 'having': '', 'order': '',
                            'IEU': ex['sql_list'][temp_i],
                            'exp': {
                                'select': '',
                                'from': '',
                                'where': '',
                                'group': '',
                                'having': '',
                                'order': '',
                            }
                            }
                pred_content_list.append(content)

        # adjust IEU
        # assume users can figure out the IEU relationship
        for temp_i in range(len(pred_content_list)):
            pred_content_list[temp_i]['IEU'] = ex['sql_list'][temp_i]['IEU']

        clause_category_list = ['select', 'from', 'where', 'group', 'having', 'order']
        for clause_category in clause_category_list:

            # if 'What are the African countries that have a'.lower() in ex['question'].lower():
            #     print('here')

            for pred_ct_idx in range(len(pred_content_list)):
                if matchScore(ex['sql_list'][pred_ct_idx][clause_category]['sub'], pred_content_list[pred_ct_idx][clause_category]) < threshold:
                    modification_num += 1

                    # for nested SQL simulation
                    temp_gt_sub = ex['sql_list'][pred_ct_idx][clause_category]['sub'].lower()
                    temp_gt_sub = re.sub('\( *select', '( select', temp_gt_sub)
                    temp_gt_sub = re.sub('> *\(', '> (', temp_gt_sub)
                    temp_gt_sub = re.sub('< *\(', '< (', temp_gt_sub)
                    temp_gt_sub = re.sub('in *\(', 'in (', temp_gt_sub)


                    # ablation study for simple rules
                    start_time = time.time()
                    simple_mod_res = simpleModification(pred_content_list[pred_ct_idx]['exp'][clause_category],
                                                        ex['sql_list'][pred_ct_idx][clause_category]['exp'],
                                                        pred_content_list[pred_ct_idx][clause_category])
                    end_time = time.time()
                    time_diff = start_time - end_time

                    ############ hybrid ##############
                    # if simple modification return false, use the model
                    if simple_mod_res:
                        simple_modification_cnt += 1
                        pred_subexpression = simple_mod_res
                        total_running_time1 += time_diff

                        # test time of model inference
                        start_time = time.time()
                        _xxx = run_structure.inference_structure(
                            ex['sql_list'][pred_ct_idx][clause_category]['exp'], ex['db_id'])
                        end_time = time.time()
                        time_diff = start_time - end_time
                        total_running_time2 += time_diff

                    else:
                        pred_subexpression = run_structure.inference_structure(
                            ex['sql_list'][pred_ct_idx][clause_category]['exp'], ex['db_id'])



                    ############ text-to-clause ##############

                    # pred_subexpression = run_structure.inference_structure(
                    #     ex['sql_list'][pred_ct_idx][clause_category]['exp'], ex['db_id'])



                    # ############ direct transformation ##############
                    # pred_subexpression = '' # cannot detect atomic edit in the paraphrased explanation



                    if clause_category == 'where':
                        if '( select' in temp_gt_sub or '< (' in temp_gt_sub or '> (' in temp_gt_sub or 'in (' in temp_gt_sub.lower():
                            pred_subexpression = ex['sql_list'][pred_ct_idx][clause_category]['sub']



                    pred_subexpression = addQuotes(pred_subexpression)  # add quotes to specific names



                    # remove generated subexpression with wrong types
                    # if not pred_subexpression.lower().startswith(clause_category.lower() + ' '):
                    #     pred_subexpression = ''


                    print('\nGround truth subexpression: ' + ex['sql_list'][pred_ct_idx][clause_category]['sub'])
                    print(pred_content_list[pred_ct_idx][clause_category] + '  -------------------------->  ' + pred_subexpression)
                    pred_content_list[pred_ct_idx][clause_category] = pred_subexpression # update the corresponding subexpression



        final_sql = ''
        # add the first SQL

        for query_idx in range(len(pred_content_list)):
            # nested
            if pred_content_list[query_idx]['IEU'] == 'nested':
                pass
            # IEU
            elif pred_content_list[query_idx]['IEU']:
                if query_idx == 0:
                    raise Exception('should be no IEU in 0')
                final_sql += ' ' + pred_content_list[query_idx]['IEU']
            elif query_idx != 0:
                raise Exception('no IEU')


            for clause_category in clause_category_list:
                if pred_content_list[query_idx][clause_category]:
                    final_sql += ' ' + pred_content_list[query_idx][clause_category]



        final_sql = final_sql.strip()

        # if matchScore(ex['select']['sub'], content['select']) < threshold:
        #     pred_subexpression = run_structure.inference_structure(ex['select']['exp'], ex['db_id'])
        #     pred_subexpression = addQuotes(pred_subexpression) # add quotes to specific names
        #     # pred_subexpression = col_in_table_check(pred_subexpression, ex['db_id']) # remove incorrect table name
        #     print(content['select'] + '  -------------------------->  ' + pred_subexpression)
        #     content['select'] = pred_subexpression
        # if matchScore(ex['where']['sub'], content['where']) < threshold:
        #     pred_subexpression = run_structure.inference_structure(ex['where']['exp'], ex['db_id'])
        #     pred_subexpression = addQuotes(pred_subexpression)  # add quotes to specific names
        #     # pred_subexpression = col_in_table_check(pred_subexpression, ex['db_id'])  # remove incorrect table name
        #     print(content['where'] + '  -------------------------->  ' + pred_subexpression)
        #     content['where'] = pred_subexpression
        # if matchScore(ex['group']['sub'], content['group']) < threshold:
        #     pred_subexpression = run_structure.inference_structure(ex['group']['exp'], ex['db_id'])
        #     pred_subexpression = addQuotes(pred_subexpression)  # add quotes to specific names
        #     # pred_subexpression = col_in_table_check(pred_subexpression, ex['db_id'])  # remove incorrect table name
        #     print(content['group'] + '  -------------------------->  ' + pred_subexpression)
        #     content['group'] = pred_subexpression
        # if matchScore(ex['order']['sub'], content['order']) < threshold:
        #     pred_subexpression = run_structure.inference_structure(ex['order']['exp'], ex['db_id'])
        #     pred_subexpression = addQuotes(pred_subexpression)  # add quotes to specific names
        #     # pred_subexpression = col_in_table_check(pred_subexpression, ex['db_id'])  # remove incorrect table name
        #     print(content['order'] + '  -------------------------->  ' + pred_subexpression)
        #     content['order'] = pred_subexpression

        # construct subexpression list for composition
        # sub_list = []
        # if content['select'] and content['select'].lower().startswith('select '):
        #     sub_list.append(content['select'])
        # if content['where'] and content['where'].lower().startswith('where '):
        #     sub_list.append(content['where'])
        # if content['group'] and content['group'].lower().startswith('group '):
        #     sub_list.append(content['group'])
        # if content['order'] and content['order'].lower().startswith('order '):
        #     sub_list.append(content['order'])


        # compose subexpressions to new sql
        # regenerated_pred_sql = composeSQL(sub_list, ex['db_id'])

        # regenerated_pred_sql = ' '.join(sub_list)

        # output gold sql and user-simulated interactive sql to files
        f_NL2SQL_pred.write(NL2SQL_pred_sql + '\n')
        f_pred.write(final_sql + '\n')
        f_gold.write(gold_sql_no_alias + '\t' + ex['db_id'] + '\n')
        f_question.write(ex['question'] + '\n')

    f_NL2SQL_pred.close()
    f_gold.close()
    f_pred.close()
    f_question.close()

    print("number of exceptions:", exception_num)
    print("number of simple modification:", simple_modification_cnt)
    print("number of total modification:", modification_num)
    print("time of atomic modification:", total_running_time1)
    print("time of model inference:", total_running_time2)

    ############################# Evaluation #############################
    
    print('Without interaction')
    print('-'*50)
    evaluate(gold_dir, pred_NL2SQL_dir, db_dir, etype, kmaps) # one-shot
    print('\n\n')
    
    print('With interaction')
    print('-'*50)
    evaluate(gold_dir, pred_dir, db_dir, etype, kmaps) # interaction
    
