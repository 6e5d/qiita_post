from importer import importer
importer("../../flatmark/flatmark", __file__)

def load_token():
	return open(Path(__file__).parent.parent / "token.txt").read().strip()
