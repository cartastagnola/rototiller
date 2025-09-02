#!/usr/bin/env python3

for i in range(10):
    print(i)

print("ads")
for i in range(-10, 0):
    print(i)

import sys,os
import curses
from pathlib import Path

sys.path.append('/home/boon/gitRepos/pyfiglet/')
sys.path.append('/home/boon/gitRepos/pyfiglet/pyfiglet/')
#from pyfiglet import Figlet
import pyfiglet

custom_fonts_path = "/home/boon/gitRepos/pyfiglet/pyfiglet/fonts-standard"

fonts = []
for font in Path(custom_fonts_path).glob("*"):
    fonts.append(font.stem)

fonts.sort()

possibleFont = ['cyberlarge', 'cybersmall', 'chunky', 'contessa', 'cosmike', 'doh', 'linux', 'rectangles']
possibleFont = ['mono9', 'cybersmall', 'future', 'smmono9', 'doom', 'ogre', 'smblock', 'pagga', 'emboss', 'bigchief', 'bigfig', 'bigascii9', 'bigascii12' ]

# load all fig
directory_path = custom_fonts_path
files = os.listdir(directory_path)
# Remove extensions
stripped_names = [os.path.splitext(file)[0] for file in files if os.path.isfile(os.path.join(directory_path, file))]
possibleFont = sorted(stripped_names)

possibleFont = ['starwars', 'standard', 'smblock', 'small', 'pagga', 'dos_rebel', 'chunky', 'big', 'doom']
fonts = possibleFont

def load_custom_fonts(path):
    """Load custom fonts from the specified directory."""
    fonts = pyfiglet.Figlet(fonts_dir=path)
    return fonts

# for pyfiglet
def print_text_with_custom_font(fonts, text):
    """Print text using a custom font."""
    # You can specify the font name when creating the Figlet instance.
    custom_font = fonts.get_font_by_name("custom-font")

    if custom_font:
        result = custom_font.renderText(text)
        print(result)
    else:
        print(f"Custom font 'custom-font' not found.")

class Font:
    def __init__(self):
        self.fChars = {} # ASCII code; figlet chars hashtable
        self.hardBlank = 0
        self.height = 0
        self.baseLine = 0
        self.maxLength = 0
        self.oldLayout = 0
        self.commentLines = 0
        self.printDirection = 0
        self.smushMode = 0

class FChar:
    """Struct for the figlet char
    chars: array of string
    width: the width in chars"""
    def __init__(self):
        self.chars = ''  # string of array for every line of the char
        self.width = 0  # width of the char
        self.smushLeft = []  # array of len, of the height of the char
        self.smushRight = []  # array of len, of the height of the char
        #then doing the subtraciont between the right of one char and the left of the other
        #i can calculate the smush

# forse il FONT non serve e basta un hastavble
# coinciare a costruire il font

def lastNonSpaceChar(string):
    i = len(string) - 1
    while i > 0:
        char = string[i]
        if char != ' ' and char != '\n':
           return i
        i -= 1
    return i

def firstNonSpaceChar(string):
    i = 0
    while i < len(string):
        char = string[i]
        if char != ' ' and char != '\n':
           return i
        i += 1
    return i

txt = 'asdf  awef aweg aqjkl  '
a = lastNonSpaceChar(txt)
print('_____')
print(a)
print(txt[a])
txt = '     '
a = lastNonSpaceChar(txt)
print('______')
print(a)
print(txt[a])
txt = 'i     '
a = lastNonSpaceChar(txt)
print('______')
print(a)
print(txt[a])
txt = '    q'
a = lastNonSpaceChar(txt)
print('______')
print(a)
print(txt[a])
txt = '    q'
a = firstNonSpaceChar(txt)
print('__first____')
print(a)
print(txt[a])
txt = '1   q'
a = firstNonSpaceChar(txt)
print('__first____')
print(a)
print(txt[a])
txt = ' d  q'
a = firstNonSpaceChar(txt)
print('__first____')
print(a)
print(txt[a])


def loadFontFTL(filePath, font):
    with open(filePath, 'r') as file:
        # read the header
        lines = file.readlines()
        print(lines[0])
        header = lines.pop(0)[5:-1].split(' ')
        print(header)
        font.hardBlank = header[0]
        font.height = int(header[1])
        font.baseLine = int(header[2])
        font.maxLength = int(header[3])
        font.oldLayout = int(header[4])
        font.commentLines = int(header[5])
        font.smushMode = int(header[4])  # for doom, this is the smush value...
        commentLines = font.commentLines
        while commentLines > 0:
            lines.pop(0)
            commentLines -= 1

        # parse ascii chars
        asciiIdx = 32
        fChar = FChar()
        smushLeft = []
        smushRight = []
        while asciiIdx < 127:
            line = lines.pop(0)
            lstIdx = lastNonSpaceChar(line)
            if line[lstIdx] == line[lstIdx - 1]:
                lstIdx -= 1
                charLine = line[0:lstIdx]

                #substitute the hardblank
                clean_charLine = ''
                for i in charLine:
                    if i == font.hardBlank:
                        clean_charLine += ' '
                    else:
                        clean_charLine += i
                fChar.chars += clean_charLine
                fChar.width = lstIdx

                # smush stuffs
                smushLeft.append(firstNonSpaceChar(charLine))
                smushRight.append(lstIdx - lastNonSpaceChar(charLine))
                fChar.smushLeft = smushLeft
                fChar.smushRight = smushRight

                # store the font
                font.fChars[asciiIdx] = fChar

                #print(asciiIdx, " ascii")
                #print(fChar.chars)

                fChar = FChar()
                smushLeft = []
                smushRight = []
                asciiIdx += 1

            else:
                charLine = line[0:lstIdx]
                smushLeft.append(firstNonSpaceChar(charLine))
                smushRight.append(lstIdx - lastNonSpaceChar(charLine))

                #substitute the hardblank
                clean_charLine = ''
                for i in charLine:
                    if i == font.hardBlank:
                        clean_charLine += ' '
                    else:
                        clean_charLine += i
                fChar.chars += clean_charLine


def sizeText(text, font: Font):
    "return the size of the text using a figlet font"
    y = font.height
    x = 0
    for c in text:
        x += font.fChars[ord(c)].width
    return x, y


def renderFont(text, font):
    strings = [''] * font.height
    prev_char = ' '
    smushMode = True if font.smushMode > 0 else False
    for i in text:
        fChar = font.fChars[ord(i)]
        begin = 0
        end = fChar.width

        # calculate the smush betweeb this and the previous char
        smushList = []
        smush = 0
        if smushMode:
            prev_fChar = font.fChars[ord(prev_char)]
            if not i == ' ':
                for l, r in zip(prev_fChar.smushRight, fChar.smushLeft):
                    smushList.append(l+r)
                smush = min(smushList) * -1
                #print(f"smush between {prev_char} and {i} is smush {smush}")
            else:
                smush = -1

        # draw the chars
        for s in range(font.height):
            if smushMode:
            #if False:
                newLine = fChar.chars[begin:end]
                if prev_char == ' ' or i == ' ':
                    if i == ' ':
                        chars = fChar.chars[begin:end]
                        strings[s] += ' ' * len(chars)
                        pass
                    else:
                        strings[s] += fChar.chars[begin:end]

                #if i != ' ' and prev_char != ' ':
                else:
                    if i == ' ':
                        print('char', i)
                        print(fChar.smushLeft)
                        print(fChar.smushRight)
                        print(smush)
                    if smush == 0:
                        print('charrrr')
                        print(i)
                        print(smush)
                    left_chars = ''
                    right_chars = newLine[:smush*-1]
                    remaining_right_chars = newLine[smush*-1:]
                    left_chars = strings[s][smush:]
                    strings[s] = strings[s][:smush]
                    for l, r in zip(left_chars, right_chars):
                        if l == ' ':
                            strings[s] += r
                        else:
                            strings[s] += l
                    strings[s] += remaining_right_chars

               # else:
               #     strings[s] += fChar.chars[begin:end]
            else:
                strings[s] += fChar.chars[begin:end]
            begin = end
            end = begin + fChar.width
        prev_char = i
    return strings



ffont = Font()
pathA = Path("/home/boon/gitRepos/pyfiglet/pyfiglet/fonts-standard/doom.flf")
loadFontFTL(pathA, ffont)
print('two')
s = renderFont('  rototiller', ffont)
print(s)
for i in s:
    print(i)
print('two done')

ffont = Font()
pathA = Path("/home/boon/gitRepos/pyfiglet/pyfiglet/fonts-standard/doom.flf")
loadFontFTL(pathA, ffont)
print('two')
s = renderFont('toto roto -:; - : ;  tiiiller', ffont)
for i in s:
    print(i)
print('two done')

ffont = Font()
pathA = Path("/home/boon/gitRepos/pyfiglet/pyfiglet/fonts-standard/future.tlf")
loadFontFTL(pathA, ffont)
print('one')
s = renderFont('toto MOro   rototiller poto', ffont)
for i in s:
    print(i)


f = pyfiglet.Figlet(font=fonts[5], width=100)
print(f.renderText('rototiller'))
print(f.renderText('rototiiiller piller    giller'))
print(f.renderText('r o   t o t i l l e r'))
print(f.renderText('it ri ir rs sr il ii ih ik      io'))

#
#
#
#
#            pass
#
#    except FileNotFoundError:
#        print(f"File not found at {filePath}.")
#    except Exception as e:
#        print(f"An error occured: {str(e)}")

# Load custom fonts from the specified path
#fonts = load_custom_fonts(custom_fonts_path)

# Use a custom font to generate and print text
#print_text_with_custom_font(fonts, "Hello, PyFiglet!")
#
#

f = pyfiglet.Figlet(font=possibleFont[2], width=130)
print(f.renderText('chia'))
#for fn in possibleFont:
#    f = pyfiglet.Figlet(font=fn, width=130)
#    print(f.renderText('chia wallet'))
#    print(f.renderText('Chia Wallet'))
#

#f = pyfiglet.Figlet(font='slant', width=130)
#print(f.renderText('text to render'))
#print(f.renderText('t e x t  t o  r e n d e r'))
print("end")
print("""                      .'''''              `;ll;`
                      :lllll'            .llllll.
                      :lllll'             `;ll;`
         ..''''''..   :lllll' .'''''.                  .....
      ',IllllllllllI  :lllll:Illlllll:'   ",,,,,.   .^;lllllI,"lllllI
    .;lllllll:"^^",;  :llllllllllllllll'  ;lllll.  `llllllllllllllllI
   .Illlll:'          `,llll;`..';lllll,  ;lllll. `lllllI^'.'^IlllllI
   `lllll:.'```'..      ^lll`    'lllll,  ;lllll. ;lllll'     `lllllI
   "lllll:`'.         ',llll'    'lllll,  ;lllll. llllll      'lllllI
   ,lllll,          ':llllll'    'lllll,  ;lllll. :lllll`     `lllllI
 .'.:lllllI"`''''^,lllllllll'    'lllll,  ;lllll. .Illlll,```,lllllll
     ^Illllllllllllll;;lllll'    'lllll,  ;lllll.  .:lllllllllIllllll.
       '^,IlllllI:"`. ^:::::'    ':::::"  ;lllll.    '":llll:^.":::::^
            ..                                                        """)


def menu(stdscr):
    key = 0

    stdscr.clear()
    stdscr.refresh()

    # Start colors in curses
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)

    ff = 0
#    f = pyfiglet.Figlet(font=fonts[0], width=130)


    while key != ord('q'):
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        if key == ord('a'):
            ff += 1
            ff = ff % len(fonts)
            try:
                f = pyfiglet.Figlet(font=fonts[ff], width=130)
            except:
                pass
        if key == ord('h'):
            ff -= 1
            ff = ff % len(fonts)
            try:
                f = pyfiglet.Figlet(font=fonts[ff], width=130)
            except:
                pass


        # Turning on attributes for title
        stdscr.attron(curses.color_pair(1))
        stdscr.attron(curses.A_BOLD)

        # Rendering title
        try:
            #stdscr.addstr(5, 0, f.renderText("1 - Wallet w W a l l e t hdd analytics "))
            stdscr.addstr(5, 0, f.renderText("Peak: 4_456_456 "))
            #stdscr.addstr(10, 0, f.renderText("2 - harvester analytics"))
            #stdscr.addstr(15, 0, f.renderText("3 - xch / XCH - CHIA chia "))
            stdscr.addstr(15, 0, f.renderText("PEAK: 4.456.456 "))
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
            #stdscr.addstr(20, 0, f.renderText("4 - move interface"))
            f = pyfiglet.Figlet(font=fonts[ff], width=230)
            font = pyfiglet.FigletFont(fonts[ff])
            stdscr.addstr(25, 10, f.renderText(fonts[ff]))
            stdscr.addstr(35, 0, f"name: {fonts[ff]} height: {font.height}")
        except:
            stdscr.addstr(5, 0, "not working")
            stdscr.addstr(15, 0, fonts[ff])


        stdscr.refresh()
        key = stdscr.getch()


def main():
    curses.wrapper(menu)

if __name__ == "__main__":
    main()
