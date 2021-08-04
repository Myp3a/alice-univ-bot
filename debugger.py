import json

def dbg(var,varname=None,compact=False):
    if compact:
        if varname is None:
            varname = ""
        print(f'{varname} ({type(var)},{len(var)}): {var}')
    else:
        print('vvvvv')
        if varname is not None:
            print(varname)
        else:
            print('no name')
        print(f'type: {type(var)}')
        print(f'len: {len(var)}')
        try:
            var_json = json.dumps(var)
            print(json.dumps(var, indent=4, sort_keys=True))
        except:
            print(var)
        print('^^^^^')