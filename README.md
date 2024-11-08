# Anime1 LocalServer

Local video server for anime1

Watch anime in local video player

## Attention

It is now more recommended to use [Anime1Proxy](https://github.com/XFY9326/Anime1Proxy), which is written in Kotlin, is faster and supports HTTP/2.

## Requirements

- Python 3.10

## Dependencies

- aiohttp
- bs4
- xspf_lib

**If you want to use system tray:**

- pystray

## Usage

Install dependencies  
(It's recommended to install dependencies in venv instead of global environment)

```shell
pip install poetry
poetry install --only main
```

Launch local server in terminal

```shell
poetry run python main.py
```

## System tray and packaging

*This is not necessary unless you want a better using experience.*

Build with [Nuitka](https://github.com/Nuitka/Nuitka)

**Additional requirements**

- nuitka
- imageio
- Nuitka compilers (See [Nuitka](https://github.com/Nuitka/Nuitka))

Install all dependencies

```shell
poetry install
```

Build

```shell
poetry install
poetry run python build.py
```

You will find single executable file under `./build` folder

## Url methods

- `http://127.0.0.1:8520`  
  Home page (Show help)
- `http://127.0.0.1:8520/p?url=<Url>`  
  Parse url to json detail
- `http://127.0.0.1:8520/l`  
  List all recent video categories (No external videos by default)  
  If there are any `ex` parameters (`http://127.0.0.1:8520/l?ex=1`), it will list all external videos
- `http://127.0.0.1:8520/c/<CategoryId>`  
  Open category by category id (Response m3u8 playlist)
- `http://127.0.0.1:8520/c/<CategoryId>?playlist=m3u8`  
  Download category by category id (Response m3u8 playlist)
- `http://127.0.0.1:8520/c/<CategoryId>?playlist=dpl`  
  Download category by category id (Response PotPlayer dpl playlist)
- `http://127.0.0.1:8520/c/<CategoryId>?playlist=dpl_ext`  
  Download category by category id (Response PotPlayer dpl external playlist which redirects to m3u8)
- `http://127.0.0.1:8520/c/<CategoryId>?playlist=xspf`  
  Download category by category id (Response XSPF playlist for VLC, PotPlayer etc.)
- `http://127.0.0.1:8520/c/<CategoryId>?playlist=xspf_ext`  
  Download category by category id (Response XSPF playlist which redirects to m3u8)
- `http://127.0.0.1:8520/v/<PostId>`  
  Open video by post id (Response video stream)

## Example

List all video categories without external videos

```text
http://127.0.0.1:8520/l
```

List all videos under this category

```text
http://127.0.0.1:8520/p?url=https://anime1.me/category/2013年春季/進擊的巨人
```

```json5
{
  "type": "category",
  "id": "90",
  "title": "進擊的巨人",
  "url": "http://127.0.0.1:8520/c/90",
  "playlists": {
    "m3u8": "http://127.0.0.1:8520/c/90?playlist=m3u8",
    "dpl": "http://127.0.0.1:8520/c/90?playlist=dpl",
    "dpl_ext": "http://127.0.0.1:8520/c/90?playlist=dpl_ext",
    "xspf": "http://127.0.0.1:8520/c/90?playlist=xspf",
    "xspf_ext": "http://127.0.0.1:8520/c/90?playlist=xspf_ext"
  },
  "videos": [
    {
      "id": "1213",
      "title": "進擊的巨人 [01]",
      "url": "http://127.0.0.1:8520/v/1213"
    },
    // More videos ...
  ]
}
```

Open this category as m3u8 playlist

```text
http://127.0.0.1:8520/c/90
```

Play specific video in browser or any video player

```text
http://127.0.0.1:8520/v/1213
```
