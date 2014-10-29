# -*- coding=utf-8 -*-
# TODO: Build archive
# TODO: Use folder to specify column and order of column
# TODO: Article ordering that works as expected
# TODO: Option of just updating, without re-compiling

__author__ = "Andy Shu Xin"
__copyright__ = "Copyright (C) 2014 Andy Shu Xin"
__license__ = "GNU General Public License v3.0"

SOURCE_DIR = "./md"
SOURCE_EXT = ".md"
META_DB_DIR = "articles.csv"
MAIN_TEMPLATE = './template/main.html'
FRONT_TEMPLATE = './template/frontpage.html'
CONFIG_DIR = ".orca.conf"

CSV_DELIMITER = ';'

PREFERRED_INDENTATION = 8

ORCA_CODE_PREFIX = '<!--ORCA:'

from os import listdir, chdir, getcwd
from os.path import getmtime, splitext
from configparser import ConfigParser
import csv
from subprocess import call

# Modify md2html if switching to new markdown render engine
import markdown2
md2html = lambda s: markdown2.markdown(s, extras=['wiki-tables'])


def get_path_under_source_dir(path):
    return SOURCE_DIR + '/' + path


def get_tag_content(html, tag):
    htmlOriginal = html
    html = html.upper()
    tag = tag.upper()

    try:
        pos1 = html.index('<'+tag+'>') + len(tag) + 2
        pos2 = html.index('</'+tag+'>', pos1)

        return htmlOriginal[pos1:pos2]

    except ValueError:
        return ''


def get_html_title(html):
    res = get_tag_content(html, 'H1')
    for newline_tag in ('<br>', '<br/>', '<br />'):
        res = res.replace(newline_tag, '')
    return res


def get_single_ORCA_code(html, code):
    signiture_string = ORCA_CODE_PREFIX + code
    try:
        posStart = html.index(signiture_string) + len(signiture_string)
        posMark = html.index('=', posStart)
        posEnd = html.index('-->', posMark)
        return html[posMark+1:posEnd]
    except ValueError:
        return ''


def get_source_list():
    """
    Returns a dictionary, the keys are (names of) source files newer
    or older than their respective HTML files, the second is its
    modification time.
    """

    source_list = dict()

    # Pair all source files with its latest modification time
    for file in listdir(SOURCE_DIR):
        if file.endswith(SOURCE_EXT):
            fileDir = file
            source_list[file] = getmtime(get_path_under_source_dir(fileDir))

    # Retrieve records of last time's source list
    previous_source_list = dict()
    try:
        with open(META_DB_DIR, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=CSV_DELIMITER, quotechar='|')
            for row in reader:
                previous_source_list[row[0]] = float(row[1])
    except IOError: # Previous record not found
        pass

    # Update source list record
    with open(META_DB_DIR, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=CSV_DELIMITER,
                            quotechar='|', quoting=csv.QUOTE_MINIMAL)
        for file in source_list:
            writer.writerow([file, str(source_list[file])])

    # Delete from source_list which are older or of the same
    # modification time.
    for file in list(source_list.keys()):
        if file in list(previous_source_list.keys()):
            if source_list[file] <= previous_source_list[file]:
                del source_list[file]

    return source_list


def indent(s, n=0, newline=1):
    """
    Return a string, which is putting n spaces in front of every line of s.
    Used in html construction.
    """

    END = '\n' * newline

    result = ''
    for line in s.splitlines():
        result += ' ' * (n + PREFERRED_INDENTATION) + line + END

    return result


def build_html(compile_list):
    """
    Call markdown2 to convert every .md file in the compile list to
    HTML files.
    """

    def beautify(mainHtml, template=''):

        def getORCAlabel(line):

            try:
                posStart = line.index('ORCA:LABEL=') + len('ORCA:LABEL=')
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

        # Load template
        if not template:
            with open(MAIN_TEMPLATE, 'r') as f:
                template = f.read()
        result = template

        title = get_html_title(mainHtml)

        result = result.replace('<!--TITLETAG-->', title, 1)
        result = result.replace('<!--CONTENT-->',
                                indent(mainHtml),
                                1)

        # Execute ORCA instructions

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
                                tagQuality + '"' '>' + \
                            line + \
                            '</' + tag + '>'
                    reformattedline = indent(reformattedline)
                    result = result.replace(lineOriginal, reformattedline, 1)

        return result

    # Compile source files to the destination format
    for file in list(compile_list.keys()):
        with open(get_path_under_source_dir(file)) as f:
            sourceContent = f.read()
            htmlFile = splitext(file)[0] + '.html'
            with open(htmlFile, 'w') as f:
                print(("Converting %s" % file))
                f.write(beautify(md2html(sourceContent)))

    if not compile_list:
        print("Nothing to update.\n")


def build_frontpage():

    """
    Build index.html from existing htmls,
          following the ORCA instructions lay down in the files.
    """

    print('\nBuilding index.html')

    # Get meta info about existing HTMLs
    articles = []
    for file in listdir('.'):
        if splitext(file)[1] == '.html':
            with open(file, 'r') as f:
                html = f.read()

                if get_single_ORCA_code(html, 'FP_TITLE'):
                    title = get_single_ORCA_code(html, 'FP_TITLE')
                else:
                    title = get_html_title(html)

                articles.append({'filename':
                                 file,
                                 'title':
                                 title,
                                 'COLUMN':
                                 get_single_ORCA_code(html, 'COLUMN'),
                                 'PRIORITY':
                                 get_single_ORCA_code(html, 'PRIORITY'),
                                 'mtime':
                                 getmtime(file)})


    # Build html file
    content = ''
    for column in FRONTPAGE_COLUMN_ORDER.split(';'):
        content += indent('<div>' + '\n') +\
                   indent( '<h3>' + column + '</h3>' + '\n', 4) +\
                   indent('<ul>', 4)

        for art in articles:

            if art['PRIORITY'] == '-1':
                continue

            if art['COLUMN'] == column:
                content += indent('<li>', 8, newline=0)
                content += '<a href="'
                content += art['filename']
                content += '">'
                content += art['title']
                content += '</a></li>\n'

        content += indent('</ul>', 4)
        content += indent('</div>', 0, newline=2)

    with open(FRONT_TEMPLATE, 'r') as f:
        frontpage_HTML = f.read()
        frontpage_HTML = frontpage_HTML.replace('<!--CONTENT-->', content)
        with open('index.html', 'w') as f_index:
            f_index.write(frontpage_HTML)


def build_archive():
    #TODO
    pass


def updateGithub(compile_list):
    if compile_list:
        print('\nUpdating git respository\n')
        call(['git', 'add', '--all', '.'])
        commit_message = ';'.join(list(compile_list.keys()))
        call(['git', 'commit', '-m', commit_message])
        call(['git', 'push'])


if __name__ == '__main__':

    if getcwd()[-4:] == 'orca':
        chdir('..')

    config = ConfigParser()
    config.read(CONFIG_DIR)
    FRONTPAGE_COLUMN_ORDER = config.get('Frontpage', 'Column_Order')

    source_list = get_source_list()
    build_html(source_list)
    build_frontpage()
    build_archive()

    if source_list:
        updateGithub(source_list)
        try:
            import updateServer
            updateServer.sshUpdate()
            print("Server updated.\n")
        except ImportError:
            print("Server sync module found.\n")
    else:
        print("No modification since last server update.")

    print("*** Orca sleeps now ***\n")
