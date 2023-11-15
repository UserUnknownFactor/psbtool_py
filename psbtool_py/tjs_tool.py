from psbtool_py.tjs2manager import TJS2SManager
from glob import glob
import os, sys
from filetranslate.service_fn import read_csv_list, write_csv_list

TJS_PATHS = "system\\*.tjs"
STRINGS_NAME = "strings"
ATTRIBUTES_NAME = "attributes"
STRINGS_DB_POSTFIX = "_" + STRINGS_NAME + ".csv"
DEF_OUT_DIR = 'translation_out'

def make_postfixed_name(name, postfix):
    return os.path.join(os.path.dirname(name), os.path.basename(name) + postfix)

def remove_ext(name):
    name = name.split('.')
    return '.'.join(name[:-1])

def read_string_translations(name, ext=''):
    name = remove_ext(name)
    name = make_postfixed_name(name, ext + STRINGS_DB_POSTFIX)
    return read_csv_list(name)

def pack_function(scenarios, out_dir):
    cwd = os.getcwd()
    for fn in glob(scenarios):
        fncsv = read_string_translations(fn)
        if not fncsv: continue
        ofn = os.path.abspath(os.path.abspath(fn).replace(os.getcwd(), out_dir))
        if out_dir != DEF_OUT_DIR:
            print(f"Translating to {ofn} ... ")
        else:
            print(f"Translating {fn.replace(cwd, '')} ... ")
        ofn_dir = ''
        with open(fn, 'rb') as f:
            a = TJS2SManager(f)
            so = a.import_strings()
            try:
                i_empty = so.index('')
                fncsv.insert(i_empty, ['', ''])
            except:
                pass
            full_index_mode = False
            if len(fncsv) == len(so):
                full_index_mode = True
            for i, s in enumerate(so):
                if not s: continue
                #print(fncsv[i][0], so[i])
                if full_index_mode:
                    if fncsv[i][0][:2] != "//" and fncsv[i][1].strip() != "":
                        so[i] = fncsv[i][1]
                else:
                    for line in fncsv:
                        if line[0][:2] != "//" and len(line) > 1 and line[1].strip() != "" and line[0] == so[i]:
                            so[i] = line[1]
                            break
            if ofn_dir != os.path.dirname(ofn):
                ofn_dir = os.path.dirname(ofn)
                if ofn_dir != '' and not os.path.exists(ofn_dir):
                    os.makedirs(ofn_dir, exist_ok=True)
            with open(ofn, 'wb') as o:
                o.write(a.export_strings(so))
                pass
        pass

def unpack_function(scenarios):
    cwd = os.getcwd()
    for fn in glob(scenarios):
        fncsv = make_postfixed_name(os.path.splitext(fn)[0], STRINGS_DB_POSTFIX)
        if os.path.isfile(fncsv): continue
        print(f"Parsing {fn.replace(cwd, '')} ... ", end='')
        with open(fn, 'rb') as f:
            so = []
            s = []
            a = TJS2SManager(f)
            so = a.import_strings()
            for i in so:
                if not i: continue
                s.append([i, ''])
            write_csv_list(fncsv, s)
            print(f"{len(so)} strings")
        pass

def main():
    if len(sys.argv) > 1:
        import argparse

        parser = argparse.ArgumentParser(description='Tool to pack and unpack KiriKiri .tjs strings')
        parser.add_argument('command', choices=['pack', 'unpack'], help='Command to run')
        parser.add_argument('path', nargs='?', default=TJS_PATHS, help='Files mask')
        parser.add_argument('-od', default=DEF_OUT_DIR, help='Files mask')
        args = parser.parse_args()

        if args.command == 'pack':
            pack_function(args.path, args.od)
        elif args.command == 'unpack':
            unpack_function(args.path)
    else:
        pack_function(TJS_PATHS, DEF_OUT_DIR)

if __name__ == '__main__':
    main()