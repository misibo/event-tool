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
        self.type = 'text'
        self.text = text
        self.mode = mode

    def __str__(self):
        return f'<{self.mode.upper()}>{self.text}</{self.mode.upper()}>'
    
    def __repr__(self):
        return str(self)


class HyperLink:
    def __init__(self, url, richtext):
        self.type = 'link'
        self.url = url
        self.richtext = richtext
    
    def __str__(self):
        return f'<A href="{self.url}">{"".join(str(x) for x in self.richtext)}</A>'
    
    def __repr__(self):
        return str(self)


automaton = {
    'normal': {
        '*': 'bold',
        '_': 'italic',
        '`': 'monospace',
    },
    'bold': {
        '*': 'normal',
        '_': 'bold',
        '`': 'bold',
    },
    'italic': {
        '*': 'italic',
        '_': 'normal',
        '`': 'italic',
    },
    'monospace': {
        '*': 'monospace',
        '_': 'monospace',
        '`': 'normal',
    },
}

inline_format_pattern = re.compile(r'(\*)|(\_)|(`)')
hyperlink_pattern = re.compile(r'(\[(?P<label>.+)\]\((?P<url>.+)\))|(<(?P<plain_url>.+)>)')


def parse_inline_formatting(text, mode='normal'):
    remaining = text
    richtext = []
    while len(remaining) > 0:
        # Scan text for inline format tokens such as *, _, `
        m = inline_format_pattern.search(remaining)
        if m:
            block = remaining[:m.start()]
            if block != '':
                richtext.append(FormattedText(block, mode))
            # print(f'{mode.upper()}: |{block}|')
            mode = automaton[mode][remaining[m.start():m.end()]]
            remaining = remaining[m.end():]
        else:
            block = remaining
            if block != '':
                richtext.append(FormattedText(block, mode))
            # print(f'{mode.upper()}: |{block}|')
            remaining = ''
    return mode, richtext


def parse_simple_paragraph(text, url=True):
    remaining = text
    richtext = []
    mode = 'normal'
    while len(remaining) > 0:
        # Scan text for hyper-links
        m = hyperlink_pattern.search(remaining)
        if m:
            block = remaining[:m.start()]
            if block != '':
                mode, x = parse_inline_formatting(block, mode=mode)
                richtext += x
            groups = m.groupdict()
            if groups['plain_url']:  # variant: <www.google.ch>
                richtext.append(HyperLink(
                    url=groups['plain_url'].strip(),
                    richtext=[FormattedText(text=groups['plain_url'].strip(), mode=mode)],
                ))
            else:  # variant: [See google](www.google.ch)
                mode, x = parse_inline_formatting(groups['label'], mode=mode)
                richtext.append(HyperLink(
                    url=groups['url'].strip(),
                    richtext=x,
                ))
            remaining = remaining[m.end():]
        else:
            block = remaining
            if block != '':
                mode, x = parse_inline_formatting(block, mode=mode)
                richtext += x
            remaining = ''
    return richtext


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
            body = SimpleParagraph(parse_simple_paragraph(tail.strip()))

            if type(par) is not ListParagraph:
                if par:
                    pars.append(par)
                par = ListParagraph()
            par.items.append(body)
        else:
            if par:
                pars.append(par)

            par = SimpleParagraph(parse_simple_paragraph(line.strip()))
    
    if par:
        pars.append(par)
    
    return pars


if __name__ == '__main__':
    print(parse_simple_paragraph(
        'For some *references [see *_google_*](www.google.ch). Some <www.youtube.com> more* text'))
    print(parse_simple_paragraph("*bold* _italic_ `mon*osp*ace`"))

    # text = "*bold* _italic_ [My `monospace` link](www.google.ch) blabla"

    # for par in parse_text(text):
    #     print(par)
