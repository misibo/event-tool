def dict_expand(dict):

    def recursion(dict, keys, value):
        key = keys.pop(0)
        if key not in dict:
            dict[key] = {}
        if len(keys) >= 1:
            dict[key] = recursion(dict[key], keys, value)
        else:
            dict[key] = value
        return dict

    res = {}

    for key, value in dict.items():
        keys = key.split('.')
        res = recursion(res, keys, value)

    return res


def dict_flatten(d, path=''):
    res = {}
    for key, value in d.items():
        if type(value) is dict:
            res = {**res, **dict_flatten(value, f'{path}{key}.')}
        else:
            res[path+key] = value
    return res


d = {
    'sort.name.test.hello': 'one',
    'sort.title.test.hello': 'tree',
    'sort.name.test.ciau': 'two',
    'sort.title.bratte.hello': 'four'
    }

res1 = dict_expand(d)
res2 = dict_flatten(res1)

print('end')
