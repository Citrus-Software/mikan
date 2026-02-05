# coding: utf-8


ascii_title = r'''
        .__ __
  _____ |__|  | _______    ____        {}
 /     \|  |  |/ /\__  \  /    \       7- ]
|  Y Y  \  |    <  / __ \|   |  \    /   |
|__|_|  /__|__|_ \(____  /___|  /    \2 uu
      \/        \/     \/     \/
'''

try:
    unicode
except:
    unicode = str

ascii_title = unicode(ascii_title).format(u'🍊')
