import glob

for f in glob.glob('/home/saberch/GreenLedger_V5_Antigravity/templates/academy/modules/module_*.html'):
    with open(f, 'r') as fp:
        content = fp.read()
    if 'sticky top-0 z-50' in content:
        content = content.replace('sticky top-0 z-50', 'sticky top-0 z-30')
        with open(f, 'w') as fp:
            fp.write(content)
