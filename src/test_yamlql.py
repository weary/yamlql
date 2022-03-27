
import pytest
import yaml
from .yamlql import getql_many, getql_one

TESTLABELSETS = [
    {'label0', 'label1', 'label2'},
    {'flag0', 'flag1', 'flag2'},
    {'green', 'red', 'blue'},
]
testdata = """
assets:
- name: asset 1 long name
  alias: asset1
  classification[label1,flag1]: ~classifications.friendly
  classification[label1,flag0]: ~classifications.otherclass
  classification[label2]: ~classifications.hostile
- name: asset 2 long name
  alias: asset2
  classification: ~classifications.hostile
"""

testdata2 = """
classifications:
- name: Friendly Stuff
  alias: friendly
  greeting: Hello from friendly!
- name: Hostile Attack
  alias: hostile
  greeting: Hello from hostile!
- alias: otherclass
"""

"""
assets.any.classification
"""


def get_testmodel() -> dict:
    model = yaml.safe_load(testdata)
    model.update(yaml.safe_load(testdata2))
    return model


def test_simple():
    qry = "classifications.hostile.greeting"
    model = get_testmodel()

    out = getql_one(qry, model, alllabels=TESTLABELSETS, neededlabels={})
    assert out == "Hello from hostile!"


def test_lots1():
    qry = "assets.asset 1 long name.classification.greeting"
    labels = {'label1', 'flag1'}
    model = get_testmodel()

    out = getql_one(qry, model, alllabels=TESTLABELSETS, neededlabels=labels)
    assert out == "Hello from friendly!"


def test_lots2():
    qry = "assets.asset 1 long name.classification[label2].greeting"
    model = get_testmodel()

    out = getql_one(qry, model, alllabels=TESTLABELSETS)
    assert out == "Hello from hostile!"


def test_iter1():
    qry = "assets.any.classification.alias"
    model = get_testmodel()

    out = getql_many(qry, model, alllabels=TESTLABELSETS)
    assert set(out) == {"friendly", "hostile", "otherclass"}


def test_iter2():
    model = get_testmodel()

    qry1 = "assets.any[flag1].classification.alias"
    out1 = getql_many(qry1, model, alllabels=TESTLABELSETS)
    assert set(out1) == {"hostile", "friendly"}

    qry2 = "assets.any[label2].classification.alias"
    out2 = getql_many(qry2, model, alllabels=TESTLABELSETS)
    assert set(out2) == {"hostile"}

    qry3 = "assets.any[flag0].classification.alias"
    out3 = getql_many(qry3, model, alllabels=TESTLABELSETS)
    assert set(out3) == {"otherclass", "hostile"}


def test_iter3():
    qry = "assets[flag1].any.classification.alias"
    model = get_testmodel()

    out = getql_many(qry, model, alllabels=TESTLABELSETS)
    assert set(out) == {"hostile", "friendly"}
