import argparse

from models import AtiXML


def main():

    parser = argparse.ArgumentParser('Merge timestamps from an F5 text ' + \
        'file [F] with coding from an Atlas.ti XML dump [A] and write the' + \
        ' result to an output file [O]')
    parser.add_argument('atixml', metavar='A', type=str,
        nargs=1, help='the Atlas.ti file name (full path if in separate dir)')
    parser.add_argument('f5txt', metavar='F', type=str, nargs=1,
        help='the F5 file name (full path if in separate dir)')
    parser.add_argument('outxls', metavar='O', type=str, nargs=1,
        help='name of the output Excel file (full path if in separate dir)')
    args = parser.parse_args()

    try:
        ati = AtiXML(args.atixml[0])
        ati.merge_timestamps(args.f5txt[0])
        ati.export_to_excel(args.outxls[0])
    except:
        raise


if __name__ == '__main__':
    main()