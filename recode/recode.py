from sys import argv
from os.path import isfile, isdir
from os import mkdir
from json import dump, load
HELP = '''
Usage: recode.py <options>/<filename(s)>
Options:
    If options is specified, program will only save configs.
    
    -i: input file code. (eg. utf-8) (Default: test all known codes)
    -o: output file code. (Default: utf-8)
    -c: codes that try to convert from. (Default: test all known codes)
        split by ','.   (eg. utf-8,gbk,gb2312)
    -r: save the output file in the specified directory. (Default: out)
    -s: show all known codes. (Don't use this with others)
'''
OPTIONS = ["-i", "-o", "-c", "-s", "-r"]

CODES = ['ascii', 'big5', 'big5hkscs', 'cp037', 'cp273', 'cp424', 'cp437', 'cp500', 'cp720', 'cp737', 'cp775', 'cp850', 'cp852', 'cp855', 'cp856', 'cp857', 'cp858', 'cp860', 'cp861', 'cp862', 'cp863', 'cp864', 'cp865', 'cp866', 'cp869', 'cp874', 'cp875', 'cp932', 'cp949', 'cp950', 'cp1006', 'cp1026', 'cp1125', 'cp1140', 'cp1250', 'cp1251', 'cp1252', 'cp1253', 'cp1254', 'cp1255', 'cp1256', 'cp1257', 'cp1258', 'euc_jp', 'euc_jis_2004', 'euc_jisx0213', 'euc_kr', 'gb2312', 'gbk', 'gb18030', 'hz', 'iso2022_jp', 'iso2022_jp_1', 'iso2022_jp_2', 'iso2022_jp_2004',
         'iso2022_jp_3', 'iso2022_jp_ext', 'iso2022_kr', 'latin_1', 'iso8859_2', 'iso8859_3', 'iso8859_4', 'iso8859_5', 'iso8859_6', 'iso8859_7', 'iso8859_8', 'iso8859_9', 'iso8859_10', 'iso8859_11', 'iso8859_13', 'iso8859_14', 'iso8859_15', 'iso8859_16', 'johab', 'koi8_r', 'koi8_t', 'koi8_u', 'kz1048', 'mac_cyrillic', 'mac_greek', 'mac_iceland', 'mac_latin2', 'mac_roman', 'mac_turkish', 'ptcp154', 'shift_jis', 'shift_jis_2004', 'shift_jisx0213', 'utf_32', 'utf_32_be', 'utf_32_le', 'utf_16', 'utf_16_be', 'utf_16_le', 'utf_7', 'utf_8', 'utf_8_sig']
DEFALT = {'ipt': None, 'opt': 'utf-8', 'test': None, 'write': 'out'}


def setOption(arg):
    if arg[0] == '-s':
        for i in CODES:
            print("%15s" % i, end=' ')
        return
    opt = arg[::2]
    val = arg[1:][::2]
    option = DEFALT.copy()
    trans = {'-i': 'ipt', '-o': 'opt', '-c': 'test', "-r": "write"}
    for o, v in zip(opt, val):
        if o == '-c':
            option[trans[o]] = v.split(',')
        else:
            option[trans[o]] = v
    with open("config.json", "w") as f:
        dump(option, f)


def main(files):
    if isfile("config.json"):
        try:
            with open("config.json", "r") as f:
                config = load(f)
        except Exception:
            print("Can't read config file.")
            config = DEFALT
    else:
        print("No config file provided.")
        config = DEFALT

    codes = CODES if config["test"] is None else config["test"]
    outcode = config["opt"]
    outdir = config["write"]

    if not isdir(outdir):
        mkdir(outdir)

    for file in files:
        if isfile(outdir+'/'+file):
            print(f"File '{outdir+'/'+file} exists. Ignore.")
            continue
        if config["ipt"] is None:
            for code in codes:
                if recode(file, outdir, code, outcode, config["write"]):
                    break
        else:
            if not recode(file, outdir, config["ipt"], outcode):
                print("Could not convert '%s' from '%s' to '%s'" %
                      (file, config["ipt"], outcode))
            else:
                print(f"Success to convert {file}")


def recode(file, opt, src, to) -> bool:
    try:
        with open(file, 'r', encoding=src) as f:
            tem = f.read()
    except KeyboardInterrupt:
        exit(2)
    except Exception:
        print("Can't open file.")
        return False
    try:
        with open(opt+'/'+file, 'w', encoding=to) as f:
            f.write(tem)
    except KeyboardInterrupt:
        exit(2)
    except Exception:
        print("Can't write file.")
    return True


if __name__ == '__main__':
    if len(argv) == 1:
        print(HELP)
        exit(1)
    elif argv[1] in OPTIONS:
        setOption(argv[1:])
    else:
        main(argv[1:])
