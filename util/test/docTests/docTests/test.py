#!/usr/bin/env python
# encoding: utf-8

from __future__ import print_function

"""
Test suite for reSTTest.py
"""

import sys
import unittest

import reSTTest as doctest


class Testdoctest(unittest.TestCase):

    def test_sample(self):
        """Basic sample code-block"""

        tests = doctest.main('tests/sample.rst')
        self.assertEqual(len(tests), 1)

    def test_indent(self):
        """Varying levels of indentation"""

        tests = doctest.main('tests/indents.rst')
        self.assertEqual(len(tests), 1)
        test = tests[0]

        code = "writeln('0');"
        self.assertEqual(test.code, code)
        post = " writeln('1');\nwriteln('2');"

        self.assertEqual(test.post, post)

    def test_output(self):
        """Test :chapeloutput:"""

        tests = doctest.main('tests/features.rst')
        test = tests[0]
        output = 'features'
        self.assertEqual(test.output, output)

    def test_printoutput(self):
        """Test :chapelprintoutput:"""

        tests = doctest.main('tests/features.rst')
        test = tests[0]
        self.assertTrue(test.printoutput)

    def test_pre(self):
        """Test :chapelpre:"""

        tests = doctest.main('tests/features.rst')
        test = tests[0]
        pre = 'var x = 1;'
        self.assertEqual(test.pre, pre)

    def test_post(self):
        """Test :chapelpost:"""

        tests = doctest.main('tests/features.rst')
        test = tests[0]
        post = 'var y = 2;'
        self.assertEqual(test.post, post)

    def test_future(self):
        """Test :chapelfuture:"""

        tests = doctest.main('tests/features.rst')
        test = tests[0]
        future = 'feature: finish this some day'
        self.assertEqual(test.future, future)

    def test_compopts(self):
        """Test :chapelcompopts:"""

        tests = doctest.main('tests/features.rst')
        test = tests[0]
        compopts = '--fast'
        self.assertEqual(test.compopts, compopts)

    def test_execopts(self):
        """Test :chapelexecopts:"""

        tests = doctest.main('tests/features.rst')
        test = tests[0]
        execopts = '-v'
        self.assertEqual(test.execopts, execopts)

    def test_prediff(self):
        """Test :chapelprediff:"""

        tests = doctest.main('tests/features.rst')
        test = tests[0]
        prediff = '#!/bin/bash\nls'
        self.assertEqual(test.prediff, prediff)

    def test_append(self):
        """Test :chapelappend:"""

        tests = doctest.main('tests/features.rst')
        test = tests[0]
        self.assertTrue(test.append)


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(Testdoctest)
    exitcode = not unittest.TextTestRunner(verbosity=1).run(suite)
    sys.exit(exitcode)

