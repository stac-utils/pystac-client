import argparse
import json
import logging
import os
import sys

from .item_collection import ItemCollection
from .client import Client
from .version import __version__

STAC_URL = os.getenv('STAC_URL', None)

logger = logging.getLogger(__name__)


def search(url=STAC_URL, matched=False, save=None, headers=None, **kwargs):
    """ Main function for performing a search """

    try:
        catalog = Client.open(url, headers=headers)
        search = catalog.search(**kwargs)

        if matched:
            matched = search.matched()
            print('%s items matched' % matched)
        else:
            items = ItemCollection(search.items())
            if save:
                with open(save, 'w') as f:
                    f.write(json.dumps(items.to_dict()))
            else:
                print(json.dumps(items.to_dict()))

    except Exception as e:
        logger.error(e, exc_info=True)
        print(e)
        return 1


def parse_args(args):
    desc = 'STAC Client'
    dhf = argparse.ArgumentDefaultsHelpFormatter
    parser0 = argparse.ArgumentParser(description=desc)

    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument('--version',
                        help='Print version and exit',
                        action='version',
                        version=__version__)
    parent.add_argument('--logging', default='INFO', help='DEBUG, INFO, WARN, ERROR, CRITICAL')
    parent.add_argument('--url', help='Root Catalog URL', default=os.getenv('STAC_URL', None))
    parent.add_argument('--limit', help='Page size limit', type=int, default=500)
    parent.add_argument('--headers',
                        nargs='*',
                        help='Additional request headers (KEY=VALUE pairs)',
                        default=None)

    subparsers = parser0.add_subparsers(dest='command')

    # search command
    parser = subparsers.add_parser('search',
                                   help='Perform new search of items',
                                   parents=[parent],
                                   formatter_class=dhf)
    search_group = parser.add_argument_group('search options')

    search_group.add_argument('-c', '--collections', help='One or more collection IDs', nargs='*')
    search_group.add_argument('--ids',
                              help='One or more Item IDs (ignores other parameters)',
                              nargs='*')
    search_group.add_argument('--bbox',
                              help='Bounding box (min lon, min lat, max lon, max lat)',
                              nargs=4)
    search_group.add_argument('--intersects', help='GeoJSON Feature or geometry (file or string)')
    search_group.add_argument('--datetime',
                              help='Single date/time or begin and end date/time '
                              '(e.g., 2017-01-01/2017-02-15)')
    search_group.add_argument('-q',
                              '--query',
                              nargs='*',
                              help='Query properties of form '
                              'KEY=VALUE (<, >, <=, >=, = supported)')
    search_group.add_argument('--sortby', help='Sort by fields', nargs='*')
    search_group.add_argument('--max-items',
                              dest='max_items',
                              help='Max items to retrieve from search',
                              type=int)

    output_group = parser.add_argument_group('output options')
    output_group.add_argument('--matched',
                              help='Print number matched',
                              default=False,
                              action='store_true')
    output_group.add_argument('--save', help='Filename to save Item collection to', default=None)

    parsed_args = {k: v for k, v in vars(parser0.parse_args(args)).items() if v is not None}

    # if intersects is JSON file, read it in
    if 'intersects' in parsed_args:
        if os.path.exists(parsed_args['intersects']):
            with open(parsed_args['intersects']) as f:
                data = json.loads(f.read())
                if data['type'] == 'Feature':
                    parsed_args['intersects'] = data['geometry']
                elif data['type'] == 'FeatureCollection':
                    parsed_args['intersects'] = data['features'][0]['geometry']
                else:
                    parsed_args['intersects'] = data

    # if headers provided, parse it
    if 'headers' in parsed_args:
        new_headers = {}
        for head in parsed_args['headers']:
            parts = head.split('=')
            if len(parts) == 2:
                new_headers[parts[0]] = parts[1]
            else:
                logger.warning(f"Unable to parse header {head}")
        parsed_args['headers'] = new_headers

    return parsed_args


def cli():
    args = parse_args(sys.argv[1:])

    loglevel = args.pop('logging')
    # don't enable logging if print to stdout
    if args.get('save', False) or args.get('matched', False):
        logging.basicConfig(stream=sys.stdout, level=loglevel)
        # quiet loggers
        for lg in ['urllib3']:
            logging.getLogger(lg).propagate = False

    if args.get('url', None) is None:
        raise RuntimeError('No STAC URL provided')

    cmd = args.pop('command')
    if cmd == 'search':
        return search(**args)


if __name__ == "__main__":
    return_code = cli()
    if return_code and return_code != 0:
        sys.exit(return_code)
