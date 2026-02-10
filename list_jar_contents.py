import zipfile
zf = zipfile.ZipFile('scrcpy-server.jar')
entries = [n for n in zf.namelist() if n.startswith('com/genymobile/scrcpy')]
print('Found entries count:', len(entries))
for e in entries:
    print(e)
