#!/usr/bin/python
# -*- coding=utf-8 -*-

SOURCE_DIR = "./md"
SOURCE_EXT = ".md"
META_DB_DIR = "articles.csv"
MAIN_TEMPLATE = './template/main.html'
FRONT_TEMPLATE = './template/frontpage.html'
CONFIG_DIR = ".orca.conf"

CSV_DELIMITER = ';'

SOURCE_INDENTATION = 8

ORCA_CODE_PREFIX = '<!--ORCA:'

FORCE_GENERATE = False
GITHUB_UPDATE = True
DEBUG = False

from os import listdir, chdir
from os.path import getmtime, splitext
from ConfigParser import SafeConfigParser
import csv
import time
from time import gmtime, strftime
from subprocess import call

# Choose the text2html translator here and name the function render

import markdown2
render = lambda s: markdown2.markdown(s, extras=['wiki-tables'])

#import misaka
#render = misaka.html

def getHumanReadableTime(timeInSec):
    return timeInSec

def getAbsoluteTime(hTime):
    return hTime

def toSourceDir(dir):
    return SOURCE_DIR + '/' + dir

def extractTag(html, tag):
    htmlOriginal = html
    html = html.upper()
    tag = tag.upper()

    try:
        pos1 = html.index('<'+tag+'>') + len(tag) + 2
        pos2 = html.index('</'+tag+'>', pos1)

        return htmlOriginal[pos1:pos2]
    except ValueError:
        return ''

def extractTitle(html):
    res = extractTag(html, 'H1')
    res = res.replace('<br>', '')
    res = res.replace('<br/>', '')
    res = res.replace('<br />', '')
    return res

def extractSingleORCACode(html, code):
    signitureString = ORCA_CODE_PREFIX + code
    try:
        posStart = html.index(signitureString) + len(signitureString)
        posMark = html.index('=', posStart)
        posEnd = html.index('-->', posMark)
        return html[posMark+1:posEnd]
    except:
        return ''


def getCompileList():
    """
    Returns a dictionary, the keys are (names of) source files newer
    or older than their respective HTML files, the second is its
    modification time.
    """

    compile_list = dict()

    # Pair all .md files with its latest modification time
    for file in listdir(SOURCE_DIR):
        if file.endswith(SOURCE_EXT):
            fileDir = file
            compile_list[file] = getHumanReadableTime(
                                        getmtime(toSourceDir(fileDir)))

    # Retrieve meta info records
    previous_article_list = dict()

    with open(META_DB_DIR, 'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter=CSV_DELIMITER, quotechar='|')
        for row in reader:
            previous_article_list[row[0]] = float(row[1])

    # Update meta database
    with open(META_DB_DIR, 'wb') as csvfile:
        writer = csv.writer(csvfile, delimiter=CSV_DELIMITER,
                 quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for file in compile_list:
            writer.writerow([file, str(compile_list[file])])

    # Delete from compile_list which are older or of the same
    # modification time.
    for file in compile_list.keys():
        if file in previous_article_list.keys():
            if compile_list[file] >= previous_article_list[file]:

                if FORCE_GENERATE:
                    pass
                else:
                    del compile_list[file]

    return compile_list

def indent(s, n=0, newline=1):
    """
    Indent every line of s by n spaces.
    """

    end = '\n' * newline

    result = ''
    for line in s.splitlines():
        result += ' ' * (n + SOURCE_INDENTATION) + line + end

    return result

def compile(compile_list):

    """
    Call markdown2 to convert every .md file in the compile list to
    HTML files.
    """


    def beautify(mainHtml, template=''):

        def getORCAlabel(line):

            try:
                posStart = line.index('ORCA:LABEL=') + \
                           len('ORCA:LABEL=')
                posEnd = line.index('-->')
                tagSpecial = None
                tagSpecialQuality = None
            except ValueError:
                return ('', '', '')

            try:
                posMark = line.index('.', posStart, posEnd)
                tagSpecialQuality = line[posMark+1:posEnd]
                tagSpecial = 'class'
            except:
                pass

            try:
                posMark = line.index('#', posStart, posEnd)
                tagSpecialQuality = line[posMark+1:posEnd]
                tagSpecial = 'id'
            except:
                pass

            tag = line[posStart:posMark]

            return (tag, tagSpecial, tagSpecialQuality)

        # load template
        if not template:
            with open(MAIN_TEMPLATE, 'r') as f:
                template = f.read()
        result = template

        title = extractTitle(mainHtml)

        result = result.replace('<!--TITLETAG-->', title, 1)
        result = result.replace('<!--CONTENT-->',
                                indent(mainHtml),
                                1)

        # Deal with ORCA instructions
        for line in result.splitlines():
            if '<!--ORCA:' in line:
                lineOriginal = line[:]
                line = line.replace('<p>', '')
                line = line.replace('</p>', '')

                if 'ORCA:LABEL' in lineOriginal:
                    pos = line.index('-->')+len('-->')
                    line = line[pos:]

                    tag, tagSpecial, tagQuality = getORCAlabel(lineOriginal)
                    reformattedline = \
                            '<' + tag + ' ' + tagSpecial + '="' + \
                                tagQuality + '"' '>' +\
                            line +\
                            '</' + tag + '>'
                    reformattedline = indent(reformattedline)
                    result = result.replace(lineOriginal, reformattedline, 1)

        return result

    # Compile source files to the destination format
    for file in compile_list.keys():
        with open(toSourceDir(file)) as f:
            sourceContent = f.read().decode('utf-8')
            htmlFile = splitext(file)[0] + '.html'
            with open(htmlFile, 'w') as f:
                print "Converting %s" % file
                f.write(beautify(render(sourceContent)).encode('utf-8'))

    if not compile_list:
        print "Nothing to update."

def build_frontpage():

    """
    Build index.html from existing htmls,
          following the ORCA instructings lay down in the files.
    """

    print 'Building index.html'

    # Get meta info about existing HTMLs
    articles = []
    for file in listdir('.'):
        if splitext(file)[1] == '.html':
            with open(file, 'r') as f:
                html = f.read().decode('utf-8')
                articles.append((file,
                                 extractTitle(html),
                                 extractSingleORCACode(html, 'COLUMN'),
                                 extractSingleORCACode(html, 'PRIORITY'),
                                 getmtime(file)))


    content = ''
    for column in FRONTPAGE_COLUMN_ORDER.split(';'):
        content += indent('<div>' + '\n') +\
                   indent( '<h3>' + column + '</h3>' + '\n', 4) +\
                   indent('<ul>', 4)
        for art in articles:
            if (art[2] == column) and (art[3] > -1):
                content += indent('<li>', 8, newline=0)
                content += '<a href="'
                content += art[0]
                content += '">'
                content += art[1]
                content += '</a></li>\n'

        content += indent('</ul>', 4)
        content += indent('</div>', 0, newline=2)

    with open(FRONT_TEMPLATE, 'r') as f:
        frontHTML = f.read().decode('utf-8')
        frontHTML = frontHTML.replace('<!--CONTENT-->', content)
        with open('index.html', 'w') as f_index:
            f_index.write(frontHTML.encode('utf-8'))

def build_archive():
    pass

def updateGithub(compile_list):
    if not GITHUB_UPDATE:
        return
    if compile_list:
        print 'Updating git respository'
        call(['git', 'add', '.'])
        commit_message = ';'.join(compile_list.keys())
        call(['git', 'commit', '-m', commit_message])
        call(['git', 'push'])


if __name__ == '__main__':

    config = SafeConfigParser()
    config.read(CONFIG_DIR)
    FRONTPAGE_COLUMN_ORDER = config.get('Frontpage', 'Column_Order')

    chdir('../')
    compile_list = getCompileList()
    compile(compile_list)
    build_frontpage()
    build_archive()

    updateGithub(compile_list)
