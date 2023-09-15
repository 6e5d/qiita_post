from importer import importer
importer("../../flatmark/flatmark", __file__)

import os, json, hashlib
from pathlib import Path
from subprocess import run
token = open(Path(__file__).parent.parent / "token.txt").read().strip()

from .image_upload import upload
from flatmark.flatmark import Document, Multimedia, Paragraph
from flatmark.conv_md import conv_md

def urlcheck(url):
	if url.startswith("http"):
		return False
	return url.endswith(".png")

def sha256(src):
	h = hashlib.sha256()
	data = open(src, "rb").read()
	h.update(data)
	return h.hexdigest()

def replace_url(src, metadir, imagemap, lines):
	doc = Document(lines)
	blogurl = f"https://6e5d.com/blog/{metadir.name}"
	# first round: build the candidates
	toask = []
	for sect in doc.sects:
		for idx, block in enumerate(sect.blocks):
			if not isinstance(block, Multimedia):
				continue
			print(block.url)
			path = block.url
			if "/" in path:
				raise Exception(f"Non flat multimedia path: {path}")
			if block.ty == "image":
				ppath = src.parent / path
				hash = sha256(ppath)
				if path in imagemap:
					if hash != imagemap[path][1]:
						toask.append((path, hash))
				else:
					print("uploading", path)
					loc = upload(ppath.parent, ppath.name)
					imagemap[path] = (loc, hash)
			elif block.ty == "audio":
				sect.blocks[idx] = Paragraph(
					"> **AUDIO NOT RENDERED**"
					"(Qiitaは音声ファイルに[対応しない]"
					"(https://github.com/increments/qiita-discussions/discussions/348)ため"
					f"[個人サイト]({blogurl})"
					"に閲覧してください)"
				)
				continue
			else:
				raise Exception(block.ty)
	# ask updated images
	if len(toask) > 0:
		print("===input update list===")
		for idx, path in enumerate(toask):
			print(idx, path)
		upd = input("update: ")
		indices = [int(x) for x in upd.strip().split()]
		for idx, (path, hash) in enumerate(toask):
			if idx in indices:
				ppath = Path(path)
				print("uploading", ppath)
				loc = upload(ppath.parent, ppath.name)
				assert path in imagemap
				imagemap[path] = (loc, hash)
	# second round: perform replacing
	f = open(metadir / "imagemap.txt", "w")
	for sect in doc.sects:
		for block in sect.blocks:
			if not isinstance(block, Multimedia):
				continue
			path = block.url
			if not urlcheck(path):
				continue
			assert path in imagemap
			loc, tt = imagemap[path]
			print(tt, path, loc, file = f)
			block.url = loc
	f.close()
	lines = conv_md(doc)
	return lines

def preprocess(src):
	lines = [line.strip() for line in open(src)]
	assert lines[0].startswith("# ")
	title = lines[0].removeprefix("# ")
	assert len(lines[1]) == 0
	assert lines[2].startswith("date: ")
	date = lines[2].removeprefix("date: ")
	assert lines[3].startswith("tags: ")
	tags = lines[3].removeprefix("tags: ")
	tags = tags.split(" ")
	assert len(tags) <= 5
	assert len(lines[4]) == 0
	return lines[5:], title, date, tags

def post(metadir, posturl, text, title, tags):
	data = {
		"body": text,
		"private": False,
		"title": title,
		"tags": [{"name": tag, "versions": []} for tag in tags]
	}
	import requests
	headers = {
		"Content-Type": "application/json",
		"Authorization": f"Bearer {token}",
	}
	if posturl == None:
		print(f"new post")
		resp = requests.post(
			"https://qiita.com/api/v2/items",
			headers = headers,
			data = json.dumps(data),
		)
	else:
		print(f"update {posturl}")
		resp = requests.patch(
			posturl,
			headers = headers,
			data = json.dumps(data),
		)
	print(resp.status_code)
	print(resp.headers)
	j = json.loads(resp.content.decode())
	with open(metadir / "posturl.txt", "w") as f:
		print(j["url"], file = f)

def prepare(metadir):
	imagemap = dict()
	if Path(metadir).is_dir():
		with open(metadir / "posturl.txt") as f:
			posturl = f.read().strip()
			pid = posturl.rsplit("/", 1)[1]
			posturl = f"https://qiita.com/api/v2/items/{pid}"
		with open(metadir / "imagemap.txt") as f:
			for line in f:
				[hash, path, loc] = line.strip().split()
				imagemap[path] = (loc, hash)
	else:
		Path(metadir).mkdir()
		posturl = None
	return posturl, imagemap

def qiita_post(path):
	src = Path(path).resolve()
	proj = src.parent.resolve().name
	print("name:", proj)
	metadir = src.parent.parent.parent / "metadata" / proj
	posturl, imagemap = prepare(metadir)

	lines, title, _date, tags = preprocess(src)
	lines = replace_url(src, metadir, imagemap, lines)
	post(metadir, posturl, "\n".join(lines), title, tags)
