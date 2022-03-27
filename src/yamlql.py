import re
from typing import Any, Iterator, List, Set, Tuple


def _split_field_labels(inp: str, can_have_remainder: bool) -> Tuple[str, Set[str], str]:
    m = re.match(r"^([\w ]+)(\[([\w, ]*)\])?([.](.*))?$", inp)
    if not m:
        raise Exception("Invalid ql expression", inp)
    field, _, labels, _, remainder = m.groups()
    if not can_have_remainder and remainder:
        raise Exception("Invalid entry", inp)
    if labels is not None:
        labels = set(l.strip() for l in labels.split(','))

    return (field, labels, remainder)


class YamlQuery(object):
    def __init__(self, model, alllabels: List[Set[str]], entrynamefields):
        self.model = model
        self.alllabels = alllabels
        self.entrynamefields = entrynamefields

        if self.alllabels:
            # check all labels are unique
            flattened = set(
                val for sublist in self.alllabels for val in sublist)
            if not len(flattened) == sum(len(s) for s in self.alllabels):
                raise Exception(
                    "Duplicate labels in different categories is not supported")

    def getql(self, expr: str, currentmodel: Iterator, neededlabels: Set = None) -> Iterator:
        exprfield, exprlabels, exprrem = _split_field_labels(
            expr, can_have_remainder=True)
        if exprlabels is not None:
            if neededlabels is None:
                neededlabels = set(exprlabels)
            else:
                neededlabels.update(exprlabels)

        def entry_has_name(entry, searchvalue):
            # helper function that returns true if any of the fields mentioned in entrynamefields matches the given value
            for namefield in self.entrynamefields:
                if entry.get(namefield) == searchvalue:
                    return True
            return False

        def resolve_model_references(model):
            if isinstance(model, str) and model.startswith('~'):
                model = self.getql(model[1:], self.model, neededlabels)
            return model

        def yield_model(model):
            model = resolve_model_references(model)
            if exprrem:  # more to do, or all of the expression done?
                yield from self.getql(exprrem, model, neededlabels)
            else:
                yield model

        def get_labelcategory_for_label(label: str) -> Set[str]:
            if not self.alllabels:
                raise Exception(
                    f"No labelcategories specified, invalid label '{label}'")
            for labelcategory in self.alllabels:
                if label in labelcategory:
                    return labelcategory
            raise Exception(f"Label '{label}' not found in any labelcategory")

        def check_labels(searchlabels, datalabels) -> bool:
            if not searchlabels or not datalabels:
                return True
            for searchlabel in searchlabels:
                cat = get_labelcategory_for_label(searchlabel)
                datalabels_from_cat = set(l for l in datalabels if l in cat)
                if not datalabels_from_cat:
                    continue  # nothing specified -> good
                searchlabels_from_cat = set(
                    l for l in searchlabels if l in cat)
                # all searchlabels from this category must be in the datalabels
                if not all(s in datalabels_from_cat for s in searchlabels_from_cat):
                    return False
            return True

        if isinstance(currentmodel, dict):
            for key, model in currentmodel.items():
                keyfield, keylabels, _ = _split_field_labels(
                    key, can_have_remainder=False)
                if 'any' != exprfield and keyfield != exprfield:
                    continue

                if not check_labels(neededlabels, keylabels):
                    continue

                yield from yield_model(model)
        elif isinstance(currentmodel, list):
            for model in currentmodel:
                if 'any' != exprfield and not entry_has_name(model, exprfield):
                    continue
                yield from yield_model(model)
        elif isinstance(currentmodel, Iterator):
            for model in currentmodel:
                yield from self.getql(expr, model, neededlabels)
        else:
            raise Exception(
                f"Cannot query into {type(currentmodel)}", currentmodel, expr)


def getql_many(expr: str, model, alllabels: List[Set[str]], entrynamefields: List[str] = ['name', 'alias'],
               neededlabels: Set = None) -> Iterator:
    """
    expr : a dot-separated list of entries to follow in the model.
    model : a dict or list,
    alllabels : a list of mutually-exclusive labelsets. If a label of one
      entryset is added to the search-query, all other labels in that
      labelset are forbidden
    entrynamefields : all record-fields that are considered a name, ie, all fields that are used to resolve expr.
    neededlabels : set of labels (at most one from every row in alllabels) that must be present.

    expr is of the form:
        expr = fullentry ('.' fullentry?) 
        entry = <word> | 'any'
        labellist = '[' word (',' word)* + ']'
        fullentry = entry labellist?

    label example:
    if alllabels is [{'red','green','blue'}, {'tall','short'}]
    then my dataset can use exactly one color and one size to restrict an entry. For example:
    houseprices:
    - name: House available in many colors and sizes
      price[red,tall] = 100
      price[red,short] = 200
      price[green] = 300
    for this dataset a query for:
        houseprices.price - will return all three prices
        houseprices[red].price - will return two prices
        houseprices[red].price[tall] - will return one price
    So, an unspecified labelcategory in the dataset means the value is for all labels in that category.
    An unspecified labelcategory in the search query means that it matches all labels in that category.
    """
    q = YamlQuery(model, alllabels, entrynamefields)
    yield from q.getql(expr, model, neededlabels)


def getql_one(expr: str, model, alllabels: List[Set[str]], entrynamefields: List[str] = ['name', 'alias'],
              neededlabels: Set = None) -> Any:
    out = list(getql_many(expr, model, alllabels,
               entrynamefields, neededlabels))
    if not out:
        raise Exception("Expression did not yield any result")
    if len(out) != 1:
        raise Exception("Expression yielded more than one result")
    return out[0]
