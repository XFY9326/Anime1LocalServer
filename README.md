# Anime1LocalServer

Local video server for anime1

Watch anime in local video player

## Requirements

- Python 3.10

## Dependencies

- aiohttp
- m3u8
- bs4
- fake_useragent
- fastapi
- uvicorn

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

Build by [Nuitka](https://github.com/Nuitka/Nuitka)

```shell
python build.py
```

You will find single executable file under `./build` folder

Attention: You need to install compilers for Nuitka first! (See [Nuitka](https://github.com/Nuitka/Nuitka))

## Url

- `http://127.0.0.1:8000` Home page (Useless)
- `http://127.0.0.1:8000/p?url=<Url>` Parse url to json
- `http://127.0.0.1:8000/c/<CategoryId>` Open category by category id (Response m3u8 playlist)
- `http://127.0.0.1:8000/v/<PostId>` Open video by post id (Response video stream)

## Example

List all videos under this category

```
http://127.0.0.1:8000/parse?url=https://anime1.me/category/2012%e5%b9%b4%e5%a4%8f%e5%ad%a3/%e5%88%80%e5%8a%8d%e7%a5%9e%e5%9f%9f-sword-art-online
```

Open this category as m3u8 playlist

```
http://127.0.0.1:8000/c/82
```

Play video

```
http://127.0.0.1:8000/v/1136
```
