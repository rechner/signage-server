"""
Import content into Signage Server
"""

import os
import argparse
import sys

import magic
import yaml
from tinydb import TinyDB, Query
from werkzeug.datastructures import FileStorage

from signage_server_app import crud

# Open the database
curdir = os.path.dirname(os.path.realpath(__file__))
db = TinyDB(os.path.join(curdir, "data", "db.json"))
# Load item templates to use when checking for valid items
with open(os.path.join(curdir, "data", "item_templates.yaml"), 'r') as f:
    item_templates = yaml.load(f.read(), Loader=yaml.SafeLoader)

content_table = db.table("content")
playlists_table = db.table("playlists")

def import_file(args, playlist=[]):
    for fname in args.file:
        if not os.path.exists(fname):
            print(f"Error: {fname} does not exist, skipping...")
            continue
        if not crud.allowed_file(fname):
            print(f"Warning: {fname} is not a supported filetype, skipping...")
            continue

        #if args.replace:
        #    # Clear the playlist
        #    playlist.update({'tracks': []}, Query().name == args.playlist)

        with open(fname, "rb") as f:
            filename = os.path.basename(f.name)
            content_type = magic.from_file(fname, mime=True)
            image = FileStorage(content_type=content_type, filename=filename, stream=f)
            data = crud.process_file(image)
            data['name'] = f"{args.name_prefix}{filename}"
            if crud.valid_item(item=data, template=item_templates["content"]):
                item_id = content_table.insert(data)
                print(f"Imported id {item_id}")

            # Append to playlist
            #playlist = playlist.append(data)
            #playlists_table.update({'tracks': playlist}, Query().name == args.playlist)


def get_playlist(args):
    Playlist = Query()
    playlists = db.table("playlists")
    return playlists.get(Playlist.name == args.playlist)


def playlist_exists(args):
    return get_playlist(args) is not None


def update_playlist_to_content(args):
    all_content = content_table.all()
    tracks = [ {'duration': args.duration, 'seq': seq, 'track': track} for seq, track in enumerate(all_content) ]
    playlists_table.update({'tracks': tracks}, Query().name == args.playlist)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--name-prefix', default="imported-")
parser.add_argument('--playlist', default=None, help="If specified, replaces named playlist with imported images")
#parser.add_argument('--replace', type=bool, help="Replace playlist (instead of append) with imported values")
parser.add_argument('--duration', type=int, default=10, help="Default image duration, in seconds")
parser.add_argument('file', nargs='+', help='Image or video file to import')

if __name__ == "__main__":
    args = parser.parse_args()
    playlist = []
    if args.playlist:
        playlist = get_playlist(args)
        if playlist is None:
            print(f"Error: Playlist {args.playlist} does not exist")
            sys.exit()

    import_file(args, playlist=playlist)

    if args.playlist:
        update_playlist_to_content(args)

