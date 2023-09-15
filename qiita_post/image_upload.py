import requests, json
from qiita_post import token

# stage1: qiita.comと通信
def stage1(filename, size):
	headers = {
		"Content-Type": "application/json",
		"Authorization": f"Bearer {token}",
	}
	data = {"image": {
		"content_type": "image/png",
		"name": filename,
		"size": size,
	}}
	resp = requests.post(
		"https://qiita.com/api/upload/policies",
		data = json.dumps(data),
		headers = headers,
	)
	assert resp.status_code == 200
	content = resp.content
	resp.close()
	j = json.loads(content.decode())
	return j

# stage2: S3と通信
def stage2(j, img, filename):
	url = j["upload_url"]
	files = j["form"]
	for name, value in files.items():
		files[name] = (None, value)
	files["file"] = (filename, img, "image/png")
	resp = requests.post(url, files = files)
	# print(resp.status_code)
	headers = resp.headers
	resp.close()
	loc = headers["Location"]
	return loc

def upload(basedir, filename):
	data = open(basedir / filename, "rb").read()
	j = stage1(filename, len(data))
	loc = stage2(j, data, filename)
	return loc
