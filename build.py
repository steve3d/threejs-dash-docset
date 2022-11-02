#!/usr/bin/env python3

import argparse
import os
import os.path as path
import sys
import subprocess
import re
import shutil
import dirtyjson
import sqlite3
import glob




class Builder:
    def __init__(self, lang, version):
        self.lang = lang
        self.version = version
        self.cwd = os.getcwd()
        self.src = path.join(self.cwd, 'three.js')

    def _checkout(self):
        if self.version == 'latest':
            tags = subprocess.check_output(['git', 'tag']).decode('utf-8').split("\n")
            tags.sort(key = lambda x: int(x[1:]) if re.match(r"^\d+$", x[1:]) else 0)
            self.version = tags[-1]

        subprocess.run(['git', 'checkout', self.version])

    def _buildSource(self):
        subprocess.run(['npm', 'i'])
        subprocess.run(['npm', 'run', 'build'])

    def _copy(self):
        output = path.join(self.cwd, 'output')
        if path.isdir(output):
            shutil.rmtree(output)
        os.mkdir(output)
        shutil.copytree(path.join(self.src, 'build'), path.join(output, 'build'))
        shutil.copytree(path.join(self.src, 'docs'), path.join(output, 'docs'))
        shutil.copytree(path.join(self.src, 'files'), path.join(output, 'files'))
        shutil.copytree(path.join(self.src, 'examples'), path.join(output, 'examples'))
        with open(path.join(output, 'docs', 'page.css'), 'a', encoding='utf-8') as page, open(path.join(self.cwd, 'assets', 'page-add.css'), 'r', encoding='utf-8') as add:
            page.write(add.read())
        
        if self.lang == 'en':
            removeLang = 'zh'
        else:
            removeLang = 'en'
        for name in ['api', 'examples', 'manual']:
            shutil.rmtree(path.join(output, 'docs', name, removeLang))

    def _parse(self):
        # now use list.json instead
        with open(path.join(self.cwd, 'output', 'docs', 'list.json'), encoding='utf-8') as f:
            pages = f.read()      

        self.items = dirtyjson.loads(pages)[self.lang]

    def _index(self):
        os.chdir(self.cwd)
        if path.isdir('threejs.docset'):
            shutil.rmtree('threejs.docset')
        
        os.makedirs(path.join('threejs.docset', 'Contents', 'Resources'))
        conn = sqlite3.connect(path.join('threejs.docset', 'Contents', 'Resources', 'docSet.dsidx'))
        c = conn.cursor()
        c.execute('''CREATE TABLE searchIndex(id INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT)''')
        c.execute('''CREATE UNIQUE INDEX anchor ON searchIndex (name, type, path)''')
        self._index_group(self.items['Manual'], 'Guide', c)
        self._index_group(self.items['Developer Reference'], 'Guide', c)
        self._index_group(self.items['Examples'], 'Class', c)
        self._index_group(self.items['Reference'], 'Class', c)
        self._index_examples(c)

        conn.commit()
        conn.close()

        with open(path.join(self.cwd, 'output', 'docs', 'page.js'), 'r+', encoding='utf-8') as f:
            content = f.read().replace(r"pathname.substring( 0, pathname.indexOf( 'docs' ) + 4 ) + '/prettify", "'prettify")
            content = content.replace('../examples/#$1', '../examples/$1.html')
            content = content.replace('window.location.replace(','// window.location.replace(') # prevent loading crash fixme: need a better fix
            f.seek(0, 0)
            f.truncate()
            f.write(content)

        shutil.copy2(path.join(self.cwd, 'assets', 'icon.png'), path.join(self.cwd, 'threejs.docset'))
        shutil.copy2(path.join(self.cwd, 'assets', 'icon@2x.png'), path.join(self.cwd, 'threejs.docset'))
        shutil.copy2(path.join(self.cwd, 'assets', 'info.plist'), path.join(self.cwd, 'threejs.docset', 'Contents'))
        shutil.move(path.join(self.cwd, 'output'), path.join('threejs.docset', 'Contents', 'Resources', 'Documents'))

    def _index_examples(self, cursor):
        items = []
        for item in glob.glob(path.join(self.cwd, 'output', 'examples', '*.html')):
            filename = path.basename(item)
            items.append((filename.replace('.html', ''), 'Sample', 'examples/' + filename))

        cursor.executemany("INSERT INTO searchIndex(name, type, path) VALUES (?, ?, ?)", items)

    def _gen_api_toc(self):
        for item in glob.glob(path.join('threejs.docset', 'Contents', 'Resources', 'Documents', 'docs/api/en/**/*.html')): #'docs/api/en/**/**/*.html')):
            print('gen toc for:'+item)
            with open(item, 'r+', encoding='utf-8') as f:
                filename = path.basename(item) 
                name = filename.replace('.html', '')

                content = f.read()

                # toc
                def repl_toc_fn(matchobj):
                    # g0 = matchobj.group(0)
                    (g1,g2,g3,g0) = matchobj.group(2,3,4,1)
                    # g1 返回值
                    # g2 名称
                    # g3 类型
                    if g1 is None:
                        g1 = ''
                    if g2 is None:
                        g2 = ''
                    if g3 is None:
                        g3 = ''
                    if g0 is None:
                        g0 = ''
                    else:
                        # uppercase g0's first letter
                        g0 = g0[0].upper() + g0[1:]
                    # g2 = matchobj.group(2)
                    # print(g0,g1,g2,g3)
                    # return g1+g2+g3
                    return '<a onclick="window.parent.setUrlFragment(\'' + name + '.'+g2+'\')" target="_parent" title="' + name + '.'+g2+'" class="permalink">#</a> .<a onclick="window.parent.setUrlFragment(\'' + name + '.'+g2+'\')" id="'+g2+'">'+g2+'</a> '+g3+' : <a name="//apple_ref/cpp/'+g0+'/'+g2+'" class="param dashAnchor" onclick="window.parent.setUrlFragment(\''+g1+'\')">'+g1+'</a>'

                content_new = re.sub(r"\[(member|property|method):([\w]+) ([\w\.\s]+)\]\s*(\(.*\))?", repl_toc_fn, content, flags=re.M)
                
                f.seek(0, 0)
                f.truncate()
                f.write(content_new)
                # print(content_new)
        

    def _index_group(self, groups, type, cursor):
        items = []
        for group in groups.items():
            for item in group[1].items():
                items.append((item[0], type, 'docs/' + item[1] + '.html'))
                # items.append((item[0], type, 'https://threejs.org/docs/' + item[1] + '.html'))

        cursor.executemany("INSERT INTO searchIndex(name, type, path) VALUES (?, ?, ?)", items)

    def build(self):
        os.chdir(self.src)
        self._checkout()
        self._buildSource()
        self._copy()
        self._parse()
        self._index()
        # generate TOC
        self._gen_api_toc()
        # debug sqlite
        # shutil.copy2(path.join(self.cwd, 'threejs.docset/Contents/Resources/docSet.dsidx'), path.join(self.cwd, 'threejs.docset/Contents/Resources/docSet.db'))
        print('Build documents for version: ' + self.version)
        pass



if __name__ == '__main__':
    basedir = path.dirname(sys.argv[0])
    if basedir != os.getcwd() and basedir != '':
        os.chdir(basedir)
    
    if not path.isdir('three.js'):
        print('Please clone three.js from https://github.com/mrdoob/three.js first.')
        exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--language', help='Build three.js doc with specified language',
        default='en', type=str, choices=['en', 'zh'])

    parser.add_argument('-v', '--version', help='Build specific version of three.js documents',
        default='latest', type=str)

    args = parser.parse_args()

    builder = Builder(args.language, args.version)
    builder.build()
    