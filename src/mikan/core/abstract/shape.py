# coding: utf-8

import os
import re
import colorsys
import math

from mikan.core.utils.yamlutils import ordered_load

import mikan.templates.shapes

__all__ = ['Shape']


class Shape(object):
    shapes = {}

    @staticmethod
    def load_shapes_from_path(path=mikan.templates.shapes.__path__[0]):
        for f in os.listdir(path):
            if f.endswith('.yml'):
                p = os.path.join(path, f)
                with open(p, "r") as stream:
                    Shape.shapes[f[:-4]] = ordered_load(stream)

    color_names = dict(
        aliceblue='#f0f8ff', antiquewhite='#faebd7', aqua='#00ffff', aquamarine='#7fffd4',
        azure='#f0ffff', beige='#f5f5dc', bisque='#ffe4c4', black='#000000',
        blanchedalmond='#ffebcd', blue='#0000ff', blueviolet='#8a2be2', brown='#a52a2a',
        burlywood='#deb887', cadetblue='#5f9ea0', chartreuse='#7fff00', chocolate='#d2691e',
        coral='#ff7f50', cornflowerblue='#6495ed', cornsilk='#fff8dc', crimson='#dc143c',
        cyan='#00ffff', darkblue='#00008b', darkcyan='#008b8b', darkgoldenrod='#b8860b',
        darkgray='#a9a9a9', darkgrey='#a9a9a9', darkgreen='#006400', darkkhaki='#bdb76b',
        darkmagenta='#8b008b', darkolivegreen='#556b2f', darkorange='#ff8c00', darkorchid='#9932cc',
        darkred='#8b0000', darksalmon='#e9967a', darkseagreen='#8fbc8f', darkslateblue='#483d8b',
        darkslategray='#2f4f4f', darkslategrey='#2f4f4f', darkturquoise='#00ced1', darkviolet='#9400d3',
        deeppink='#ff1493', deepskyblue='#00bfff', dimgray='#696969', dimgrey='#696969',
        dodgerblue='#1e90ff', firebrick='#b22222', floralwhite='#fffaf0', forestgreen='#228b22',
        fuchsia='#ff00ff', gainsboro='#dcdcdc', ghostwhite='#f8f8ff', gold='#ffd700',
        goldenrod='#daa520', gray='#808080', grey='#808080', green='#008000',
        greenyellow='#adff2f', honeydew='#f0fff0', hotpink='#ff69b4', indianred='#cd5c5c',
        indigo='#4b0082', ivory='#fffff0', khaki='#f0e68c', lavender='#e6e6fa',
        lavenderblush='#fff0f5', lawngreen='#7cfc00', lemonchiffon='#fffacd', lightblue='#add8e6',
        lightcoral='#f08080', lightcyan='#e0ffff', lightgoldenrodyellow='#fafad2', lightgray='#d3d3d3',
        lightgrey='#d3d3d3', lightgreen='#90ee90', lightpink='#ffb6c1', lightsalmon='#ffa07a',
        lightseagreen='#20b2aa', lightskyblue='#87cefa', lightslategray='#778899', lightslategrey='#778899',
        lightsteelblue='#b0c4de', lightyellow='#ffffe0', lime='#00ff00', limegreen='#32cd32',
        linen='#faf0e6', magenta='#ff00ff', maroon='#800000', mediumaquamarine='#66cdaa',
        mediumblue='#0000cd', mediumorchid='#ba55d3', mediumpurple='#9370db', mediumseagreen='#3cb371',
        mediumslateblue='#7b68ee', mediumspringgreen='#00fa9a', mediumturquoise='#48d1cc', mediumvioletred='#c71585',
        midnightblue='#191970', mintcream='#f5fffa', mistyrose='#ffe4e1', moccasin='#ffe4b5',
        navajowhite='#ffdead', navy='#000080', oldlace='#fdf5e6', olive='#808000',
        olivedrab='#6b8e23', orange='#ffa500', orangered='#ff4500', orchid='#da70d6',
        palegoldenrod='#eee8aa', palegreen='#98fb98', paleturquoise='#afeeee', palevioletred='#db7093',
        papayawhip='#ffefd5', peachpuff='#ffdab9', peru='#cd853f', pink='#ffc0cb',
        plum='#dda0dd', powderblue='#b0e0e6', purple='#800080', red='#ff0000',
        rosybrown='#bc8f8f', royalblue='#4169e1', saddlebrown='#8b4513', salmon='#fa8072',
        sandybrown='#f4a460', seagreen='#2e8b57', seashell='#fff5ee', sienna='#a0522d',
        silver='#c0c0c0', skyblue='#87ceeb', slateblue='#6a5acd', slategray='#708090',
        slategrey='#708090', snow='#fffafa', springgreen='#00ff7f', steelblue='#4682b4',
        tan='#d2b48c', teal='#008080', thistle='#d8bfd8', tomato='#ff6347',
        turquoise='#40e0d0', violet='#ee82ee', wheat='#f5deb3', white='#ffffff',
        whitesmoke='#f5f5f5', yellow='#ffff00', yellowgreen='#9acd32'
    )

    maya_color_list = [
        (0.5, 0.5, 0.5), (0.0, 0.0, 0.0), (0.25, 0.25, 0.25), (0.5, 0.5, 0.5),
        (0.6, 0.0, 0.16), (0.0, 0.0, 0.38), (0.0, 0.0, 1.0), (0.0, 0.275, 0.1),
        (0.15, 0.0, 0.26), (0.8, 0.0, 0.8), (0.54, 0.28, 0.2), (0.25, 0.14, 0.12),
        (0.6, 0.15, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.25, 0.6),
        (1.0, 1.0, 1.0), (1.0, 1.0, 0.0), (0.4, 0.9, 1.0), (0.26, 1.0, 0.64),
        (1.0, 0.7, 0.7), (0.9, 0.675, 0.5), (1.0, 1.0, 0.4), (0.0, 0.6, 0.3),
        (0.6, 0.4, 0.2), (0.6, 0.6, 0.2), (0.4, 0.6, 0.2), (0.2, 0.6, 0.4),
        (0.2, 0.6, 0.6), (0.2, 0.4, 0.6), (0.4, 0.2, 0.6), (0.6, 0.2, 0.4)
    ]

    @staticmethod
    def hex_to_rgb(hex_value):
        """
        Convert a hexadecimal color value to a 3-tuple of integers
        suitable for use in an ``rgb()`` triplet specifying that color.
        """
        re_hex_color = re.compile(r'^#([a-fA-F0-9]{3}|[a-fA-F0-9]{6})$')
        match = re_hex_color.match(hex_value)
        if match is None:
            raise ValueError(
                u"'{}' is not a valid hexadecimal color value.".format(hex_value)
            )
        hex_digits = match.group(1)
        if len(hex_digits) == 3:
            hex_digits = u''.join(2 * s for s in hex_digits)

        hex_value = u'#{}'.format(hex_digits.lower())

        hex_value = int(hex_value[1:], 16)
        return (
            (hex_value >> 16) / 256.,
            (hex_value >> 8 & 0xff) / 256.,
            (hex_value & 0xff) / 256.
        )

    @staticmethod
    def rgb_to_hex(rgb):
        """
        convert a 3-tuple of integers color triplet, to a normalized hexadecimal value for that color.
        """
        rgb = map(lambda v: int(v * 255), rgb)
        return '#{:02x}{:02x}{:02x}'.format(*rgb)

    @staticmethod
    def color_to_rgb(color):
        if color in Shape.color_names:
            color = Shape.color_names[color]
        rgb = Shape.hex_to_rgb(color)
        return rgb

    @staticmethod
    def rgb_to_srgb(color):
        return [pow(c if c > 0 else 0, 0.4545) for c in color]

    @staticmethod
    def srgb_to_rgb(color):
        return [pow(c, 2.2) for c in color]

    @staticmethod
    def color_to_id(color):
        if color in Shape.color_names:
            color = Shape.color_names[color]
        rgb = Shape.hex_to_rgb(color)
        return Shape.closest_color_id(rgb)

    @staticmethod
    def closest_color_id(rgb_in):
        min_colors = {}
        for i, rgb in enumerate(Shape.maya_color_list):
            rd = (rgb[0] - rgb_in[0]) ** 2
            gd = (rgb[1] - rgb_in[1]) ** 2
            bd = (rgb[2] - rgb_in[2]) ** 2
            min_colors[(rd + gd + bd)] = i
        return min_colors[min(list(min_colors))]

    @staticmethod
    def get_color_flip(rgb, direction=1):
        direction = -float(direction)
        hsv = list(colorsys.rgb_to_hsv(*rgb))
        hsv[0] = (hsv[0] + 0.333333 * direction) % 1
        rgb = list(colorsys.hsv_to_rgb(*hsv))
        return rgb

    @staticmethod
    def color_step(r, g, b, repetitions=1):
        lum = math.sqrt(.241 * r + .691 * g + .068 * b)

        h, s, v = colorsys.rgb_to_hsv(r, g, b)

        h2 = int(h * repetitions)
        lum2 = int(lum * repetitions)
        v2 = int(v * repetitions)

        if h2 % 2 == 1:
            v2 = repetitions - v2
            lum = repetitions - lum

        return h2, lum, v2

    @staticmethod
    def color_step_hex(hex_value, repetitions=1):
        r, g, b = Shape.hex_to_rgb(hex_value)
        return Shape.color_step(r, g, b, repetitions)


Shape.load_shapes_from_path()
