from collections import defaultdict


class WiktionaryTags(object):
    def __init__(self):
        self.iso2lang = {}
        self.lang2iso = {}
        self.POS = set()
        self.save_ety_tags = {'bor': 'bor',
                              'borrowed': 'bor',
                              'learned borrowing': 'bor',
                              'calque': 'cal',
                              'inherited': 'inh',
                              'inh': 'inh',
                              'derived': 'der',
                              'der': 'der',
                              'cognate': 'cog',
                              'cog': 'cog'
                              }
        self.skip_ety_tags = {'mention', 'm', 'link', 'l', 'noncognate', 'noncog', 'ncog', 'doublet', 'sense', 's', 'w',
                              'confix', 'suffix', 'affix', 'prefix', 'cite-book'}
        self.nonstandard2standard = defaultdict(str)
        self.nonstandard2standard['LL.'] = 'lat'
        self.nonstandard2standard['VL.'] = 'lat'
        self.nonstandard2standard['ML.'] = 'lat'
        self.nonstandard2standard['NL.'] = 'lat'
        self.nonstandard2standard['la-lat'] = 'lat'

        self.load_iso()
        self.load_pos()

    def load_iso(self):
        iso_fp = 'inputs/ISO Language Codes.csv'
        with open(iso_fp, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
            for line in lines[1:]:
                iso2, iso3, lang = line.split(',')
                if len(iso2):  # Use 2-letter code if available, else use 3-letter code
                    self.iso2lang[iso2] = lang
                else:
                    self.iso2lang[iso3] = lang
                self.lang2iso[lang] = iso3

    def load_pos(self):
        pos_fp = 'inputs/parts_of_speech.txt'
        with open(pos_fp, 'r', encoding='utf-8') as f:
            for line in f:
                self.POS.add(line.strip())
