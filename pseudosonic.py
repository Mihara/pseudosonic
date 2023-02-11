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

parser.add_argument(
    "--profile", "-p", metavar="PROFILE", nargs="*", help="Which profile(s) to fetch."
)

args = parser.parse_args()

cfg = configparser.ConfigParser()
cfg.read_file(args.config)

server = cfg["SERVER"]

# Establish and test connection to server.
conn = libsonic.Connection(
    server["url"],
    port=server.getint("port", 443)
    if server["url"].startswith("https")
    else server.getint("port", 80),
    serverPath=urljoin(server.get("server_path", "/"), "rest"),
    username=server["username"],
    password=server["password"],
)

conn.ping()

# This will only get filled once.
album_data = dict()


def grab_song(songrec):
    "Grab a single song..."
    for rec in songrec:
        songlist[rec["id"]] = rec


def grab_album(albumrec):
    "Acquire every song of an album..."
    for album in albumrec:
        
        # Save album data for later.
        album_data[album["id"]] = album
        
        album_songs = conn.getAlbum(album["id"])
        grab_song(album_songs["album"]["song"])


def grab_profile(profile):
    "Fetch music data per a profile"

    if not profile.get("playlist"):
        print("Collecting favorites.")

        # Now we got our library of favorites, which comes in three kinds -
        # artist, album and song.
        favorites = conn.getStarred2()

        # Starring an artist means I want every song they're involved with,
        # so we recurse down.
        for artist in favorites["starred2"].get("artist", []):
            artist_info = conn.getArtist(artist["id"])
            grab_album(artist_info["artist"].get("album", []))

        # Now do the same for starred albums.
        grab_album(favorites["starred2"].get("album", []))

        # And for individual starred songs.
        grab_song(favorites["starred2"].get("song", []))

    else:
        print("Collecting playlist '{}'".format(profile["playlist"]))
        # Else we're dealing with a playlist, so get that.
        playlists = conn.getPlaylists()

        for playlist in playlists["playlists"]["playlist"]:
            if playlist["name"] == profile["playlist"]:
                playlist_data = conn.getPlaylist(playlist["id"])
                # Playlist entries actually appear to be songs in the end,
                # and I assume it's the same for smart playlists...
                grab_song(playlist_data["playlist"]["entry"])


def update_album_data(songlist):
    "Fetch the album information for albums we haven't done so for yet."
    for song in songlist.values():
        if not album_data.get(song["albumId"]):
            album_data[song["albumId"]] = conn.getAlbum(song["albumId"]).get("album")


def get_songs(songlist, profile):

    # Now that we have a list, go through it, streaming every song into a file,
    # explicitly stating format and bitrate so the server does the transcoding for us.

    file_format = profile.get("format", server.get("format", "mp3"))

    for song in songlist.values():

        # If the song is part of an album, the artist part of the directory is
        # the album artist, rather than the song artist.
        # This prevents scattering an album or compilation.
        # Fetching the album details takes a substantial amount of extra time though.
        
        artist_name = album_data[song["albumId"]].get("artist") or song["artist"]
        filepath = os.path.join(
            profile.get("music_dir", server.get("music_dir", ".")),
            FILE_LEGAL.sub("_", artist_name),
            FILE_LEGAL.sub("_", song["album"]),
        )
        pathlib.Path(filepath).mkdir(parents=True, exist_ok=True)
        filename = os.path.join(
            filepath,
            ("{:02} - ".format(song["track"]) if song.get("track") else "")
            + FILE_LEGAL.sub("_", song["title"])
            + "."
            + file_format,
        )

        if not profile.getboolean("overwrite") and pathlib.Path(filename).exists():
            continue

        filedata = conn.stream(
            song["id"],
            tformat=file_format,
            maxBitRate=profile.get("bitrate", server.get("bitrate", 128)),
        )
        print("Downloading {}".format(filename))
        with open(filename, "wb") as f:
            f.write(filedata.read())

        # Deal with cover art.
        if profile.getboolean("coverart"):
            cover_file = os.path.join(
                filepath,
                profile.get("coverart_file", server.get("coverart_file", "cover.jpg")),
            )
            if not pathlib.Path(cover_file).exists():
                request = conn.getCoverArt(
                    song["id"],
                    size=profile.get("coverart_size", server.get("coverart_size", 512)),
                )
                with open(cover_file, "wb") as f:
                    f.write(request.read())


for section in cfg.sections():
    if section == "SERVER":
        continue
    if args.profile and section not in args.profile:
        continue

    profile = cfg[section]

    print("Profile:", section)

    # To prevent from doing things more than once per profile, we'll suck everything
    # into one dict by song id, where every song has an 'album' and 'artist' fields anyway.
    songlist = dict()

    grab_profile(profile)
    update_album_data(songlist)
    get_songs(songlist, profile)
