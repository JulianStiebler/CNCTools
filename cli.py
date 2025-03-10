import argparse

from BIGArchive import BigArchive
from BIGArchive.patch import TargetParameters

CNCPATH = "C:\Games\Steam\steamapps\common\Command & Conquer Generals - Zero Hour"
INSIGHTFOLDER = "insights"

def main():
    parser = argparse.ArgumentParser(description="BIG file utility tool.")
    parser.add_argument('--extract', nargs='+', help='Extract a BIG file.')
    parser.add_argument('--bundle', nargs=2, help='Bundle a folder back into a BIG file.')
    parser.add_argument('--list', help='List contents of a BIG file.')
    parser.add_argument('--patch', action='store_true', help='Patch a BIG file with parameters.')
    parser.add_argument('--metadata', action='store_true', help='Scan and collect metadata from BIG files.')

    args = parser.parse_args()

    if args.extract:
        filepath = args.extract[0]
        out_dir = args.extract[1] if len(args.extract) > 1 else None
        archive = BigArchive(filepath)
        archive.extract(out_dir)
    
    elif args.bundle:
        folder_path, output_file = args.bundle
        BigArchive.bundle(folder_path, output_file)
    
    elif args.list:
        archive = BigArchive(args.list)
        archive.list_contents()
    
    elif args.patch:
        mod_params = [TargetParameters.CAMERA_HEIGHT_MAX]
        archive = BigArchive(mod_params[0].big_file)
        archive.patch_parameters(mod_params)

    elif args.metadata:
        root_directory = CNCPATH
        output_file = f'{INSIGHTFOLDER}/metadata.json'
        BigArchive.scan_and_collect_metadata(root_directory, output_file)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()