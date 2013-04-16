import argparse
import cgi
from datetime import datetime
import re

from lxml import etree
import xlwt


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

    def split_line(self, line):
        '''
        split F5 line into timestamp and rest of line
        '''
        stamp_pattern = r"\d\d:\d\d:\d\d-\d"
        match = re.match(stamp_pattern, line)
        if match:
            return match.group(0), line[10:]
        return None, line

    def smash_line(self, line):
        '''
        Strips out all whitespace for easy matching.
        '''
        timestamp, line = self.split_line(line)
        return "".join(line.split())

    def smash_quote(self, quote):
        '''
        Returns a list of lines within a quote. Strips out all whitespace for 
        easy matching.  Atlas.ti removes converts strings to HTML, so normal 
        matching is not possible.
        '''
        plist = []
        for p in quote.findall('content/p'):
            if p.text:
                plist.append(''.join(p.text.split()))
            else:
                plist.append('')
        return plist

    def find_matching_lines(self, q=None, qid=None):
        '''
        Begins looking for matches on the line Atlas.ti says it should.
        However, various things can throw it off, so don't trust it.
        Go to the next line if a match isn't found right away.
        Make sure all lines from a quote are included.
        '''
        assert(q is not None or qid is not None)
        if q is None:
            q = self.quote_by_id(qid)
        # find starting point for search
        start, end = self.quote_line_nums(q)
        # find number of lines in quote and build empty match list
        length = end - start + 1
        matches = [None] * length
        # get the lines in the quote with whitespace removed
        smshqs = self.smash_quote(q)
        # loop through each line in quote
        for i in range(length):
            # now loop through each line in f5 beginning from start
            while not matches[i] and start < len(self.f5lines):
                # get f5 line with whitespace removed
                smshln = self.smash_line(self.f5lines[start])
                # test for 'in' not '=='' because quotes in Atlas.ti don't always
                # include the entire line
                if smshqs[i] in smshln:
                    matches[i] = (start, self.f5lines[start])
                # always push starting point up, regardless of match
                start += 1
        # if any lines did not match don't bother returning a partial list
        if not all(matches):
            return None
        return matches


