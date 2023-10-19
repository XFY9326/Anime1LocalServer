# Anime1LocalServer

Local video server for anime1

Watch anime in local video player

## Requirements

- Python 3.10

## Dependencies

- aiohttp
- bs4
- fastapi
- uvicorn
- xspf_lib

## Usage

Install dependencies  
(It's recommended to install dependencies in venv instead of global environment)

```shell
pip install -r requirements.txt
```

Launch local server on `http://127.0.0.1:8000`

```shell
python main.py
```

## Packaging

*This is not necessary unless you need faster running speed or want to be able to run on a device that does not have a Python environment.*

Build by [Nuitka](https://github.com/Nuitka/Nuitka)

```shell
python build.py
```

You will find single executable file under `./build` folder

Attention: You need to install compilers for Nuitka first! (See [Nuitka](https://github.com/Nuitka/Nuitka))

## Url methods

- `http://127.0.0.1:8000`  
  Home page (Useless)
- `http://127.0.0.1:8000/p?url=<Url>`  
  Parse url to json detail
- `http://127.0.0.1:8000/c/<CategoryId>`  
  Open category by category id (Response m3u8 playlist)
- `http://127.0.0.1:8000/c/<CategoryId>?playlist=m3u8`  
  Download category by category id (Response m3u8 playlist)
- `http://127.0.0.1:8000/c/<CategoryId>?playlist=dpl`  
  Download category by category id (Response PotPlayer dpl playlist)
- `http://127.0.0.1:8000/c/<CategoryId>?playlist=dpl_ext`  
  Download category by category id (Response PotPlayer dpl external playlist which redirects to m3u8)
- `http://127.0.0.1:8000/c/<CategoryId>?playlist=xspf`  
  Download category by category id (Response XSPF playlist for VLC, PotPlayer etc.)
- `http://127.0.0.1:8000/c/<CategoryId>?playlist=xspf_ext`  
  Download category by category id (Response XSPF playlist which redirects to m3u8)
- `http://127.0.0.1:8000/v/<PostId>`  
  Open video by post id (Response video stream)

## Example

List all videos under this category

```text
http://127.0.0.1:8000/p?url=https://anime1.me/category/2013年春季/進擊的巨人
```

```json5
{
  "type": "category",
  "id": "90",
  "title": "進擊的巨人",
  "url": "http://127.0.0.1:8000/c/90",
  "playlists": {
    "m3u8": "http://127.0.0.1:8000/c/90?playlist=m3u8",
    "dpl": "http://127.0.0.1:8000/c/90?playlist=dpl",
    "dpl_ext": "http://127.0.0.1:8000/c/90?playlist=dpl_ext",
    "xspf": "http://127.0.0.1:8000/c/90?playlist=xspf",
    "xspf_ext": "http://127.0.0.1:8000/c/90?playlist=xspf_ext"
  },
  "videos": [
    {
      "id": "1213",
      "title": "進擊的巨人 [01]",
      "url": "http://127.0.0.1:8000/v/1213"
    },
    // More videos ...
  ]
}
```

Open this category as m3u8 playlist

```text
http://127.0.0.1:8000/c/90
```

Play specific video in browser or any video player

```text
http://127.0.0.1:8000/v/1213
```
