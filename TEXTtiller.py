from pathlib import Path


class Font:
    def __init__(self):
        self.fChars = {}  # ASCII code; figlet chars hashtable
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


def loadFontFTL(filePath, font):
    with open(filePath, 'r') as file:
        # read the header
        lines = file.readlines()
        header = lines.pop(0)[5:-1].split(' ')
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
                newLine = fChar.chars[begin:end]
                if prev_char == ' ' or i == ' ':
                    if i == ' ':
                        chars = fChar.chars[begin:end]
                        strings[s] += ' ' * len(chars)
                        pass
                    else:
                        strings[s] += fChar.chars[begin:end]
                else:
                    if i == ' ':
                        pass
                        # to do
                        #print('char', i)
                        #print(fChar.smushLeft)
                        #print(fChar.smushRight)
                        #print(smush)
                    if smush == 0:
                        pass
                        # to do
                        #print('charrrr')
                        #print(i)
                        #print(smush)
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
            else:
                strings[s] += fChar.chars[begin:end]
            begin = end
            end = begin + fChar.width
        prev_char = i
    return strings


if __name__ == "__main__":

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
    path_figlet_font = Path("figlet_fonts")

    ffont = Font()
    pathA = path_figlet_font / "doom.flf"
    loadFontFTL(pathA, ffont)
    print('two')
    s = renderFont('  rototiller', ffont)
    print(s)
    for i in s:
        print(i)
    print('two done')

    loadFontFTL(pathA, ffont)
    print('two')
    s = renderFont('toto roto -:; - : ;  tiiiller', ffont)
    for i in s:
        print(i)
    print('two done')

    ffont = Font()
    pathA = path_figlet_font / "future.tlf"
    loadFontFTL(pathA, ffont)
    print('one')
    s = renderFont('toto MOro   rototiller poto', ffont)
    for i in s:
        print(i)
