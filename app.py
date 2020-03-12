from flask import Flask, request, render_template
app = Flask(__name__)

@app.route('/')
def home():
    # serve homepage
    barcode = request.args.get('code', "")
    return render_template('index.html', barcode=barcode)


@app.route('/result', methods=['POST'])
def show_result():
    barcode = request.form['barcode']
    dob = request.form['dob']


    return render_template('results.html', barcode=barcode, collect_dt="03/10/2020", result="POSITIVE")