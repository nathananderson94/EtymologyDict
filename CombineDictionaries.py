wiktionary_fp = 'outputs/WiktionaryOutput_old.csv'


def create_data_dict(word, lang, src_lang, src_word='', src_rom='', pos='', relation='', citation=''):
    return word, lang, src_lang, src_word, src_rom, pos, relation, citation


data = []

count = 0

with open(wiktionary_fp, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            word, lang, pos, src_lang, src_word, relation, citation = line.strip().split(',')
            data.append(create_data_dict(word, lang, src_lang, src_word, pos=pos, relation=relation, citation=citation))
            if lang == 'ind' and src_lang == 'nld' and relation == 'bor':
                count += 1
        except ValueError:
            continue

with open('inputs/EtymologyDicts/HIL_loanwords_ES.csv', 'r', encoding='utf-8') as f:
    for line in f:
        word, src_word = line.strip().split(',')
        data.append(create_data_dict(word, 'hil', 'spa', src_word, citation='kau'))

with open('inputs/EtymologyDicts/ID_loanwords_AR.csv', 'r', encoding='utf-8') as f:
    for line in f:
        word, src_word, src_rom = line.strip().split(',')
        data.append(create_data_dict(word, 'ind', 'ara', src_word, src_rom=src_rom, citation='wkp'))

with open('inputs/EtymologyDicts/ID_loanwords_SA.csv', 'r', encoding='utf-8') as f:
    for line in f:
        word, src_word, src_rom = line.strip().split(',')
        data.append(create_data_dict(word, 'ind', 'san', src_word, src_rom=src_rom, citation='wkp'))

with open('inputs/EtymologyDicts/ID_loanwords_EN.csv', 'r', encoding='utf-8') as f:
    for line in f:
        word, src_word = line.strip().split(',')
        data.append(create_data_dict(word, 'ind', 'eng', src_word, citation='wkp'))

with open('inputs/EtymologyDicts/ID_loanwords_NL.csv', 'r', encoding='utf-8') as f:
    for line in f:
        word, src_word = line.strip().split(',')
        data.append(create_data_dict(word, 'ind', 'nld', src_word, citation='wkp'))

with open('inputs/EtymologyDicts/ID_loanwords_PT.csv', 'r', encoding='utf-8') as f:
    for line in f:
        word, src_word = line.strip().split(',')
        data.append(create_data_dict(word, 'ind', 'por', src_word, citation='wkp'))

# TODO: Process SRN data

# for entry in sorted(data):
#     print(entry)

print(count)
