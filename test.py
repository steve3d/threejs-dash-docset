#!/usr/bin/env python3
import re

content = "<h3>[method:Object getAttributes]()</h3>"

name = 'hehe';

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

print(content_new)