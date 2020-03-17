#!/usr/bin/env python3

"""
Write barcode labels
"""

# https://gist.github.com/lkrone/04ca0e3ae3a78f434e5ac84cfd9ca6b1
# https://programtalk.com/vs2/python/8113/ReportLab/tests/test_graphics_images.py/

import io
import tempfile
import secrets
from os import path
import string
import hashlib
import datetime
import argparse
import sys

from barcode.writer import ImageWriter
import barcode
import qrcode

from reportlab.lib.pagesizes import letter
from reportlab.graphics.shapes import Drawing, String, Image
from reportlab.graphics import renderPDF
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import inch

PAGESIZE = letter
NUM_LABELS_X = 2
NUM_LABELS_Y = 7
URL = 'https://securelink.labmed.uw.edu'

LABEL_WIDTH = PAGESIZE[0] / NUM_LABELS_X

# avery 5162
LABEL_HEIGHT = (1 + 5 / 16) * inch
SHEET_TOP = (10 + 3 / 16) * inch

VERSION = 1


def get_chunks(text, n):
    for i in range(0, len(text), n):
        yield text[i:i + n]


def get_code(length=16):
    """Return a string of the specified length composed of N - 1 random
    characters followed by the uppercased first character of the md5 checksum.

    """

    chars = [c for c in string.ascii_uppercase + string.digits
             if c not in {'I', '1', 'O', '0'}]

    text = ''.join(secrets.choice(chars) for i in range(length - 1))
    check_char = hashlib.md5(text.encode('utf-8')).hexdigest()[0].upper()

    return text + check_char


def get_qr(text):
    qr = qrcode.QRCode()
    qr.add_data(text)
    qr.make(fit=True)

    bc = qr.make_image(fill_color="black", back_color="white")
    with io.BytesIO() as f:
        bc.save(f)
        f.seek(0)
        return f.read()


def get_code128(text):

    # Sunquest expects a semicolon before the payload
    ean = barcode.get('code128', ';' + text, writer=ImageWriter())
    # print(ean.default_writer_options)
    options = {
        'module_height': 5,
        'text_distance': 1,
    }

    with io.BytesIO() as f:
        ean.write(f, options=options, text='-'.join(get_chunks(text, 4)))
        f.seek(0)
        return f.read()


def lablabel(barcode_image, counter):

    date = datetime.datetime.now().strftime('%Y-%m-%d')
    label_drawing = Drawing(LABEL_WIDTH, LABEL_HEIGHT)

    bc_width, bc_height = 230, 60

    label_drawing.add(String(30, bc_height + 10,
                             f'Place this label on lab requisition',
                             fontName="Helvetica",
                             fontSize=10, textAnchor="start"))

    label_drawing.add(String(LABEL_WIDTH - 35, bc_height + 10,
                             f'({counter})',
                             fontName="Helvetica",
                             fontSize=8, textAnchor="start"))

    label_drawing.add(String(30, bc_height - 5,
                             'Lab: scan into QRCODE',
                             fontName="Helvetica",
                             fontSize=10, textAnchor="start"))

    # x, y, width, height, path
    label_drawing.add(Image(20, -10, bc_width, bc_height, barcode_image))

    label_drawing.add(String(bc_width + 10, 0,
                             f'v{VERSION} {date}',
                             fontName="Helvetica",
                             fontSize=8, textAnchor="start"))

    return label_drawing


def qrlabel(url, code, barcode_image, counter):

    label_drawing = Drawing(LABEL_WIDTH, LABEL_HEIGHT)

    # position qr code on left of label
    # x, y, width, height, path
    bc_margin = 20
    bc_edge = LABEL_HEIGHT - bc_margin
    barcode = Image(10, 0, bc_edge, bc_edge, barcode_image)
    label_drawing.add(barcode)

    text_x = bc_edge + 10

    label_drawing.add(String(text_x, 58, url,
                             fontName="Helvetica", fontSize=14, textAnchor="start"))

    label_drawing.add(String(text_x, 46,
                             'Visit address above or scan QR code',
                             fontName="Helvetica", fontSize=10, textAnchor="start"))

    label_drawing.add(String(LABEL_WIDTH - 20, 46,
                             f'({counter})',
                             fontName="Helvetica", fontSize=8, textAnchor="end"))

    label_drawing.add(String(text_x, 34,
                             'Your retrieval code:',
                             fontName="Helvetica", fontSize=10, textAnchor="start"))

    label_drawing.add(String(text_x, 20,
                             '-'.join(get_chunks(code, 4)),
                             fontName="Helvetica-Bold",
                             fontSize=13, textAnchor="start"))

    label_drawing.add(String(text_x, 8,
                             'Testing performed by the University of Washington',
                             fontName="Helvetica-Oblique",
                             fontSize=9, textAnchor="start"))

    return label_drawing


def fill_sheet(canvas, page_number, fake_code=None):

    with tempfile.TemporaryDirectory() as d:
        for label_number in range(NUM_LABELS_Y):
            counter = f'{page_number + 1}-{label_number + 1}'
            code = fake_code or get_code()

            y = SHEET_TOP - LABEL_HEIGHT - label_number * LABEL_HEIGHT

            pth1 = path.join(d, code) + '-code128.png'
            with open(pth1, 'wb') as f:
                f.write(get_code128(code))
            label1 = lablabel(pth1, counter)

            renderPDF.draw(label1, canvas, 0, y)

            pth2 = path.join(d, code) + '-qr.png'
            with open(pth2, 'wb') as f:
                f.write(get_qr(f'{URL}?code={code}'))
            label2 = qrlabel(URL, code, pth2, counter)

            renderPDF.draw(label2, canvas, LABEL_WIDTH, y)


def hline(p, y):
    p.moveTo(0, y)
    p.lineTo(PAGESIZE[0], y)


def vline(p, x):
    p.moveTo(x, 0)
    p.lineTo(x, PAGESIZE[1])


def draw_grid(canvas, include_vline=False):
    """Label layout for Avery 5162 labels"""

    p = canvas.beginPath()

    if include_vline:
        gutter = 1 / 8 * inch
        center = PAGESIZE[0] / 2
        for x in [gutter, center - gutter, center + gutter, PAGESIZE[0] - gutter]:
            vline(p, x)

    # bottommost edge, measured from bottom
    bottom = 7 / 8 * inch
    hline(p, bottom)

    # label boundaries
    for i in range(1, NUM_LABELS_Y):
        hline(p, bottom + i * (1 + 5 / 16) * inch)

    # top edge, measured from bottom
    hline(p, (10 + 3 / 16) * inch)

    p.close()
    canvas.drawPath(p)


def write_labels(outfile, npages=1, include_vline=False, fake_code=None):

    canvas = Canvas(outfile, pagesize=PAGESIZE)
    for page_number in range(npages):
        fill_sheet(canvas, page_number=page_number, fake_code=fake_code)
        draw_grid(canvas, include_vline=include_vline)

        # starts a new page
        canvas.showPage()

    canvas.save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-o', '--outfile',
                        help='Output file name (default '
                        'is "securelink-labels-{date}-n{npages}")')
    parser.add_argument('-n', '--npages', default=1, type=int)
    parser.add_argument('--vline', help='draw vertical line',
                        action='store_true', default=False)
    parser.add_argument('--fake-code', help='fill sheet with this fake code')

    args = parser.parse_args(sys.argv[1:])

    if args.outfile:
        outfile = args.outfile
    else:
        date = datetime.datetime.now().strftime('%Y-%m-%d')
        outfile = f'securelink-labels-{date}-n{args.npages}.pdf'

    print(f'writing {outfile}')
    write_labels(outfile, npages=args.npages, include_vline=args.vline,
                 fake_code=args.fake_code)
