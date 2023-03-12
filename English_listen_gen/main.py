from re import match
from mytts import SpeechConfig, AudioOutputConfig, SpeechSynthesizer
from html import escape
from rich import print

def read(filename):
    rst:list[str] = []
    with open(filename, 'r',encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            delay = match("\{delay\s([\d\.]+)\}",line)
            if delay is not None:
                # rst.append(f'<break time="{delay.group(1)}" />')
                t = float(delay.group(1))
                delay_text = ""
                if t>5:
                    delay_text = '<break time="5s" />'*int(t//5)+f'<break time="{t%5}s" />'
                else:
                    delay_text = f'<break time="{t}s" />'
                if "</voice>" in rst[-1]:
                    rst[-1] = rst[-1].replace("</voice>",delay_text+'</voice>')
                else:
                    rst.append(f'<voice name="zh-CN-YunfengNeural"><break time="{delay_text}s" /</voice>')
                    raise RuntimeWarning("Why there is a delay at the very beginning?")
                continue
            who, con = line.split(': ')
            if who == "B":
                fmt = f'<voice name="zh-CN-YunfengNeural"><prosody rate="-30%">{con}</prosody></voice>'
            elif who == "W":
                fmt = f'<voice name="en-US-JennyMultilingualNeural"><prosody rate="-5%" pitch="0%">{con}</prosody></voice>'
            elif who == "M":
                fmt = f'<voice name="en-US-EricNeural"><mstts:silence  type="Sentenceboundary" value="100ms"/><prosody rate="10%" pitch="0%">{con}</prosody></voice>'
            else:
                raise AssertionError("Not a valid text format: {}->{}".format(who,con))
            rst.append(fmt)
    SSML_MODEL='''<speak xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" xmlns:emo="http://www.w3.org/2009/10/emotionml" version="1.0" xml:lang="en-US">{}</speak>'''
    lines = rst
    totLines = len(lines)
    content = []
    i = 0
    while i < totLines:
        tem = ""
        while tem.count("<voice name=") < 49 and i < totLines:
            tem += lines[i]
            tem += "\n"
            i += 1
        # tem = escape(tem)
        content.append(SSML_MODEL.format(tem))
    return content

def syn(content:list[str]):
    spe=SpeechConfig()
    for i,con in enumerate(content):
        opt_cfg=AudioOutputConfig(filename="%02d.mp3" % i)
        print(SpeechSynthesizer(spe,opt_cfg,debug=True).speak_ssml(con))


if __name__ == '__main__':
    print(read("input.txt")[0])
    syn(read("input.txt"))