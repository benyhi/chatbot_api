from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
####
from dotenv import load_dotenv
import os
####
from .controller import consultar_producto, crear_producto, actualizar_producto
####

load_dotenv()

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)

@app.route('/product', methods=['GET'])
def hello():
    return jsonify({"message": "Hello, world!"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)