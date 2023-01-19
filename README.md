# Pseudosonic

Imagine you have a [Navidrome](https://www.navidrome.org/) server *(or another Subsonic API server capable of transcoding)* and a cheap MP3 player, not capable of running a Subsonic client or playing half the formats your music collection is stored in, which you need to synchronize a substantial subset of your music library onto. Or, you don't like the available Subsonic clients for your phone and wish to just make an offline copy of your library, compressed down for your phone.

While you can, of course, go for the files themselves, you can press your server into doing the transcoding as well as selecting files to be synchronized. But you need a Subsonic API client to do that.

This is a nearly-trivial script which is a quick and dirty implementation of such a client.

## Caveats

1. This is not a sufficiently idiot-proof tool for people who don't speak any Python. If you do, it will surely save you an afternoon, or at least serve as a base to build your own script which does things a slightly different way.
2. This script should not strictly *require* Linux, since it depends only on Python 3+ and a Subsonic API library. Nevertheless, it was not tested on anything other than that.
3. It assumes that a certain regular expression is sufficient to make song names into valid unique filenames. While so far I have yet to bump into exceptions with Japanese and Russian, there's no guarantee this is rock solid on your particular system.
4. Downloaded files are saved as an `<artist>/<album>/<track> <song name>.<format extension>` directory tree, according to their tags, rather than directory locations on the server, which may or may not be what you wanted.

## Usage

1. Install requirements with `pip -r requirements.txt`, whether making a virtualenv *(I really like using [direnv](https://direnv.net/) for the job)* or globally or per user.
2. Copy `config.ini.example` to `config.ini` and edit that to set up where your Subsonic server is, where do you want the converted files, and what format do you want them in.
3. Run and wait.

The script is capable of synchronizing your favorited songs, or a specific named playlist, whether a smart playlist or otherwise.

## License

This little ditty is released under the terms of WTFPL 4.0

