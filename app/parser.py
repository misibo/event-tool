import re


LIST_START_1 = '* '
LIST_START_2 = '- '


def extract_paragraphs(text):
    lines = [''] + [x.strip() for x in text.split('\n')]

    paragraph = ''
    for line in lines:
        if line == '':
            if paragraph != '':
                yield paragraph  # finish existing paragraph
            paragraph = ''
        else:
            if line.startswith(LIST_START_1) or line.startswith(LIST_START_2):
                if paragraph != '':
                    yield paragraph  # finish existing paragraph
                paragraph = line  # start a list item
            else:
                if paragraph == '':
                    # start new paragraph
                    paragraph = line
                else:
                    # extend existing paragraph
                    paragraph = paragraph + ' ' + line
    
    if paragraph != '':
        yield paragraph


class FormattedText:
    def __init__(self, text, mode):
        self.text = text
        self.mode = mode
    
    def __str__(self):
        return f'{self.mode.upper()}[{self.text}]'
    
    def __repr__(self):
        return f'{self.mode.upper()}[{self.text}]'


automaton = {
    'normal': {
        '*': 'bold',
        '_': 'italic',
        '`': 'monospace',
    },
    'bold': {
        '*': 'normal',
        '_': 'normal',
        '`': 'normal',
    },
    'italic': {
        '*': 'normal',
        '_': 'normal',
        '`': 'normal',
    },
    'monospace': {
        '*': 'normal',
        '_': 'normal',
        '`': 'normal',
    },
}

tokenizer = re.compile(r'(\*)|(\_)|(`)')


def parse_formatting(text):
    remaining = text
    parts = []
    mode = 'normal'
    while True:
        m = tokenizer.search(remaining)
        if m:
            text = remaining[:m.start()]
            if text != '':
                parts.append(FormattedText(text, mode))
            # print(f'{mode.upper()}: |{text}|')
            mode = automaton[mode][remaining[m.start():m.end()]]
            remaining = remaining[m.end():]
        else:
            text = remaining
            if text != '':
                parts.append(FormattedText(text, mode))
            # print(f'{mode.upper()}: |{text}|')
            break
    return parts


class SimpleParagraph:
    def __init__(self, parts):
        self.type = 'simple'
        self.parts = parts
    
    def __str__(self):
        return ''.join(str(x) for x in self.parts)

    def __repr__(self):
        return str(self)


class ListParagraph:
    def __init__(self):
        self.type = 'list'
        self.items = []
    
    def __str__(self):
        return 'LIST: ' + ', '.join([str(x) for x in self.items])
    
    def __repr__(self):
        return str(self)


def parse_text(text):
    lines = extract_paragraphs(text)

    par = None
    pars = []
    for line in lines:
        if line.startswith(LIST_START_1) or line.startswith(LIST_START_2):
            if line.startswith(LIST_START_1):
                tail = line[len(LIST_START_1):]
            else:
                tail = line[len(LIST_START_2):]

            # List
            body = SimpleParagraph(parse_formatting(tail.strip()))

            if type(par) is not ListParagraph:
                if par:
                    pars.append(par)
                par = ListParagraph()
            par.items.append(body)
        else:
            if par:
                pars.append(par)

            par = SimpleParagraph(parse_formatting(line.strip()))
    
    if par:
        pars.append(par)
    
    return pars


if __name__ == '__main__':
    text = "*bold* _italic_ `monospace` normal"

    for par in parse_text(text):
        print(par)
