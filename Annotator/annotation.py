import os

def EventColor(evt):
    dict_event = {
        'Sinus Rhythm':     (0, 1, 0),
        'AF':               (1, 0.6, 0.6),
        'SVT':              (0.6, 0.2, 0.6),
        'VT':               (0.6, 0, 0.2),
        'VF':               (1, 0, 0),
        'SHOCK':            (0, 0, 0),
        'NOISE':            (0.6, 0.6, 0.6),
    }
    dict_text = {
        'SHOCK':            (1, 0, 0),
        'SVT':              (1, 1, 1),
    }
    ec =  dict_event[evt] if evt in dict_event else (0,0,0)
    if evt in dict_text:
        et =  dict_text[evt]
    elif evt in dict_event:
        et=(0,0,0)
    else:
        et=(1,1,0)
    return ec, et

def save_Annot(file, cardiac_Events):
        with open(file, 'w') as f:
            for item in cardiac_Events:
                f.write("%.1f\t%s\n" % (item[0], item[1]))

def load_Annot(file):
    if not os.path.exists(file):
        return [[0, 'Sinus Rhythm']]
        # raise NameError('Annotation to load does not exist.')
        
    with open(file, "r") as f:
        cardiac_Events=[]
        contents = f.readlines()
        for text in contents:
            data = text.split('\n')
            data = data[0]
            data = data.split('\t')
            cardiac_Events.append([float(data[0]), data[1]])
    return cardiac_Events