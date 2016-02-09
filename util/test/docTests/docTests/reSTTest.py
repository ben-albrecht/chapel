#!/usr/bin/env python
# encoding: utf-8

from __future__ import print_function

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from docutils import core

"""
Temporary global tuple of test data strings
Note: Maybe this should be a part of ChapelTest class?"""
testids = (':chapeloutput:',
           ':chapelprintoutput:',
           ':chapelpre:',
           ':chapelpost:',
           ':chapelfuture:',
           ':chapelcompopts:',
           ':chapelexecopts:',
           ':chapelprediff:',
           ':chapelfilebase:',
           ':chapelappend:',
          )

boolids = (':chapelprintoutput:', ':chapelappend:')

def getargs(args=None):
    """
    Get arguments from command line
    :args: arguments, if predefined
    :returns: arguments parsed
    """
    parser = ArgumentParser(prog='reSTTest',
                            usage='%(prog)s  reSTfile [options] ',
                            description=''' %(prog)s  parses reST files for
                            chapel tests''',
                            formatter_class=ArgumentDefaultsHelpFormatter
                            )
    parser.add_argument('reSTfile', help=' help')

    opts = parser.parse_args(args)
    return opts


class ChapelTest(object):
    """
    Class for using chapel test meta-data
    Goals:
        1.  Successfully parse a code-block::chapel √
            * Confirm some test cases:
                * Multiple tests
                * Multiline comment with testid
                * Various levels of indentation
        2. Successfully write a test.chpl from parsed data

    """

    def __init__(self,**testdata):
        """
        Setup all the test meta-data
        """
        # Dictionary of test meta-data parsed from reST comment blocks starting
        # with :chapelexample:
        self.data = testdata.copy()

        # Chapel code from codeblock
        self.code = self.getdata('chapelcode')

        # TODO
        # REQUIRED: Contents of this data is placed into the .good file
        self.output = self.getdata(':chapeloutput:')

        # TODO
        # This enables the output to be reinserted back into file as code block
        self.printoutput = self.getdata(':chapelprintoutput:')

        # TODO
        # This block of chapel code is placed before the next code block
        self.pre = self.getdata(':chapelpre:')

        # TODO
        # This block of chapel code is placed after the next code block
        self.post = self.getdata(':chapelpost:')

        # TODO
        # Contents are copied into their respective files verbatim
        self.future = self.getdata(':chapelfuture:')
        self.compopts = self.getdata(':chapelcompopts:')
        self.execopts = self.getdata(':chapelexecopts:')
        self.prediff = self.getdata(':chapelprediff:')
        # There are other filetypes, right? no perf-stuff though...

        # TODO
        # File base name for generating filenames, e.g. sample -> sample.good
        self.filebase = self.getdata(':chapelfilebase:')

        # TODO
        # Append the contents of this test to the previous test.
        # All other data in this chapelexample comment block will be ignored
        self.append = self.getdata(':chapelappend:')


    def getdata(self, dataname):
        if dataname in self.data.keys():
            return self.data[dataname]
        return None

    def write(self):
        """Write test data to file, based on filebase"""
        pass

    def getfilebase(self):
        """Determine path and file base name for test"""
        pass


def countindent(l):
    """Count indentation"""
    indentation = len(l) - len(l.strip(' '))
    return indentation


def extractdatablock(source):
    """Extract indented block starting with first line of source as testid"""

    if len(source) <= 1:
        return None

    datablock = []

    baseline = source[0]
    baseindent = countindent(baseline)


    minindent = countindent(source[1])

    for line in source[1:]:
        # Data block continues until indentation < 2
        if countindent(line) > baseindent + 1:
            datablock.append(line)
            if countindent(line) < minindent:
                minindent = countindent(line)
        else:
            break

    datablockunindented = [l[minindent:] for l in datablock]

    return '\n'.join(datablockunindented)


def extracttestdata(rawsource):
    """Extract test meta-data from comment block into dictionary"""
    global testids
    global boolids

    source = rawsource.split('\n')

    testdata = {}
    for line in source:
        linecontains = [d for d in testids if d in line]

        if linecontains:
            if len(linecontains) != 1:
                # TODO: raise error / logging ERROR
                print("Error: A line contains more than one test data ID")

            testid = linecontains[0]
            index = source.index(line)

            if testid in boolids:
                testdata[testid] = True
            else:
                testdata[testid] = extractdatablock(source[index:])

    return testdata


def doctreetraverse(node):
    """Breadth-first search of doctree for comments with testid"""

    thislevel = [node]
    testid = ':chapelexample:'

    tests = []
    while thislevel:
        nextlevel = []
        idfound = False

        for n in thislevel:

            # If the last node was a comment with testid
            if idfound and n.tagname == 'literal_block':
                testdata['chapelcode'] = n.rawsource
                tests.append(ChapelTest(**testdata))
                idfound = False
            if n.tagname == 'comment' and testid in n.rawsource:
                testdata = extracttestdata(n.rawsource)
                idfound = True
            elif n.children:
                nextlevel.extend(n.children)

        thislevel = nextlevel

    return tests


def main(docfile):
    """TODO: Docstring for main.
    :returns: tests # type: List[ChapelTest]

     - chapelexample (REQUIRED)
       If a filename is not given on the first line, the filename is
       generated from the input filename and the line number.

    """

    with open(docfile, 'r') as doc:
        doctext = doc.read()
    doctree = core.publish_doctree(doctext)

    tests = doctreetraverse(doctree)

    return tests


if __name__ == '__main__':
    args = getargs()
    main(args.reSTfile)
