from WiktionaryEntry import WiktionaryEntry
from WiktionaryTags import WiktionaryTags
import gc


class WiktionaryExtractor(object):
    def __init__(self):
        self.entries = []
        self.current_entry_text = []
        self.current_page_title = None
        self.saving_flag = False  # When True, create WiktionaryEntry; when False, continue

        self.TAGS = WiktionaryTags()
        self.wiktionary_dump_filepath = 'inputs/truncated_enwiktionary-20200820-pages-articles.xml'

    @staticmethod
    def write_entry(entry=None):
        output_str = '1'
        if entry is not None:
            output_str = entry.to_full_string()
        if len(output_str):
            with open('outputs/WiktionaryOutput.csv', 'a', encoding='utf-8') as writer:
                writer.write(output_str + '\n')

    # Create a new WiktionaryEntry object and either write to output CSV file or append to self.entries
    def create_entry(self, write=False):
        if self.current_page_title == 'abansada':
            print('CREATING')
            new_entry = WiktionaryEntry(self.current_page_title, self.current_entry_text)
            print(self.current_entry_text)
            print(new_entry)
            print(new_entry.to_full_string())
            if write:
                self.write_entry(new_entry)
            else:
                self.entries.append(new_entry)

            self.saving_flag = False
        else:
            self.write_entry()

        self.current_entry_text = []
        gc.collect()

    @staticmethod
    def is_meta(line):
        if line[0] == '<':
            return True
        return False

    def process_meta(self, meta_line):
        if self.saving_flag:
            self.create_entry(write=True)

        word_tag = '<title>'
        if meta_line[:len(word_tag)] == word_tag:
            self.current_page_title = meta_line[len(word_tag):-(len(word_tag) + 1)]
            if ':' in self.current_page_title[:11]:  # This is an explanatory page, not a definitions page
                self.saving_flag = False

            if self.current_page_title == 'abansada':
                print('Found')

    @staticmethod
    def get_header_depth(header_line):
        i = 0
        while i < len(header_line) and header_line[i] == '=':
            i += 1
        return i

    @staticmethod
    def is_header(line):
        if line[0] == '=':
            return True
        return False

    @staticmethod
    def is_lang(line):
        if line[:18] == '{{wikipedia||lang=':
            return True
        return False

    def process_header(self, header_line):
        lang_depth = 2
        if self.get_header_depth(header_line) == lang_depth:
            if self.saving_flag:
                self.create_entry(write=True)

            lang = header_line[lang_depth:-lang_depth]
            if lang in self.TAGS.lang2iso:
                self.saving_flag = True

    def process_lang_id(self, line):
        lang_id = line[18:-2]
        if self.saving_flag:
            self.create_entry(write=True)

        if lang_id in self.TAGS.iso2lang:
            self.saving_flag = True

    def process_line(self, line):
        line = line.strip()
        if not len(line):
            return
        elif self.is_meta(line):
            self.process_meta(line)
        elif self.is_header(line):
            self.process_header(line)
        elif self.is_lang(line):
            self.process_lang_id(line)

        if self.saving_flag:
            self.current_entry_text.append(line)

    def run(self):
        with open(self.wiktionary_dump_filepath, 'r+', encoding='utf-8') as f:
            for line in f:
                self.process_line(line)

    def test_cycle(self):
        stream_len = 100000
        import time
        start = time.time()
        with open(self.wiktionary_dump_filepath, 'r+', encoding='utf-8') as f:
            end_index = float('inf')
            stream = [None]*stream_len
            for i, line in enumerate(f):
                if line.strip() == '<title>abansada</title>':
                    end_index = i + 100
                elif i > end_index:
                    extract_lines = stream[i % stream_len:] + stream[:i % stream_len]
                    with open('inputs/truncated_enwiktionary-20200820-pages-articles.xml', 'w', encoding='utf-8') as w:
                        for extract_line in extract_lines:
                            w.write(extract_line)
                            w.write('\n')
                    break
                stream[i % stream_len] = line[:-1]

        print('Time: {:02f} sec'.format(time.time() - start))


if __name__ == "__main__":
    scraper = WiktionaryExtractor()
    scraper.run()

    for entry in scraper.entries:
        print(entry.to_full_string())
    # scraper.test_cycle()
