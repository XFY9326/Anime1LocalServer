# Anime1LocalServer

Local video server for anime1

Watch anime in local video player

## Requirements

- Python 3.10

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

## Url

- `http://127.0.0.1:8000` Home page (Useless)
- `http://127.0.0.1:8000/parse?url=<CategoryUrl>` Parse caregory url to json
- `http://127.0.0.1:8000/v/<CategoryId>` Open caregory by id (Response m3u8 playlist)
- `http://127.0.0.1:8000/v/<CategoryId>/<VideoId>` Open video in caregory by id (Response video stream)

## Example

List all videos under this category

```
http://127.0.0.1:8000/parse?url=https://anime1.me/category/2012%e5%b9%b4%e5%a4%8f%e5%ad%a3/%e5%88%80%e5%8a%8d%e7%a5%9e%e5%9f%9f-sword-art-online
```

Open this category as m3u8 playlist

```
http://127.0.0.1:8000/v/82
```

Play video

```
http://127.0.0.1:8000/v/82/1136
```