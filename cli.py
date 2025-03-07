import argparse

from big import BigArchive
from big.patch import TargetParameters


def main():
    parser = argparse.ArgumentParser(description="BIG file utility tool.")
    parser.add_argument('--extract', nargs='+', help='Extract a BIG file.')
    parser.add_argument('--bundle', nargs=2, help='Bundle a folder back into a BIG file.')
    parser.add_argument('--list', help='List contents of a BIG file.')
    parser.add_argument('--patch', action='store_true', help='Patch a BIG file with parameters.')

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
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()