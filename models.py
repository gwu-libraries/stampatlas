from datetime import datetime
import re

from lxml import etree
import xlwt

# Create constant string of chars to strip out of text for matching
NON_ALPHANUMS = ''.join(c for c in map(chr, range(256)) if not c.isalnum())
VOWELS = 'AaEeIiOoUu'


class AtiXML():

    def __init__(self, path):
        self.root = self.parse_xml(path)

    def parse_xml(self, path):
        tree = etree.parse(path)
        return tree.getroot()

    @property
    def quotes(self):
        return self.root.xpath("primDocs/primDoc[@id='pd_1']/quotations/q")

    @property
    def links(self):
        return self.root.xpath("links/objectSegmentLinks/codings/iLink")

    @property
    def codes(self):
        return self.root.xpath("codes/code")

    @property
    def memos(self):
        return self.root.xpath("memos/memo")

    @property
    def codefams(self):
        return self.root.xpath("families/codeFamilies/codeFamily")

    def quote_by_id(self, qid):
        xpath = "primDocs/primDoc[@id='pd_1']/quotations/q[@id='%s']" % qid
        quotes = self.root.xpath(xpath)
        return quotes[0] if quotes else None

    def code_by_id(self, cid):
        codes = self.root.xpath("codes/code[@id='%s']" % cid)
        return codes[0] if codes else None

    def link_exists(self, cid, qid):
        xpath = "links/objectSegmentLinks/codings/iLink[@obj='%s' and @qRef='%s']"
        xpath = xpath % (cid, qid)
        links = self.root.xpath(xpath)
        return True if links else False

    def add_f5_file(self, path):
        self.f5lines = self.parse_f5(path)

    def parse_f5(self, path):
        '''
        return a 1-based list of lines from the F5 file
        '''
        f5 = open(path, 'r')
        lines = f5.readlines()
        f5.close()
        lines.insert(0, '')
        return lines

    def quote_line_nums(self, q=None, qid=None):
        '''
        return the starting and ending line numbers for a quote
        according to Atlas.ti data (which may be wrong)
        '''
        assert(q is not None or qid is not None)
        if q is None:
            q = self.quote_by_id(qid)
        start, end = q.get('loc').strip('!').split(',')
        start = start.split('@')[1].strip()
        end = end.split('@')[1].strip()
        return int(start), int(end)

    def quote_text(self, quote=None, qid=None):
        try:
            if quote is None:
                quote = self.quote_by_id(qid)
            return ''.join([p.text for p in quote.findall('content/p') if p.text])
        except:
            print 'Error with quote: %s' % quote.get('id')
            raise

    def split_line(self, line):
        '''
        split F5 line into timestamp and rest of line
        '''
        stamp_pattern = r"\d\d:\d\d:\d\d-\d"
        match = re.match(stamp_pattern, line)
        if match:
            return match.group(0), line[10:]
        return None, line

    def smash_line(self, line, how_hard=0):
        '''
        Strips out all whitespace and, optionally, non-alphnumerics for easy 
        matching.
        '''
        timestamp, line = self.split_line(line)
        smashed = "".join(line.split())
        if how_hard > 0:
            smashed = smashed.translate(None, NON_ALPHANUMS)
        if how_hard > 1:
            smashed = smashed.translate(None, VOWELS)
        return smashed

    def smash_quote(self, quote=None, qid=None, how_hard=0):
        '''
        Returns a list of lines within a quote. Strips out all whitespace and,
        optionally, non-alphanumerics for easy matching.  Atlas.ti removes 
        converts strings to HTML, so normal matching is not possible.
        '''
        if quote is None and qid is not None:
            quote = self.quote_by_id(qid)
        plist = []
        for p in quote.findall('content/p'):
            if p.text:
                # as last resort use the shortened quote in the name attribute
                if how_hard == 3:
                    smashed = ''.join(quote.get('name').split())
                else:
                    smashed = ''.join(p.text.split())
                if how_hard > 0:
                    smashed = smashed.translate(None, NON_ALPHANUMS)
                if how_hard > 1:
                    smashed = smashed.translate(None, VOWELS)
                plist.append(smashed)
            else:
                plist.append('')
        return plist

    def find_matching_lines(self, q=None, qid=None, rigor=0):
        '''
        Begins looking for matches on the line Atlas.ti says it should.
        However, various things can throw it off, so don't trust it.
        Go to the next line if a match isn't found right away.
        Make sure all lines from a quote are included.
        '''
        assert(q is not None or qid is not None)
        if q is None:
            q = self.quote_by_id(qid)
        if rigor > 2:
            return self.guess_matching_lines(q)
        # find starting point for search
        start, end = self.quote_line_nums(q)
        # find number of lines in quote and build empty match list
        length = end - start + 1
        matches = [None] * length
        # get the lines in the quote with whitespace removed
        smshqs = self.smash_quote(q, how_hard=rigor)
        # loop through each line in quote
        for i in range(length):
            # now loop through each line in f5 beginning from start
            while not matches[i] and start < len(self.f5lines):
                # get f5 line with whitespace removed
                smshln = self.smash_line(self.f5lines[start], how_hard=rigor)
                # test for 'in' not '=='' because quotes in Atlas.ti don't always
                # include the entire line
                if smshqs[i] in smshln:
                    matches[i] = (start, self.f5lines[start])
                # always push starting point up, regardless of match
                start += 1
        # If any lines did not match don't bother returning a partial list.
        # But before giving up, try again with non-alphanumerics stripped out.
        # We don't do this from the start because some lines are all symbols.
        if not all(matches):
            if rigor < 3:
                return self.find_matching_lines(q, rigor=rigor+1)
            return None
        return matches



    def next_timestamp(self, linenum):
        time, line = None, None
        while time is None:
            linenum += 1
            time, line = self.split_line(self.f5lines[linenum])
        return time

    def previous_timestamp(self, linenum):
        time, line = None, None
        while time is None:
            linenum -= 1
            time, line = self.split_line(self.f5lines[linenum])
        return time

    def duration(self, start, end):
        try:
            s = datetime.strptime(start, "%H:%M:%S-%f")
            e = datetime.strptime(end, "%H:%M:%S-%f")
            return str(e - s)
        except:
            print 'ERROR calculating duration! start: %s  end: %s' % (start, end)
            return ''

    def merge_timestamps(self, f5path=None):
        if f5path:
            self.add_f5_file(f5path)

        errors = []
        for quote in self.quotes:
            matches = self.find_matching_lines(quote)
            if matches is None:
                start, estend, startline, endline = '', '', '', ''
                errors.append(quote.get('id'))
            else:
                # get start and finish line numbers
                startline = str(matches[0][0])
                endline = str(matches[-1][0])
                # get start timestamp or estimate based on previous line
                start, sline, x = None, None, 0
                while start is None:
                    if x < len(matches):
                        start, sline = self.split_line(matches[x][1])
                        x += 1
                    # if no timestamp, grab one from previous line
                    else:
                        eststart = self.previous_timestamp(matches[0][0])
                        quote.set('estimatedStartTime', eststart)
                        start = ''
                # get estimated end time by finding the next timestamp
                estend = self.next_timestamp(matches[-1][0])
            # now add values to xml
            quote.set('startTime', start)
            quote.set('estimatedEndTime', estend)
            quote.set('startLine', startline)
            quote.set('endLine', endline)
        output = open('testout.xml', 'w')
        output.write(etree.tostring(self.root))
        output.close()
        return errors

    # Here begins the Excel methods

    def writerow(self, sheet, rownum, values):
        for celnum, value in enumerate(values):
            sheet.write(rownum, celnum, value)

    def writefirstrow(self, sheet):
        labels = ['HU Name', 'Onset time', 'Est. Duration', 'Text', 'All Codes']
        for code in self.codes:
            labels.append(code.get('name'))
        labels.append('Code Count')
        self.writerow(sheet, 0, labels)

    def writequotes(self, sheet):
        for row, quote in enumerate(self.quotes, start=1):
            values = [self.root.find('hermUnit').get('name')]
            values.append(quote.get('startTime'))
            values.append(self.duration(quote.get('startTime'),
                quote.get('estimatedEndTime')))
            values.append(self.quote_text(quote))
            values.append([])
            link_count = 0
            for code in self.codes:
                if self.link_exists(code.get('id'), quote.get('id')):
                    values.append(1)
                    values[4].append(code.get('name'))
                    link_count += 1
                else:
                    values.append(0)
            values[4] = ', '.join(values[4])
            values.append(link_count)
            self.writerow(sheet, row, values)

    def export_to_excel(self, filename):
        wkbk = xlwt.Workbook(encoding='utf-8')
        sheet = wkbk.add_sheet('codings')
        self.writefirstrow(sheet)
        self.writequotes(sheet)
        wkbk.save(filename)
