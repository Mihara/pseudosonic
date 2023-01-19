#!/usr/bin/env python3

"""
Trivial pseudo-client.
"""

import os
import re
import pathlib
import argparse
import configparser
from urllib.parse import urljoin

import libsonic

FILE_LEGAL = re.compile(r"[^\w_. -]")

parser = argparse.ArgumentParser(
    description="Dowlonad music off a Subsonic server, "
    "forcing a specific transcode format."
)
parser.add_argument(
    "--config",
    "-c",
    metavar="FILE",
    nargs="?",
    default="config.ini",
    type=argparse.FileType("r"),
    help="Configuration file to use",
)

args = parser.parse_args()

cfg = configparser.ConfigParser()
cfg.read_file(args.config)

cfg = cfg["pseudosonic"]

# Establish and test connection to server.
conn = libsonic.Connection(
    cfg["url"],
    port=cfg.getint("port", 443)
    if cfg["url"].startswith("https")
    else cfg.getint("port", 80),
    serverPath=urljoin(cfg.get("server_path", "/"), "rest"),
    username=cfg["username"],
    password=cfg["password"],
)

conn.ping()

# To prevent from doing things more than once, we'll suck everything
# into one dict by song id, where every song has an 'album' and 'artist' fields anyway.
songlist = dict()


def grab_song(songrec):
    "Grab a single song..."
    for rec in songrec:
        songlist[rec["id"]] = rec


def grab_album(albumrec):
    "Acquire every song of an album..."
    for album in albumrec:
        album_songs = conn.getAlbum(album["id"])
        grab_song(album_songs["album"]["song"])


if not cfg.get("playlist"):
    print("Collecting favorites.")

    # Now we got our library of favorites, which comes in three kinds -
    # artist, album and song.
    favorites = conn.getStarred2()

    # Starring an artist means I want every song they're involved with,
    # so we recurse down.
    for artist in favorites["starred2"]["artist"]:
        artist_info = conn.getArtist(artist["id"])
        grab_album(artist_info["artist"]["album"])

    # Now do the same for starred albums.
    grab_album(favorites["starred2"]["album"])

    # And for individual starred songs.
    grab_song(favorites["starred2"]["song"])

else:
    print("Collecting playlist '{}'".format(cfg["playlist"]))
    # Else we're dealing with a playlist, so get that.
    playlists = conn.getPlaylists()

    for playlist in playlists["playlists"]["playlist"]:
        if playlist["name"] == cfg["playlist"]:
            playlist_data = conn.getPlaylist(playlist["id"])
            # Playlist entries actually appear to be songs in the end,
            # and I assume it's the same for smart playlists...
            grab_song(playlist_data["playlist"]["entry"])

# Now that we have a list, go through it, streaming every song into a file,
# explicitly stating format and bitrate so the server does the transcoding for us.

file_format = cfg.get("format", "mp3")

for song in songlist.values():
    filepath = os.path.join(
        cfg.get("music_dir", "."),
        FILE_LEGAL.sub("_", song["artist"]),
        FILE_LEGAL.sub("_", song["album"]),
    )
    pathlib.Path(filepath).mkdir(parents=True, exist_ok=True)
    filename = os.path.join(
        filepath,
        ("{:02} - ".format(song["track"]) if song["track"] else "")
        + FILE_LEGAL.sub("_", song["title"])
        + "."
        + file_format,
    )
    filedata = conn.stream(
        song["id"], tformat=file_format, maxBitRate=cfg.get("bitrate", 128)
    )
    print("Downloading {}".format(filename))
    with open(filename, "wb") as f:
        f.write(filedata.read())
