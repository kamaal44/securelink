# securelink barcode generation

## setup

```
python3 -m venv py3-env
source py3-env/bin/activate
pip install -U pip
pip install -r barcodes-requirements.txt
```

## generate barcodes

In your activated virtualenv, view the options:

```
% python -m barcodes.sheet -h
usage: sheet.py [-h] [-o OUTFILE] [-n NPAGES] [--vline]
                [--fake-code FAKE_CODE]

Write barcode labels

optional arguments:
  -h, --help            show this help message and exit
  -o OUTFILE, --outfile OUTFILE
                        Output file name (default is "securelink-
                        labels-{date}-n{npages}")
  -n NPAGES, --npages NPAGES
  --vline               draw vertical line
  --fake-code FAKE_CODE
                        fill sheet with this fake code
```

Generate 5 pages of barcodes:

```
% python -m barcodes.sheet --npages 5
writing securelink-labels-2020-03-16-n5.pdf
```
