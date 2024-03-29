import unittest

import models


test_ati_xml = "sample_data/confidential/ati-sample1.xml"
test_f5 = ("sample_data/confidential/f5-sample1.txt")


class TestStampAtlas(unittest.TestCase):

    def setUp(self):
        self.ati = models.AtiXML(test_ati_xml)
        self.ati.add_f5_file(test_f5)

    def test_properties(self):
        self.assertEqual(len(self.ati.quotes), 345)
        self.assertEqual(len(self.ati.codes), 50)
        self.assertEqual(len(self.ati.memos), 7)
        self.assertEqual(len(self.ati.codefams), 8)
        self.assertEqual(len(self.ati.links), 442)

    def test_quote_by_id(self):
        quote = self.ati.quote_by_id('q1_4')
        self.assertEqual(quote.get('name'), "PA1: I went to /Furman_Univers..")

    def test_code_by_id(self):
        code = self.ati.code_by_id('co_7')
        self.assertEqual(code.get('name'), "CORR- Corrective Laughter")

    def test_link_exists(self):
        self.assertTrue(self.ati.link_exists('co_3', 'q1_325'))
        self.assertFalse(self.ati.link_exists('co_3', 'q1_444'))

    def test_parse_f5(self):
        lines = self.ati.parse_f5(test_f5)
        self.assertEqual(len(lines), 228)
        self.assertEqual(lines[2], "00:00:00-0 ((fMRI begins))\n")

    def test_quote_line_nums(self):
        q = self.ati.quote_by_id('q1_14')
        start, end = self.ati.quote_line_nums(q)
        self.assertEqual(start, 36)
        self.assertEqual(end, 36)

        start, end = self.ati.quote_line_nums(qid='q1_121')
        self.assertEqual(start, 42)
        self.assertEqual(end, 58)

        start, end = self.ati.quote_line_nums(qid='q1_27')
        self.assertEqual(start, 61)
        self.assertEqual(end, 62)

    def test_split_line(self):
        line = self.ati.f5lines[164]
        timestamp, line = self.ati.split_line(line)
        self.assertEqual(timestamp, '00:07:31-4')
        self.assertEqual(line, " PA2: Oh okay that's nice. \n")

    def test_smash_line(self):
        line = self.ati.f5lines[170]
        exp = "PA1ThatIthinkwouldbeachallengeunlessyouwerereallyreallyfluentinthelanguage"
        self.assertEqual(self.ati.smash_line(line, how_hard=True), exp)

    def test_smash_quote(self):
        quote1 = self.ati.quote_by_id('q1_193')
        exp1 = "ThatIthinkwouldbeachallengeunlessyouwerereallyreallyfluentinthelanguage"
        self.assertEqual(self.ati.smash_quote(quote1, how_hard=True)[0], exp1)
        quote2 = self.ati.quote_by_id('q1_27')
        exp2 = ""
        self.assertEqual(self.ati.smash_quote(quote2, how_hard=True)[0], exp2)

    def test_find_matching_lines(self):
        expected1 = [(61, '\n'), (62, '00:03:26-6 PA1: Oh /wow/ [@@]\n')]
        result1 = self.ati.find_matching_lines(qid='q1_27')
        self.assertEqual(result1, expected1)

        expected2 = [(208, "00:09:25-5 PA1:\tWe didn't (.). That was u:m (.) most of the fraternities and sororities didn't have a house where most of the l-members lived. They would ha:ve (.) [dedicated hallways] in the dorms\n"),
            (209, '\n'),
            (210, "00:09:33-2 PA2: \t\t\t\t   [Oh okay]  \tOh okay.\n"),
            (211, '\n'),
            (212, "00:09:35-9 PA1: But I-I- (.) I'm really not sure of the reasoning of that other tha:n (.) um national fraternities and sororities were fairly new on campus. Every thing was local (.) [until] about six seven years before I went there. So it was a pretty big financial investment to actually have houses. \n")]
        result2 = self.ati.find_matching_lines(qid='q1_118')
        self.assertEqual(result2, expected2)

        # Trouble records
        expected3 = [(176, "00:08:07-4 PA2: \t\t  [So] (1.8) /Yep/ so I was u:h-- I was in Massachusetts fo:r all three years. No vacations. @\n"),
            (177, '\n'),
            (178, "00:08:16-0 PA1: O:h no:. Did you--did you live close enough-- or was-- I'm guessing it wasn't close enough to drive home. Or did you just get to go home on break?\n")]
        result3 = self.ati.find_matching_lines(qid='q1_343')
        self.assertEqual(result3, expected3)

        '''
        # Corrected spelling causes no match
        expected4 = [(78, "00:04:02-8 PA1: I tr:ied intramural volleyball briefly and I turned out to be really really bad at it, but it was [more] fun as a social event [I think then] \t\tthen actual sport. ")]
        result4 = self.ati.find_matching_lines(qid='q1_35')
        self.assertEqual(result4, expected4)
        '''

    def test_merge_timestamps(self):
        errors = self.ati.merge_timestamps()
        self.assertEqual(len(errors), 0)

        result1 = self.ati.quote_by_id('q1_343').get('startTime')
        expected1 = '00:08:07-4'
        self.assertEqual(result1, expected1)

        result2 = self.ati.quote_by_id('q1_343').get('estimatedEndTime')
        expected2 = '00:08:24-6'
        self.assertEqual(result2, expected2)


if __name__ == '__main__':
    unittest.main()