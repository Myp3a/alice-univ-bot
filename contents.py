class Text:
    def __init__(self,text,bold=False,italic=False):
        self.content = text
        self.bold = bold
        self.italic = italic


class MultilineText:
    def __init__(self,*args):
        self.lines = []
        for elem in args:
            self.lines.append(elem)
    
    def add_line(self,line):
        self.lines.append(line)


class Table:
    def __init__(self):
        self.cols = {}
        self.header = None

    @property
    def rows(self):
        rows = []
        for rowid in range(len(list(self.cols.values())[0])):
            row = []
            for colid in self.cols:
                row.append(self.cols[colid][rowid])
            rows.append(row)
        return rows

    def set_header(self,header):
        self.header = header
        if self.header == "":
            self.header = None

    def set_cols(self,cols):
        self.cols = {}
        for elem in cols:
            self.cols[elem] = []
        
    def add_row(self,row):
        for elem in row:
            self.cols[elem].append(row[elem])
    
    def max_len(self,col):
        length = 0
        for elem in self.cols[col]:
            if len(elem) > length:
                length = len(elem)
        return length

class Button:
    def __init__(self,text,callback):
        self.text = text
        self.callback = callback