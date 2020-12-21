import copy
import re
import unicodedata as ud
from enum import Enum
from WiktionaryTags import WiktionaryTags


# State: Is the parser reading an etymology or a pronunciation entry? 0 if no, 1 if etymology, 2 if pronunciation
class State(Enum):
    OTHER = 0
    ETYM = 1
    PRONOUNCE = 2


# Stores a single entry for the etymology dictionary
class WiktionaryEntry(object):
    __slots__ = ('word', 'raw_text', 'iso_code', 'pos', 'ipa', 'root_lang', 'nonstandard_root_code', 'root_word',
                 'root_roman', 'root_ipa', 'derivation', 'etym_number', 'universal_pronunciation', 'other_entries',
                 'headers', 'TAGS', 'latin_letters')

    def __init__(self, word, raw_text):
        self.word = self.process_word(word)
        self.raw_text = raw_text
        self.iso_code = ''
        self.pos = []
        self.ipa = ''
        self.root_lang = ''
        self.nonstandard_root_code = ''
        self.root_word = []
        self.root_roman = ''
        self.root_ipa = ''
        self.derivation = ''
        self.etym_number = 0
        self.universal_pronunciation = False

        self.other_entries = []  # Stores other etymologies for the same entry

        self.headers = []  # To help with debugging

        self.TAGS = WiktionaryTags()
        self.latin_letters = {}  # To ensure that romanizations are in Latin letters

        self.parse()

    def reinitialize(self, reinit_pos=True):
        if reinit_pos:
            self.pos = []
        if not self.universal_pronunciation:
            self.ipa = ''
        self.root_lang = ''
        self.nonstandard_root_code = ''
        self.root_word = []
        self.root_roman = ''
        self.root_ipa = ''
        self.derivation = ''

    # Denote reconstructions with *
    @staticmethod
    def process_word(word):
        processed = re.sub('^Reconstruction:[\w ]+/', '*', word)
        return processed

    def process_src_word_var(self, word):
        if type(word) is list:
            word = self.combine_last_elements(word)
        return word

    @staticmethod
    def split_key(line):
        for i, char in enumerate(line):
            if char == '=':
                return [line[:i], line[i+1:]]
            elif not char.isalpha():
                break
        return ['', line]

    @staticmethod
    def separate_pipes(line):
        sections = []

        start_idx = 0
        depth = 0
        i = 0
        while i + 1 < len(line):
            char = line[i]
            next_char = line[i+1]
            if char == '{' and next_char == '{':
                depth += 1
                i += 1
            elif char == '}' and next_char == '}':
                depth -= 1
                i += 1
            elif char == '|' and depth == 0:
                sections.append(line[start_idx:i])
                start_idx = i + 1

            i += 1

        sections.append(line[start_idx:])
        return sections

    @staticmethod
    def get_curly_braces(line):
        sections = []

        compound_flag = False
        paren_flag = False
        start_idx = None
        depth = 0
        i = 0
        while i + 1 < len(line):
            char = line[i]
            next_char = line[i+1]
            if char == '(':
                paren_flag = True
            elif paren_flag:
                if char == ')':
                    paren_flag = False
            elif char == '{' and next_char == '{':
                if depth == 0:
                    start_idx = i + 2
                depth += 1
                i += 1
            elif char == '}' and next_char == '}':
                depth -= 1
                i += 1
                if depth == 0:
                    if compound_flag:
                        if len(sections):
                            if type(sections[-1]) is not list:
                                sections[-1] = [sections[-1]]
                            sections[-1].append(line[start_idx:i-1])
                        compound_flag = False
                    else:
                        sections.append(line[start_idx:i-1])
            elif char == '+' and depth == 0:  # Compound
                compound_flag = True
            i += 1

        return sections

    def get_base_list(self, l):
        if len(l) == 1 and type(l[0]) is list:
            return self.get_base_list(l[0])
        return l

    def process_sub_braces(self, e):
        sub = []
        children = self.separate_pipes(e)
        for i, c in enumerate(children):
            key, val = self.split_key(c)
            e_child = self.get_curly_braces(val)
            if len(e_child):
                dub_sub = []
                for e_c in self.get_base_list(e_child):
                    dub_sub.append(self.separate_pipes(e_c))
                sub.append([key, dub_sub])
            else:
                sub.append([key, val])
        return sub

    def get_all_braces(self, line):
        output = []
        entries = self.get_curly_braces(line)
        for e in entries:
            if type(e) is list:
                sub = []
                for cmp in e:
                    compound_sub = self.process_sub_braces(cmp)
                    sub.append(compound_sub)
            else:
                sub = self.process_sub_braces(e)
            output.append(sub)
        return output

    @staticmethod
    def is_header(line):
        if line[0] == '=':
            return True
        return False

    @staticmethod
    def get_header_depth(header_line):
        i = 0
        while header_line[i] == '=':
            i += 1
        return i

    @staticmethod
    def is_lang(line):
        if line[:18] == '{{wikipedia||lang=':
            return True
        return False

    def create_other_entry(self, reinit_pos=True, increment_etym=False):
        new_entry = copy.copy(self)

        # Only have "self" contain list of other entries (prevent useless deeper recursion)
        self.other_entries = new_entry.other_entries
        new_entry.other_entries = []

        self.other_entries.append(new_entry)
        self.reinitialize(reinit_pos)
        if increment_etym:
            self.etym_number += 1

    def process_header(self, line):
        header_depth = self.get_header_depth(line)
        header = line[header_depth:-header_depth].strip()
        self.headers.append(header + '-' + str(header_depth))

        lang_depth = 2
        if header_depth == lang_depth and header in self.TAGS.lang2iso:
            self.iso_code = self.TAGS.lang2iso[header]
        elif header == 'Pronunciation':
            return State.PRONOUNCE
        elif header_depth == 3:
            if header[:9] == 'Etymology':
                if len(header) > 9 and header != 'Etymology 1':  # Create another Entry if multiple etymologies given
                    self.create_other_entry(increment_etym=True)
                return State.ETYM

        if header in self.TAGS.POS:
            self.pos.append(header)

        return State.OTHER

    def process_lang(self, line):
        lang_id = line[18:-2]
        self.iso_code = self.iso2full_iso(lang_id)

    def set_derivation(self, der):
        if der in self.TAGS.save_ety_tags:
            self.derivation = self.TAGS.save_ety_tags[der]
            return True
        return False

    def set_root_lang(self, lang_id):
        self.root_lang = self.iso2full_iso(lang_id)
        if len(self.root_lang):
            return True
        return False

    def set_root_word(self, src_words, rom, ipa):
        result = False
        for word in src_words:
            if len(word) and word != '-':
                self.root_word.append(word)
                result = True
        if len(rom):
            self.root_roman = re.sub(' ', '+', rom)
            result = True
        if len(ipa):
            self.root_ipa = ipa
            result = True
        return result

    @staticmethod
    def process_src_word(src_word):
        src_word = re.sub('\([^)]*\)', '', src_word)
        src_word = re.sub('\[', '', src_word)
        src_word = re.sub(']', '', src_word)

        # If there is a list of words, split the words into a list
        splits = re.search(', ', src_word)
        if splits is not None:
            words = [src_word[:splits.start()], src_word[splits.end():]]
        else:
            words = [re.sub('\s+', '+', src_word.strip())]

        return words

    def set_nonstandard_root(self, lang_id):
        self.nonstandard_root_code = lang_id
        if lang_id in self.TAGS.nonstandard2standard:
            self.root_lang = self.TAGS.nonstandard2standard[lang_id]

    def parse_etymology(self, etym):
        # Check if compound
        if type(etym[0][0]) is list:
            cmp_der, cmp_src_lang_id, cmp_src_word, cmp_rom, cmp_ipa = [], [], [], [], []
            for cmp in etym:
                der, src_lang_id, src_word, rom, ipa = self.get_etym_vars(cmp)
                cmp_der.append(der)
                cmp_src_lang_id.append(src_lang_id)
                if len(src_word):
                    cmp_src_word.append(src_word)
                if len(rom):
                    cmp_rom.append(rom)
                if len(ipa):
                    cmp_ipa.append(ipa)
            der = cmp_der[0]
            src_lang_id = cmp_src_lang_id[0]
            src_word = '+'.join(cmp_src_word)
            rom = '+'.join(cmp_rom)
            ipa = '+'.join(cmp_ipa)
        else:
            der, src_lang_id, src_word, rom, ipa = self.get_etym_vars(etym)

        result = True
        result *= self.set_derivation(der)
        if not self.set_root_lang(src_lang_id):
            self.set_nonstandard_root(src_lang_id)

        self.set_root_word(self.process_src_word(src_word), rom, ipa)

        if not result:  # If any of the steps failed, delete the other parts
            self.reinitialize(reinit_pos=False)

    def compare_entry(self, der, lang_id, src_word, entry):
        if der in self.TAGS.save_ety_tags:
            der_tag = self.TAGS.save_ety_tags[der]

            iso = self.iso2full_iso(lang_id)
            if not len(iso):
                if lang_id != entry.nonstandard_root_code:
                    return False

            if entry.derivation == der_tag and src_word in entry.root_word:
                return True

        return False

    def iso2full_iso(self, lang_id):
        if lang_id not in self.TAGS.iso2lang:
            return ''
        lang = self.TAGS.iso2lang[lang_id]
        iso = self.TAGS.lang2iso[lang]
        return iso

    def combine_last_elements(self, l):
        combined = []
        for e in l:
            combined.append(e[-1])
        return '+'.join(combined)

    def is_latin(self, uchr):
        try:
            return self.latin_letters[uchr]
        except KeyError:
            return self.latin_letters.setdefault(uchr, 'LATIN' in ud.name(uchr))

    def only_roman_chars(self, unistr):
        return all(self.is_latin(uchr) for uchr in unistr if uchr.isalpha())  # isalpha suggested by John Machin

    def process_tr(self, string):
        if type(string) is list:
            string = self.combine_last_elements(string)

        if not self.only_roman_chars(string):
            return ''

        processed = re.sub('[\[\]]', '', string)
        processed = re.sub(r'<sub>\w*</sub>', '', processed)
        processed = re.sub(r'<sup>\w*</sup>\.?', '', processed)
        processed = re.sub(r'&lt;sub&gt;\w*&lt;/sub&gt;', '', processed)
        processed = re.sub(r'&lt;sup&gt;\w*&lt;/sup&gt;\.?', '', processed)

        return processed

    def get_etym_vars(self, etym):
        der = src_lang_id = src_word = romanized = ipa = ''
        for i, (key, var) in enumerate(etym):
            if key == 'tr':
                romanized = self.process_tr(var)
            elif key == 'ts':
                ipa = '/{}/'.format(self.process_tr(var))
            elif key == 'sort':
                # TODO: implement. Should this accept the next entry as the root word?
                pass
            elif not len(key):
                if i == 0:
                    der = var
                    if der not in self.TAGS.save_ety_tags and der != 'm':
                        break
                elif der in ['cognate', 'cog', 'm']:
                    if i == 1:
                        src_lang_id = var
                    elif i == 2:
                        src_word = self.process_src_word_var(var)
                elif i == 2:
                    src_lang_id = var
                elif i == 3:
                    src_word = self.process_src_word_var(var)

        return der, src_lang_id, src_word, romanized, ipa

    def process_etymologies(self, line):
        etyms = self.get_all_braces(line)

        for i, etym in enumerate(etyms):
            self.create_other_entry(reinit_pos=False)
            self.parse_etymology(etym)

            # Some Middle Chinese words are split across two etymology tags
            if self.root_lang == 'ltc' and not len(self.root_word):
                if i + 1 < len(etyms):
                    next_etym = etyms[i+1]
                    if len(next_etym) >= 2 and next_etym[0][1] == 'ltc-l':
                        word = re.sub('[\[\]\(\)]', '', next_etym[1][1])
                        self.root_word.append(word)

    def is_compound_pair(self, pair):
        if len(pair) > 1 and type(pair[1]) is list:
            return True
        return False

    def get_pron_vars(self, pron):
        lbl = phonemic = phonetic = ''
        for i, pair in enumerate(pron):
            if self.is_compound_pair(pair):
                continue
            key, val = pair
            if len(key):
                continue
            elif i == 0:
                lbl = val
                if lbl not in ['IPA', 'IPAchar']:
                    break
            elif i > 1 and len(val):
                if val[0] == '/' and not len(phonemic):
                    phonemic = val
                    break
                elif val[0] == '[' and not len(phonetic):
                    phonetic = val
                    break

        return lbl, phonemic, phonetic

    def parse_pronunciation(self, pron, accent=''):
        self.universal_pronunciation = True
        for header in self.headers:
            if header[:9] == 'Etymology':
                self.universal_pronunciation = False
                break

        _, phonemic, phonetic = self.get_pron_vars(pron)
        if not len(self.ipa):
            if len(phonemic):
                self.ipa = phonemic
            elif len(phonetic):
                self.ipa = phonetic
        elif self.ipa[0] == '[' and len(phonemic):
            self.ipa = phonemic

    def process_pronunciation(self, line):
        pronunciations = self.get_all_braces(line)

        accent = ''
        for i, pron in enumerate(pronunciations):
            if len(pron) == 2 and pron[0][1] == 'a':
                accent = pron[1][1]
            else:
                self.parse_pronunciation(pron, accent)

        for entry in self.other_entries:
            if entry.etym_number == self.etym_number:
                entry.ipa = self.ipa

    def parse(self):
        state = State.OTHER
        for line in self.raw_text:
            if self.is_header(line):
                state = self.process_header(line)
            elif self.is_lang(line):
                self.process_lang(line)
            elif state is State.ETYM:
                self.process_etymologies(line)
            elif state is State.PRONOUNCE:
                self.process_pronunciation(line)

    def to_list(self, dist):
        output = []
        if not len(self.root_word):  # If only a transcription or romanization is available
            output.append([self.word, self.iso_code, self.pos, self.ipa, self.root_lang, self.nonstandard_root_code, '',
                    self.root_roman, self.root_ipa, self.derivation, dist, self.etym_number])

        for word in self.root_word:
            output.append([self.word, self.iso_code, self.pos, self.ipa, self.root_lang, self.nonstandard_root_code, word,
                           self.root_roman, self.root_ipa, self.derivation, dist, self.etym_number])

        return output

    def to_full_list(self):
        full_list = []

        dist = 0
        prev_etym_number = self.etym_number

        for entry in self.other_entries:
            if entry.etym_number != prev_etym_number:
                dist = 0
                prev_etym_number = entry.etym_number

            if len(entry.root_lang) or len(entry.nonstandard_root_code):
                if entry.derivation in ['cognate', 'cog', 'm']:  # Don't set a dist for words that aren't ancestors
                    if len(entry.root_word) or len(entry.root_roman) or len(entry.root_ipa):
                        full_list.extend(entry.to_list(dist=0))
                else:
                    dist += 1
                    full_list.extend(entry.to_list(dist))

        if len(self.root_lang) or len(self.nonstandard_root_code):
            if self.derivation in ['cognate', 'cog', 'm']:  # Don't set a dist for words that aren't ancestors
                if len(self.root_word) or len(self.root_roman) or len(self.root_ipa):
                    full_list.extend(self.to_list(0))
            else:
                dist += 1
                full_list.extend(self.to_list(dist))

        return full_list

    @staticmethod
    def combine_first(l1, l2, idx):
        return l1[idx]

    @staticmethod
    def combine_pos(l1, l2, idx):
        pos1 = l1[idx]
        pos2 = l2[idx]
        return list(set(pos1) | set(pos2))

    @staticmethod
    def combine_ipa(l1, l2, idx):
        ipa1 = l1[idx]
        ipa2 = l2[idx]

        if not len(ipa1):
            return ipa2
        if not len(ipa2):
            return ipa1
        if ipa1[0] == '/' and ipa2[0] != '/':
            return ipa1
        if ipa1[0] != '/' and ipa2[0] == '/':
            return ipa2
        if len(ipa1) >= len(ipa2):
            return ipa1
        return ipa2

    @staticmethod
    def combine_by_greater_length(l1, l2, idx):
        val1 = l1[idx]
        val2 = l2[idx]
        if len(val1) >= len(val2):
            return val1
        return val2

    @staticmethod
    def combine_der(l1, l2, idx):
        der1 = l1[idx]
        der2 = l2[idx]
        if der1 == 'der' and der2 != 'cog':
            return der2
        return der1

    @staticmethod
    def combine_dist(l1, l2, idx):
        dist1 = l1[idx]
        dist2 = l2[idx]
        if dist1 == 0:
            return dist2
        elif dist2 == 0:
            return dist1
        elif dist1 <= dist2:
            return dist1
        return dist2

    def combine_duplicates(self, l1, l2):
        combined = [self.combine_first(l1, l2, 0)]
        combined.append(self.combine_first(l1, l2, 1))
        combined.append(self.combine_pos(l1, l2, 2))
        combined.append(self.combine_ipa(l1, l2, 3))
        combined.append(self.combine_by_greater_length(l1, l2, 4))
        combined.append(self.combine_by_greater_length(l1, l2, 5))
        combined.append(self.combine_by_greater_length(l1, l2, 6))
        combined.append(self.combine_by_greater_length(l1, l2, 7))
        combined.append(self.combine_by_greater_length(l1, l2, 8))
        combined.append(self.combine_der(l1, l2, 9))
        combined.append(self.combine_dist(l1, l2, 10))
        combined.append(self.combine_dist(l1, l2, 11))

        return combined

    def lang_duplicates(self, l1, l2):
        lang1 = l1[4]
        lang2 = l2[4]
        return lang1 == lang2

    def word_duplicates(self, l1, l2):
        word1 = l1[6]
        word2 = l2[6]
        if word1 == word2 or not len(word1) or not len(word2):
            return True
        return False

    def are_duplicates(self, l1, l2):
        return self.lang_duplicates(l1, l2) and self.word_duplicates(l1, l2)

    def check_list_duplicates(self, full_list):
        while True:
            temp_list = []
            merged_idxs = []
            for i, l1 in enumerate(full_list):
                for j, l2 in enumerate(full_list):
                    if i >= j or i in merged_idxs or j in merged_idxs:
                        continue
                    if self.are_duplicates(l1, l2):
                        temp_list.append(self.combine_duplicates(l1, l2))
                        merged_idxs.append(i)
                        merged_idxs.append(j)

            for k, l in enumerate(full_list):
                if k not in merged_idxs:
                    temp_list.append(l)

            if len(temp_list) == len(full_list):
                break
            full_list = temp_list

        return full_list

    @staticmethod
    def list_to_string(entry_list):
        pos = entry_list[2]
        entry_list[2] = '/'.join(sorted(pos))
        entry_list = entry_list[:-1]
        entry_list[-1] = str(entry_list[-1])
        entry_list.append('wik')
        return ','.join(entry_list)

    def to_full_string(self):
        full_list = self.to_full_list()
        final_list = self.check_list_duplicates(full_list)
        return '\n'.join([self.list_to_string(x) for x in sorted(final_list, key=lambda x: (x[-1], x[-2]))])


if __name__ == "__main__":
    word = 'test'
    raw_text = []
    with open('inputs/test.txt', 'r', encoding='utf-8') as f:
        raw_text = [x for x in f.read().splitlines() if len(x)]
    test = WiktionaryEntry(word, raw_text)
    # print(test.check_list_duplicates(test.to_full_list()))
    print(test.to_full_string())

    # line = 'From {{bor|id|jv|ꦲꦭꦱ꧀|t=forest|tr={{l|jv|alas}}}}, from {{der|id|poz-pro|*halas|t=forest, wilderness, woods, jungle}}, from {{der|id|map-pro|*Salas|t=forest, wilderness, woods}}. Cognate to {{cog|ban|ᬳᬮᬲ᭄|t=forest|tr=alas}}.'
    # line = 'From {{inh|af|nl|({{l|nl|de}}) {{l|nl|hare}}}}.'
    # line = '{{calque|fr|ja|日本||Japan|tr={{l|ja|にほん}}, Nihon}}.'
    # line = 'Borrowing from {{bor|ja|vi|東京|sort=とんきん|tr={{l|vi|Đông Kinh}}|t=[[Eastern]] [[capital]]}}, a historical name for [[Hanoi]]. {{rfv-etym|ja}}'
    # entries = test.get_all_braces(line)
    # for e in entries:
    #     print(e)


# TODO: {{etyl|la|en}} {{m|la|geologia}}
# TODO: when one entry contains etymologyical relations not contained in those words' entries... separate into chain?
# TODO: check borrowings with dist > 1. Should this be possible?
# TODO: check compounds with space vs. with +, compare with main entry word))
# (TODO: handle non-standard codes)
# (TODO: set distance to word)
# (TODO: include romanization/transcription if available (tr/ts))
# (TODO: check that right-to-left languages are saved properly)
# (TODO: fix "sort=")
# (TODO: check that there are no duplicates)
# (TODO: Fix that pronunciations aren't processed until after the etymologies have already been saved)
# (TODO: include pronunciation for recipient words, if available)
# (TODO: handle compounds > 2)
# TODO: (remove [[ ]], (.*), and add + to internal compounds)
